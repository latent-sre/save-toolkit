"""command_exit_zero's completion token (EVAL-012 WP-10 precondition 5, PR #334's finding 5).

An oracle that loads candidate code into its own process could be ended by that code with exit 0
(`sys.exit(0)`, `os._exit(0)`), which command_exit_zero read as a pass. With `completion: true` the
runner hands the command a fresh token; the oracle removes it from its environment before any
candidate code runs and prints it last once every assertion holds. Oracles that run candidate code
only in a child process (operator-cli, pager-webhook) or only read candidate files (obs-burn-rules,
pcf-deploy-job) cannot be ended that way and do not adopt it.
"""

import ast
import sys
import tempfile
from pathlib import Path

import pytest
from probe import catalog, checking, constants, workspaces
from probe_testkit import scenario_file, tiny_spec, ws_context

ROOT = Path(__file__).resolve().parent
IN_PROCESS_ORACLES = {
    "agent-injection/check_repair.py",
    "natural-injection/check_orders.py",
    "natural-injection/check_backoff.py",
    "root-cause/probe_retry.py",
    "incident-writes/probe_checks.py",
    "incidents-api/probe_checks.py",
    "maintenance-banner/probe_banner.py",
    "python-craft/check_contracts.py",
    "python-craft/check_indexed_membership.py",
    "python-craft/check_new_code.py",
}
EARLY_EXIT = "import os\nos._exit(0)\n"
# Modules the candidate creates rather than edits, so the fixture has no file to replace.
CREATED_MODULES = {"python-craft/check_new_code.py": ("outcome_counts.py",)}


def run_check(source, **params):
    """Run command_exit_zero on a staged script in a fresh tiny workspace."""
    with tempfile.TemporaryDirectory(prefix="completion-") as tmp:
        spec = tiny_spec()
        ws = workspaces.seed_workspace(spec, Path(tmp))
        check = {"command": f'"{sys.executable}" -I -B probe_completion.py', "writes": {"probe_completion.py": source},
                 **params}
        return checking.CHECKS["command_exit_zero"](ws_context(spec, ws), check)


TOKEN = f"import os\nprint(os.environ[{checking.COMPLETION_ENV!r}])\n"


@pytest.mark.parametrize(("source", "params", "state", "evidence"), [
    (TOKEN, {"completion": True}, "PASS", "exit 0"),
    ("print('all assertions passed')\n", {"completion": True}, "FAIL", "without its completion token"),
    (TOKEN + "print('late output')\n", {"completion": True}, "FAIL", "without its completion token"),
    (TOKEN + "raise SystemExit(1)\n", {"completion": True}, "FAIL", "exit 1"),
    (TOKEN + "raise SystemExit(3)\n", {"completion": True, "inconclusive_exit_code": 3}, "INCONCLUSIVE", "exit 3"),
    # Without the flag nothing is handed over and exit 0 still passes.
    (f"import os, sys\nsys.exit(1 if {checking.COMPLETION_ENV!r} in os.environ else 0)\n", {}, "PASS", "exit 0"),
])
def test_completion_passes_only_on_the_token_as_the_last_line(source, params, state, evidence):
    outcome = run_check(source, **params)
    assert (outcome.state, evidence in outcome.evidence) == (state, True), outcome.evidence


def test_each_run_gets_a_fresh_token():
    first, second = run_check(TOKEN, completion=True), run_check(TOKEN, completion=True)
    assert first.state == second.state == "PASS"
    assert first.evidence != second.evidence, "the evidence tail carries each run's own token"


@pytest.mark.parametrize(("check", "valid"), [
    ({"check": "command_exit_zero", "command": "python x.py", "completion": True}, True),
    ({"check": "command_exit_zero", "command": "python x.py", "completion": "yes"}, False),
    ({"check": "command_exit_zero", "command": "python x.py", "completion": False}, False),
    ({"check": "text_regex", "pattern": "x", "completion": True}, False),
])
def test_validation_accepts_only_true_on_command_exit_zero(check, valid):
    problems = catalog.validate_scenario(tiny_spec(checks=[{**check, "text": "probe"}]))
    assert (not problems) is valid, problems


def staged_oracles(spec):
    return {name: str(src) for c in spec.get("checks", []) for name, src in (c.get("writes_from") or {}).items()}


def runs_oracle(check, names):
    return check["check"] == "command_exit_zero" and any(name in str(check.get("command", "")) for name in names)


def test_every_check_that_runs_an_in_process_oracle_declares_completion_and_no_other_does():
    sources = {f"evals/oracles/{rel}" for rel in IN_PROCESS_ORACLES}
    declared = needed = 0
    for path in sorted(constants.SCENARIO_DIR.glob("*.yaml")):
        spec = scenario_file(path)
        names = {name for name, src in staged_oracles(spec).items() if src in sources}
        for check in spec.get("checks", []):
            needs = runs_oracle(check, names)
            assert bool(check.get("completion")) is needs, (spec["id"], check.get("command"))
            declared += bool(check.get("completion"))
            needed += needs
    assert declared == needed > len(IN_PROCESS_ORACLES)


def test_each_in_process_oracle_removes_the_token_before_anything_else_runs():
    adopted = {path.relative_to(ROOT / "oracles").as_posix() for path in (ROOT / "oracles").rglob("*.py")
               if checking.COMPLETION_ENV in path.read_text(encoding="utf-8")}
    assert adopted == IN_PROCESS_ORACLES
    for rel in sorted(IN_PROCESS_ORACLES):
        body = ast.parse((ROOT / "oracles" / rel).read_text(encoding="utf-8")).body
        statements = [node for node in body if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
                      and not (isinstance(node, ast.ImportFrom) and node.module == "__future__")]
        imports_os, pops = statements[:2]
        assert ast.unparse(imports_os) == "import os", rel
        assert ast.unparse(pops) == f"COMPLETION = os.environ.pop({checking.COMPLETION_ENV!r}, '')", rel


def completion_checks(oracle):
    source = f"evals/oracles/{oracle}"
    for path in sorted(constants.SCENARIO_DIR.glob("*.yaml")):
        spec = scenario_file(path)
        names = {name for name, src in staged_oracles(spec).items() if src == source}
        yield from ((spec, check) for check in spec.get("checks", []) if check.get("completion") and runs_oracle(check, names))


@pytest.mark.parametrize("oracle", sorted(IN_PROCESS_ORACLES))
def test_candidate_code_that_exits_zero_no_longer_passes(oracle, tmp_path):
    """Every candidate module the fixture holds exits 0 the moment it loads. Each declared check
    fails; where the flag-free check passed, as finding 5 found, the failure names the missing
    token. A mode that runs the candidate in a child process already failed, and still does."""
    reproduced = 0
    for index, (spec, check) in enumerate(completion_checks(oracle)):
        ws = workspaces.seed_workspace(spec, tmp_path / str(index))
        staged = staged_oracles(spec)
        modules = [*ws.repo.rglob("*.py"), *(ws.repo / name for name in CREATED_MODULES.get(oracle, ()))]
        for module in modules:
            if ".git" not in module.parts and module.name not in staged:
                module.write_text(EARLY_EXIT, encoding="utf-8")
        for name, src in staged.items():  # a later check reuses a file an earlier one staged
            (ws.repo / name).write_text((constants.ROOT / src).read_text(encoding="utf-8"), encoding="utf-8")
        ctx = ws_context(spec, ws)
        unflagged = checking.CHECKS["command_exit_zero"](ctx, {k: v for k, v in check.items() if k != "completion"})
        flagged = checking.CHECKS["command_exit_zero"](ctx, check)
        assert flagged.state == "FAIL", (spec["id"], flagged.evidence)
        if unflagged.state == "PASS":
            assert "without its completion token" in flagged.evidence, (spec["id"], flagged.evidence)
            reproduced += 1
    assert reproduced, f"no check of {oracle} let an early exit pass without the token"
