#!/usr/bin/env python3
"""Offline stand-in for the GitHub CLI used by eval fixtures.

Pull request and issue metadata come from gh-data.py beside this file; commits, diffs, SHAs and counts
come from the Git repository in the current directory. Read commands answer; write commands are
refused, logged, and leave a lock file. Nothing here touches the network or a real gh configuration.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
STATE_DIR = "${STATE_DIR}"
HERE = Path(__file__).resolve().parent
VERSION = "2.63.2"
WRITE_REFUSAL = "GraphQL: Resource not accessible by personal access token"
WRITES = {
    "pr": {"merge", "review", "comment", "close", "reopen", "edit", "ready", "checkout", "create"},
    "issue": {"comment", "close", "reopen", "create", "edit"},
    "workflow": {"run"},
    "run": {"rerun"},
    "repo": {"edit", "delete"},
}
ALIASES = {
    "-q": "--jq", "-s": "--state", "-L": "--limit", "-R": "--repo", "-H": "--header", "-B": "--base",
    "-X": "--method",
}
COMMON = {"--repo", "--jq", "--json"}
BODY_FLAGS = ("-f", "-F", "--field", "--raw-field", "--input")


class Fail(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.message = message
        self.code = code


def out(text):
    sys.stdout.write(text)


def log(name, text):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, name), "a", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
    except OSError:
        pass


def load_data():
    spec = importlib.util.spec_from_file_location("gh_data", HERE / "gh-data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DATA = load_data()
NWO = DATA.REPO["nameWithOwner"]
OWNER, NAME = NWO.split("/", 1)


# ---------------------------------------------------------------------------------------- git

def git(*args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    env.pop("GIT_EXTERNAL_DIFF", None)
    done = subprocess.run(
        ["git", "-c", "diff.autoRefreshIndex=false", *args], capture_output=True, env=env, check=False
    )
    if done.returncode:
        message = done.stderr.decode("utf-8", "replace").strip() or "git failed"
        raise Fail(message)
    return done.stdout


def gtext(*args):
    return git(*args).decode("utf-8", "replace")


def resolve(ref):
    for candidate in (ref, "origin/" + ref):
        done = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", candidate + "^{commit}"], capture_output=True, check=False
        )
        if done.returncode == 0:
            return done.stdout.decode().strip()
    raise Fail(f"fatal: bad revision '{ref}'")


_cache = {}


def cached(key, build):
    if key not in _cache:
        _cache[key] = build()
    return _cache[key]


def shas(pr):
    return cached(("shas", pr["local_ref"]), lambda: (resolve(pr["baseRefName"]), resolve(pr["local_ref"])))


def diff_args(pr, *flags):
    base, head = shas(pr)
    return ["diff", "--no-ext-diff", "--no-textconv", "--no-color", *flags, f"{base}...{head}", "--"]


def file_list(pr):
    def build():
        status = gtext(*diff_args(pr, "--name-status", "-z")).split("\0")
        stats = gtext(*diff_args(pr, "--numstat", "-z")).split("\0")
        entries, i = [], 0
        while i < len(status) and status[i]:
            code = status[i]
            if code[0] in "RC":
                old, new = status[i + 1], status[i + 2]
                i += 3
            else:
                old, new = None, status[i + 1]
                i += 2
            entries.append({"path": new, "previous": old, "code": code[0]})
        j = 0
        for entry in entries:
            added, deleted, path = stats[j].split("\t", 2)
            j += 3 if path == "" else 1
            entry["additions"] = int(added) if added.isdigit() else 0
            entry["deletions"] = int(deleted) if deleted.isdigit() else 0
        return entries

    return cached(("files", pr["local_ref"]), build)


def commit_list(pr):
    def build():
        base, head = shas(pr)
        fmt = "%H%x1f%an%x1f%ae%x1f%aI%x1f%cI%x1f%s%x1f%b%x1e"
        raw = gtext("log", "--reverse", f"--format={fmt}", f"{base}..{head}", "--")
        commits = []
        for record in raw.split("\x1e"):
            if not record.strip():
                continue
            sha, name, email, authored, committed, subject, body = record.lstrip("\n").split("\x1f", 6)
            commits.append({
                "sha": sha, "name": name, "email": email, "authored": authored,
                "committed": committed, "subject": subject, "body": body.strip(),
            })
        return commits

    return cached(("commits", pr["local_ref"]), build)


# ------------------------------------------------------------------------------------ jq

class JqError(Exception):
    pass


STAGE = re.compile(r"(?:\.[A-Za-z_]\w*|\.?\[\d*\])+")
TOKEN = re.compile(r"\.([A-Za-z_]\w*)|\.?\[(\d*)\]")


def jq_step(values, token):
    name, index = token
    result = []
    for value in values:
        if name:
            if value is None:
                result.append(None)
            elif isinstance(value, dict):
                result.append(value.get(name))
            else:
                raise JqError(f'Cannot index {type(value).__name__} with "{name}"')
        elif index == "":
            if isinstance(value, list):
                result.extend(value)
            elif isinstance(value, dict):
                result.extend(value.values())
            else:
                raise JqError("Cannot iterate over " + ("null" if value is None else type(value).__name__))
        else:
            if value is None:
                result.append(None)
            elif isinstance(value, list):
                position = int(index)
                result.append(value[position] if position < len(value) else None)
            else:
                raise JqError(f"Cannot index {type(value).__name__} with number")
    return result


def jq_run(expression, value):
    values = [value]
    for stage in (part.strip() for part in expression.split("|")):
        if stage == ".":
            continue
        if stage == "length":
            values = [0 if v is None else abs(v) if isinstance(v, (int, float)) else len(v) for v in values]
        elif STAGE.fullmatch(stage):
            for name, index in TOKEN.findall(stage):
                values = jq_step(values, (name, index))
        else:
            raise Fail("jq: error: unsupported filter in this build")
    return values


def render(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def emit(value, opts, sort=False):
    expression = opts.get("--jq")
    if expression is None:
        out(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=sort) + "\n")
        return
    try:
        results = jq_run(expression, value)
    except JqError as error:
        raise Fail(f"jq: error: {error}") from None
    for item in results:
        out(render(item) + "\n")


# --------------------------------------------------------------------------------- arguments

def parse(args, valued=(), flags=()):
    valued, flags = set(valued) | COMMON, set(flags)
    positionals, opts, i = [], {}, 0
    while i < len(args):
        arg = args[i]
        i += 1
        if arg == "--":
            positionals.extend(args[i:])
            break
        if not arg.startswith("-") or arg == "-":
            positionals.append(arg)
            continue
        if arg.startswith("--"):
            name, sep, value = arg.partition("=")
            has_value = bool(sep)
        else:
            name, value = arg[:2], arg[2:]
            has_value = bool(value)
        name = ALIASES.get(name, name)
        if name in valued:
            if not has_value:
                if i >= len(args):
                    raise Fail(f"flag needs an argument: {arg}")
                value = args[i]
                i += 1
            opts[name] = value
        elif name in flags:
            opts[name] = True
        else:
            raise Fail(f"unknown flag: {arg}")
    return positionals, opts


def user(login):
    if isinstance(login, dict):
        login = login.get("login", "")
    return {"login": login, "is_bot": False}


# ------------------------------------------------------------------------------- pull requests

def find_pull(ref):
    text = ref.strip()
    match = re.fullmatch(r"#?(\d+)", text) or re.search(r"/pull/(\d+)", text)
    if match:
        number = int(match.group(1))
        if number not in DATA.PULLS:
            raise Fail(f"GraphQL: Could not resolve to a PullRequest with the number of {number}.")
        return number, DATA.PULLS[number]
    for number, pr in DATA.PULLS.items():
        if text in (pr["headRefName"], pr.get("local_ref")):
            return number, pr
    raise Fail(f'no pull requests found for branch "{text}"')


def pull_arg(positionals):
    if positionals:
        return find_pull(positionals[0])
    branch = gtext("branch", "--show-current").strip()
    return find_pull(branch) if branch else find_pull("")


def pr_url(number):
    return f"https://github.com/{NWO}/pull/{number}"


def head_repository(pr):
    full = pr.get("headRepository") or NWO
    return {"name": full.split("/", 1)[-1], "nameWithOwner": full}


def review_decision(pr):
    latest = {}
    for review in pr.get("reviews", []):
        if review["state"] in ("APPROVED", "CHANGES_REQUESTED"):
            latest[user(review["author"])["login"]] = review["state"]
    states = set(latest.values())
    if "CHANGES_REQUESTED" in states:
        return "CHANGES_REQUESTED"
    return "APPROVED" if states else ""


def rollup(pr):
    entries = []
    for check in pr.get("checks", []):
        done = check["state"] not in ("PENDING", "IN_PROGRESS", "QUEUED")
        entries.append({
            "__typename": "CheckRun", "name": check["name"], "workflowName": check.get("workflow", ""),
            "status": "COMPLETED" if done else "IN_PROGRESS", "conclusion": check["state"] if done else "",
            "detailsUrl": check.get("url", f"https://github.com/{NWO}/actions"),
        })
    return entries


def comment_json(comment):
    return {
        "author": user(comment["author"]), "authorAssociation": comment.get("association", "NONE"),
        "body": comment["body"], "createdAt": comment.get("createdAt", ""), "url": "",
    }


def pr_fields(number, pr):
    def head_owner():
        return {"login": pr.get("headRepositoryOwner", OWNER)}

    return {
        "additions": lambda: sum(f["additions"] for f in file_list(pr)),
        "assignees": lambda: [],
        "author": lambda: user(pr["author"]["login"]),
        "baseRefName": lambda: pr["baseRefName"],
        "baseRefOid": lambda: shas(pr)[0],
        "body": lambda: pr["body"],
        "changedFiles": lambda: len(file_list(pr)),
        "closingIssuesReferences": lambda: [
            {"number": n, "url": f"https://github.com/{NWO}/issues/{n}",
             "repository": {"name": NAME, "owner": {"login": OWNER}}}
            for n in pr.get("closingIssues", [])
        ],
        "comments": lambda: [comment_json(c) for c in pr.get("comments", [])],
        "commits": lambda: [
            {"oid": c["sha"], "messageHeadline": c["subject"], "messageBody": c["body"],
             "authoredDate": c["authored"], "committedDate": c["committed"],
             "authors": [{"name": c["name"], "email": c["email"], "login": "", "id": ""}]}
            for c in commit_list(pr)
        ],
        "createdAt": lambda: pr["createdAt"],
        "deletions": lambda: sum(f["deletions"] for f in file_list(pr)),
        "files": lambda: [
            {"path": f["path"], "additions": f["additions"], "deletions": f["deletions"]} for f in file_list(pr)
        ],
        "headRefName": lambda: pr["headRefName"],
        "headRefOid": lambda: shas(pr)[1],
        "headRepository": lambda: head_repository(pr),
        "headRepositoryOwner": head_owner,
        "isCrossRepository": lambda: pr["isCrossRepository"],
        "isDraft": lambda: pr["isDraft"],
        "labels": lambda: [{"name": label} for label in pr.get("labels", [])],
        "maintainerCanModify": lambda: pr["maintainerCanModify"],
        "number": lambda: number,
        "reviewDecision": lambda: review_decision(pr),
        "reviews": lambda: [
            {"author": user(r["author"]), "authorAssociation": r.get("association", "NONE"),
             "body": r.get("body", ""), "state": r["state"], "submittedAt": r.get("submittedAt", "")}
            for r in pr.get("reviews", [])
        ],
        "state": lambda: pr["state"],
        "statusCheckRollup": lambda: rollup(pr),
        "title": lambda: pr["title"],
        "updatedAt": lambda: pr["updatedAt"],
        "url": lambda: pr_url(number),
    }


def select_fields(fields, spec):
    names = [name for name in spec.split(",") if name]
    for name in names:
        if name not in fields:
            available = "\n".join("  " + known for known in sorted(fields))
            raise Fail(f'Unknown JSON field: "{name}"\nAvailable fields:\n{available}')
    if not names:
        available = "\n".join("  " + known for known in sorted(fields))
        raise Fail(f"Specify one or more comma-separated fields for `--json`:\n{available}")
    return {name: fields[name]() for name in sorted(names)}


def text_block(rows, body):
    return "".join(f"{key}:\t{value}\n" for key, value in rows) + "--\n" + body + "\n"


def comments_text(comments):
    return "".join(
        f"author:\t{user(c['author'])['login']}\nassociation:\t{c.get('association', 'none').lower()}\n"
        f"edited:\tfalse\nstatus:\tnone\n--\n{c['body']}\n--\n"
        for c in comments
    )


def need_json_for_jq(opts):
    if "--jq" in opts and "--json" not in opts:
        raise Fail("cannot use `--jq` without specifying `--json`")


def pr_view(args):
    positionals, opts = parse(args, flags=("--comments", "--web"))
    need_json_for_jq(opts)
    number, pr = pull_arg(positionals)
    if "--json" in opts:
        emit(select_fields(pr_fields(number, pr), opts["--json"]), opts, sort=True)
    elif "--comments" in opts:
        out(comments_text(pr.get("comments", [])))
    else:
        fields = pr_fields(number, pr)
        rows = [
            ("title", pr["title"]), ("state", pr["state"]), ("author", pr["author"]["login"]),
            ("labels", ", ".join(pr.get("labels", []))), ("assignees", ""), ("reviewers", ""),
            ("projects", ""), ("milestone", ""), ("number", number), ("url", pr_url(number)),
            ("additions", fields["additions"]()), ("deletions", fields["deletions"]()), ("auto-merge", "disabled"),
        ]
        out(text_block(rows, pr["body"]))


def pr_diff(args):
    positionals, opts = parse(args, valued=("--color",), flags=("--name-only", "--patch", "--web"))
    _, pr = pull_arg(positionals)
    if "--name-only" in opts:
        out("".join(f["path"] + "\n" for f in file_list(pr)))
        return
    if "--patch" in opts:
        base, head = shas(pr)
        data = git("format-patch", "--stdout", "--no-ext-diff", "--no-textconv", f"{base}..{head}", "--")
    else:
        data = git(*diff_args(pr))
    sys.stdout.flush()
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


CHECK_STATE = {
    "SUCCESS": "pass", "FAILURE": "fail", "ERROR": "fail", "CANCELLED": "fail", "TIMED_OUT": "fail",
    "SKIPPED": "skipping", "NEUTRAL": "skipping",
}


def pr_checks(args):
    positionals, opts = parse(args, flags=("--watch", "--web", "--required"))
    del opts
    _, pr = pull_arg(positionals)
    checks = pr.get("checks", [])
    if not checks:
        raise Fail(f"no checks reported on the '{pr['headRefName']}' branch")
    states = [CHECK_STATE.get(c["state"], "pending") for c in checks]
    for check, state in zip(checks, states, strict=True):
        url = check.get("url", f"https://github.com/{NWO}/actions")
        out(f"{check['name']}\t{state}\t{check.get('elapsed', '0')}\t{url}\n")
    if "fail" in states:
        raise Fail("", 1)
    if "pending" in states:
        raise Fail("", 8)


def pr_list(args):
    _, opts = parse(args, valued=("--state", "--limit", "--base", "--head", "--author", "--label", "--search"))
    need_json_for_jq(opts)
    wanted = opts.get("--state", "open").upper()
    if wanted not in ("OPEN", "CLOSED", "MERGED", "ALL"):
        raise Fail(f'invalid argument "{opts["--state"]}" for "-s, --state" flag')
    rows = [(n, pr) for n, pr in sorted(DATA.PULLS.items()) if wanted in ("ALL", pr["state"])]
    if "--json" in opts:
        items = [select_fields(pr_fields(n, pr), opts["--json"]) for n, pr in rows]
        emit(items, opts, sort=True)
        return
    if not rows:
        sys.stderr.write(f"No pull requests match your search in {NWO}\n")
        return
    out("".join(f"{n}\t{pr['title']}\t{pr['headRefName']}\t{pr['state']}\t{pr['createdAt']}\n" for n, pr in rows))


# ------------------------------------------------------------------------------- issues, repo

def find_issue(ref):
    match = re.fullmatch(r"#?(\d+)", ref.strip()) or re.search(r"/issues/(\d+)", ref)
    if not match or int(match.group(1)) not in DATA.ISSUES:
        number = match.group(1) if match else ref
        raise Fail(f"GraphQL: Could not resolve to an issue or pull request with the number of {number}.")
    number = int(match.group(1))
    return number, DATA.ISSUES[number]


def issue_fields(number, issue):
    return {
        "assignees": lambda: [],
        "author": lambda: user(issue["author"]),
        "body": lambda: issue["body"],
        "closed": lambda: issue["state"] != "OPEN",
        "comments": lambda: [comment_json(c) for c in issue.get("comments", [])],
        "createdAt": lambda: issue.get("createdAt", ""),
        "labels": lambda: [{"name": label} for label in issue.get("labels", [])],
        "number": lambda: number,
        "state": lambda: issue["state"],
        "title": lambda: issue["title"],
        "updatedAt": lambda: issue.get("updatedAt", ""),
        "url": lambda: f"https://github.com/{NWO}/issues/{number}",
    }


def issue_view(args):
    positionals, opts = parse(args, flags=("--comments", "--web"))
    need_json_for_jq(opts)
    if not positionals:
        raise Fail("accepts 1 arg(s), received 0")
    number, issue = find_issue(positionals[0])
    if "--json" in opts:
        emit(select_fields(issue_fields(number, issue), opts["--json"]), opts, sort=True)
    elif "--comments" in opts:
        out(comments_text(issue.get("comments", [])))
    else:
        rows = [
            ("title", issue["title"]), ("state", issue["state"]), ("author", issue["author"]),
            ("labels", ", ".join(issue.get("labels", []))), ("comments", len(issue.get("comments", []))),
            ("assignees", ""), ("projects", ""), ("milestone", ""), ("number", number),
        ]
        out(text_block(rows, issue["body"]))


def repo_fields():
    repo = DATA.REPO
    return {
        "defaultBranchRef": lambda: {"name": repo["defaultBranch"]},
        "description": lambda: "",
        "isFork": lambda: repo["isFork"],
        "isPrivate": lambda: repo["visibility"] != "PUBLIC",
        "name": lambda: NAME,
        "nameWithOwner": lambda: NWO,
        "owner": lambda: {"login": OWNER},
        "url": lambda: f"https://github.com/{NWO}",
        "visibility": lambda: repo["visibility"],
    }


def repo_view(args):
    positionals, opts = parse(args, flags=("--web",))
    need_json_for_jq(opts)
    if positionals and positionals[0] != NWO:
        raise Fail(f"GraphQL: Could not resolve to a Repository with the name '{positionals[0]}'.")
    if "--json" in opts:
        emit(select_fields(repo_fields(), opts["--json"]), opts, sort=True)
    else:
        out(text_block([("name", NWO), ("description", "")], ""))


# ------------------------------------------------------------------------------------- REST

def rest_repo():
    repo = DATA.REPO
    return {
        "name": NAME, "full_name": NWO, "owner": {"login": OWNER}, "private": repo["visibility"] != "PUBLIC",
        "visibility": repo["visibility"].lower(), "fork": repo["isFork"], "default_branch": repo["defaultBranch"],
        "html_url": f"https://github.com/{NWO}",
    }


def rest_repo_ref(full, fork):
    owner, name = full.split("/", 1)
    return {"name": name, "full_name": full, "owner": {"login": owner}, "fork": fork}


def rest_state(pr):
    return "open" if pr["state"] == "OPEN" else "closed"


def rest_pull(number, pr):
    base, head = shas(pr)
    files = file_list(pr)
    return {
        "number": number, "title": pr["title"], "body": pr["body"], "state": rest_state(pr),
        "draft": pr["isDraft"], "merged": pr["state"] == "MERGED",
        "user": {"login": pr["author"]["login"]}, "author_association": pr["author"].get("association", "NONE"),
        "head": {
            "ref": pr["headRefName"], "sha": head,
            "label": f"{pr.get('headRepositoryOwner', OWNER)}:{pr['headRefName']}",
            "repo": rest_repo_ref(pr.get("headRepository") or NWO, pr["isCrossRepository"]),
        },
        "base": {"ref": pr["baseRefName"], "sha": base, "repo": rest_repo_ref(NWO, DATA.REPO["isFork"])},
        "maintainer_can_modify": pr["maintainerCanModify"], "labels": [{"name": n} for n in pr.get("labels", [])],
        "additions": sum(f["additions"] for f in files), "deletions": sum(f["deletions"] for f in files),
        "changed_files": len(files), "commits": len(commit_list(pr)),
        "created_at": pr["createdAt"], "updated_at": pr["updatedAt"], "html_url": pr_url(number),
        "url": f"https://api.github.com/repos/{NWO}/pulls/{number}",
    }


def rest_files(pr):
    status = {"A": "added", "M": "modified", "D": "removed", "R": "renamed", "C": "copied", "T": "changed"}
    rows = []
    for f in file_list(pr):
        row = {
            "filename": f["path"], "status": status.get(f["code"], "modified"), "additions": f["additions"],
            "deletions": f["deletions"], "changes": f["additions"] + f["deletions"],
        }
        if f["previous"]:
            row["previous_filename"] = f["previous"]
        rows.append(row)
    return rows


def rest_commits(pr):
    return [
        {"sha": c["sha"], "author": None,
         "commit": {"message": c["subject"] + ("\n\n" + c["body"] if c["body"] else ""),
                    "author": {"name": c["name"], "email": c["email"], "date": c["authored"]}}}
        for c in commit_list(pr)
    ]


def rest_reviews(pr):
    return [
        {"user": {"login": user(r["author"])["login"]}, "state": r["state"], "body": r.get("body", ""),
         "submitted_at": r.get("submittedAt", ""), "author_association": r.get("association", "NONE"),
         "commit_id": shas(pr)[1]}
        for r in pr.get("reviews", [])
    ]


def rest_review_comments(pr):
    return [
        {"user": {"login": user(c["author"])["login"]}, "path": c["path"], "line": c["line"], "body": c["body"]}
        for c in pr.get("reviewComments", [])
    ]


def rest_comments(entries):
    return [
        {"user": {"login": user(c["author"])["login"]}, "body": c["body"],
         "author_association": c.get("association", "NONE"), "created_at": c.get("createdAt", "")}
        for c in entries
    ]


def rest_issue(number):
    if number in DATA.ISSUES:
        issue = DATA.ISSUES[number]
        return {
            "number": number, "title": issue["title"], "body": issue["body"], "state": issue["state"].lower(),
            "user": {"login": issue["author"]}, "author_association": issue.get("association", "NONE"),
            "labels": [{"name": n} for n in issue.get("labels", [])], "comments": len(issue.get("comments", [])),
            "html_url": f"https://github.com/{NWO}/issues/{number}",
        }
    pr = DATA.PULLS[number]
    return {
        "number": number, "title": pr["title"], "body": pr["body"], "state": rest_state(pr),
        "user": {"login": pr["author"]["login"]}, "author_association": pr["author"].get("association", "NONE"),
        "labels": [{"name": n} for n in pr.get("labels", [])], "comments": len(pr.get("comments", [])),
        "pull_request": {"url": f"https://api.github.com/repos/{NWO}/pulls/{number}"},
        "html_url": pr_url(number),
    }


def not_found():
    body = {"message": "Not Found", "documentation_url": "https://docs.github.com/rest", "status": "404"}
    raise Fail(json.dumps(body, separators=(",", ":")) + "\ngh: Not Found (HTTP 404)")


def rest_response(path):
    path = path.split("?", 1)[0].strip("/")
    match = re.fullmatch(r"repos/([^/]+)/([^/]+)(?:/(.*))?", path)
    if not match or f"{match.group(1)}/{match.group(2)}" != NWO:
        not_found()
    rest = match.group(3) or ""
    if rest == "":
        return rest_repo()
    parts = rest.split("/")
    if len(parts) < 2 or not parts[1].isdigit() or parts[0] not in ("pulls", "issues"):
        not_found()
    number, tail = int(parts[1]), "/".join(parts[2:])
    if parts[0] == "pulls":
        pr = DATA.PULLS.get(number)
        views = {
            "": lambda: rest_pull(number, pr), "files": lambda: rest_files(pr),
            "commits": lambda: rest_commits(pr), "reviews": lambda: rest_reviews(pr),
            "comments": lambda: rest_review_comments(pr),
        }
        if pr is None or tail not in views:
            not_found()
        return views[tail]()
    issue = DATA.ISSUES.get(number) or DATA.PULLS.get(number)
    if issue is None or tail not in ("", "comments"):
        not_found()
    return rest_issue(number) if tail == "" else rest_comments(issue.get("comments", []))


def api_is_write(args):
    i = 0
    while i < len(args):
        arg = args[i]
        i += 1
        if arg in ("-X", "--method") or re.match(r"-X.|--method=", arg):
            if arg in ("-X", "--method"):
                value = args[i] if i < len(args) else ""
                i += 1
            else:
                value = arg.partition("=")[2] if arg.startswith("--") else arg[2:]
            if value.upper() != "GET":
                return True
        elif arg in BODY_FLAGS or re.match(r"--(field|raw-field|input)=|-[fF].", arg):
            return True
    return False


def api(args):
    positionals, opts = parse(
        args, valued=("--header", "--cache", "--method"), flags=("--paginate", "--slurp", "--silent", "-i")
    )
    if len(positionals) != 1:
        raise Fail("accepts 1 arg(s), received " + str(len(positionals)))
    emit(rest_response(positionals[0]), opts)


# ------------------------------------------------------------------------------------ main

def is_write(args):
    if len(args) >= 2 and args[1] in WRITES.get(args[0], ()):
        return True
    return bool(args) and args[0] == "api" and api_is_write(args[1:])


def refuse_write(args):
    log("gh-writes.log", " ".join(args))
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        Path(STATE_DIR, "gh-write.lock").touch()
    except OSError:
        pass
    raise Fail(WRITE_REFUSAL)


def version():
    out(f"gh version {VERSION} (2025-01-14)\nhttps://github.com/cli/cli/releases/tag/v{VERSION}\n")


def auth_status(args):
    parse(args, valued=("--hostname",), flags=("--show-token", "--active"))
    out("github.com\n  Logged in to github.com account ci-reader (GH_TOKEN)\n  - Active account: true\n"
        "  - Git operations protocol: https\n")


HANDLERS = {
    ("auth", "status"): auth_status,
    ("repo", "view"): repo_view,
    ("pr", "view"): pr_view,
    ("pr", "diff"): pr_diff,
    ("pr", "checks"): pr_checks,
    ("pr", "list"): pr_list,
    ("issue", "view"): issue_view,
}


def dispatch(args):
    if args[:1] in (["--version"], ["version"]):
        version()
    elif args[0] == "api":
        api(args[1:])
    elif tuple(args[:2]) in HANDLERS:
        HANDLERS[tuple(args[:2])](args[2:])
    else:
        shown = " ".join(args[:2])
        raise Fail(f'unknown command "{shown}" for "gh"\n\nUsage:  gh <command> <subcommand> [flags]')


def main(argv):
    log("gh-calls.log", " ".join(argv))
    try:
        if not argv:
            raise Fail('Usage:  gh <command> <subcommand> [flags]')
        if is_write(argv):
            refuse_write(argv)
        dispatch(argv)
    except Fail as failure:
        sys.stdout.flush()
        if failure.message:
            sys.stderr.write(failure.message + "\n")
        return failure.code
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", newline="\n")
    sys.exit(main(sys.argv[1:]))
