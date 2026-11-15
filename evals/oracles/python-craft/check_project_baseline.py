"""Project-baseline outcome checks staged after the model turn; no third-party dependencies.

`new` inspects a freshly started project: its declared floor, packaging, dependency fields, tool
settings and CI script, and the small behavior the task specified. `narrow` inspects a scoped fix
in an older project: the defect is fixed for the project's own floor and its toolchain is untouched.
These are public regression oracles for disposable fixtures, not hidden evaluations or a sandbox.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call

import ast
import contextlib
from datetime import timedelta
import hashlib
import importlib
import importlib.util
import io
import re
import tomllib
from types import FunctionType
from unittest import TestCase


CHECK = TestCase()
FLOOR = 14
TYPE_CHECKERS = {"mypy", "pyright", "basedpyright", "ty", "pyrefly", "pytype", "pyre-check"}
LEGACY_FILES = ("setup.py", "setup.cfg", "requirements.txt", "requirements-dev.txt", "Pipfile", "poetry.lock")
# Text digests of the older project's toolchain files, as its scenario fixture ships them.
NARROW_TOOLCHAIN = {
    "pyproject.toml": "fe27cd257eff3cb732590c2c1e133bb4e1a1677166774c215d4a7b75e57cd5d9",
    "poetry.lock": "130c5cd7a7f01d4daaf7581ddfdb3c91c774a52d588606cf03707e6d9a162d35",
    ".flake8": "eda03f3b4590bf808a342f504995cb21e869a04c304787550c059f1c1580445f",
}
MIGRATION_FILES = ("uv.lock", "ruff.toml", ".ruff.toml", "requirements.txt", "setup.py")


def text_digest(path):
    # read_text applies universal newlines, so a Windows checkout of the fixture hashes the same.
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def requirement_name(requirement):
    return re.split(r"[\s<>=!~;\[(@]", requirement.strip(), maxsplit=1)[0].lower().replace("_", "-")


def minor(value, pattern):
    match = re.search(pattern, str(value))
    return int(match.group(1)) if match else None


def functions(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    return {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}, tree


def check_metadata(project, data):
    floor = minor(project.get("requires-python", ""), r">=\s*3\.(\d+)")
    CHECK.assertIsNotNone(floor, "requires-python declares no '>=3.N' floor")
    CHECK.assertGreaterEqual(floor, FLOOR, "requires-python floor is below 3.14")
    build = data.get("build-system", {})
    CHECK.assertTrue(build.get("build-backend") and build.get("requires"), "no build backend declared for an installable project")
    CHECK.assertIn("quota-check", project.get("scripts", {}), "quota-check console script is not declared")
    CHECK.assertNotIn("poetry", data.get("tool", {}), "project metadata is not in the standard [project] table alone")
    for name in LEGACY_FILES:
        CHECK.assertFalse(Path(name).exists(), f"{name} duplicates what pyproject.toml and uv own")


def check_dependencies(project, data):
    published = [requirement_name(r) for r in project.get("dependencies", [])]
    for extra in project.get("optional-dependencies", {}).values():
        published += [requirement_name(r) for r in extra]
    grouped = [requirement_name(r) for group in data.get("dependency-groups", {}).values()
               for r in group if isinstance(r, str)]
    for tool in sorted({"pytest", "ruff"} | TYPE_CHECKERS):
        CHECK.assertNotIn(tool, published, f"{tool} is a development tool but is published as a runtime dependency or extra")
    for tool in ("pytest", "ruff"):
        CHECK.assertIn(tool, grouped, f"{tool} is missing from [dependency-groups]")
    checkers = sorted(TYPE_CHECKERS.intersection(grouped))
    CHECK.assertEqual(len(checkers), 1, f"expected exactly one type checker in [dependency-groups], found {checkers}")
    return checkers[0]


def check_tool_settings(data, checker):
    tools = data.get("tool", {})
    target = tools.get("ruff", {}).get("target-version")
    if target is not None:
        CHECK.assertGreaterEqual(minor(target, r"py3(\d+)") or 0, FLOOR, "ruff target-version is below the floor")
    if checker == "mypy":
        CHECK.assertFalse(Path("mypy.ini").exists(), "mypy settings belong in pyproject.toml")
        settings = tools.get("mypy", {})
        CHECK.assertGreaterEqual(minor(settings.get("python_version"), r"3\.(\d+)") or 0, FLOOR,
                                 "mypy python_version is not set to the floor")
        CHECK.assertIs(settings.get("strict"), True, "mypy is not strict")
    elif checker in ("pyright", "basedpyright"):
        CHECK.assertFalse(Path("pyrightconfig.json").exists(), "pyright settings belong in pyproject.toml")
        settings = tools.get(checker, {}) or tools.get("pyright", {})
        CHECK.assertGreaterEqual(minor(settings.get("pythonVersion"), r"3\.(\d+)") or 0, FLOOR,
                                 "pyright pythonVersion is not set to the floor")
        CHECK.assertEqual(settings.get("typeCheckingMode"), "strict", "pyright is not strict")
    else:
        version = tools.get(checker, {}).get("environment", {}).get("python-version")
        if version is not None:
            CHECK.assertGreaterEqual(minor(version, r"3\.(\d+)") or 0, FLOOR, "type checker python-version is below the floor")


def check_ci(checker):
    CHECK.assertTrue(Path("ci.sh").is_file(), "ci.sh is missing")
    joined = Path("ci.sh").read_text(encoding="utf-8").replace("\\\n", " ")
    commands = [re.sub(r"\s+#.*$", "", line).strip() for line in joined.splitlines()]
    commands = [line for line in commands if line and not line.startswith("#")]
    text = "\n".join(commands)
    CHECK.assertNotIn("--frozen", text, "ci.sh uses --frozen, which skips the lockfile check")
    CHECK.assertNotIn("--no-sync", text, "ci.sh uses --no-sync, which can run a stale environment")
    CHECK.assertIsNone(re.search(r"\bpip3?\s+install\b", text), "ci.sh installs with pip instead of the lockfile")
    uv_commands = [line for line in commands if re.search(r"\buv\s+(sync|run)\b", line)]
    CHECK.assertTrue(any(re.search(r"\buv\s+sync\b", line) for line in uv_commands), "ci.sh never runs uv sync")
    for line in uv_commands:
        if "--no-project" in line:
            continue  # the built-artifact check runs outside the project and its lock
        CHECK.assertIn("--locked", line, f"ci.sh command is not locked: {line}")
    for line in commands:
        CHECK.assertIsNone(re.match(rf"(exec\s+)?(pytest|ruff|python3?|{re.escape(checker)})\b", line),
                           f"ci.sh runs a check outside uv run: {line}")
    for needle, label in (("ruff check", "ruff check"), ("pytest", "pytest"), (checker, "the type checker")):
        pattern = rf"(?<![\w-]){re.escape(needle)}(?![\w-])"
        CHECK.assertTrue(any(re.search(pattern, line) for line in commands), f"ci.sh does not run {label}")
    CHECK.assertTrue(any("ruff format" in line and ("--check" in line or "--diff" in line) for line in commands),
                     "ci.sh does not check formatting without rewriting files")


def check_sources():
    sources = sorted(Path("src").rglob("*.py"))
    CHECK.assertTrue(sources, "no package under src/")
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                CHECK.assertNotIn("annotations", [alias.name for alias in node.names],
                                  f"{path} imports annotations from __future__ on a 3.14 floor")
    tests = [path for path in Path("tests").rglob("test_*.py") if any(name.startswith("test") for name in functions(path)[0])]
    CHECK.assertTrue(tests, "no test functions under tests/")


def annotated(function, label):
    arguments = function.args.posonlyargs + function.args.args + function.args.kwonlyargs
    for argument in arguments:
        CHECK.assertIsNotNone(argument.annotation, f"{label} parameter {argument.arg} is not annotated")
    CHECK.assertIsNotNone(function.returns, f"{label} has no return annotation")


def returned(label, function, *args):
    """The candidate's result for a call the contract says must succeed."""
    try:
        return candidate_call(function, *args)
    except Exception as exc:
        raise AssertionError(f"{label} raised {exc!r}") from exc


def run_main(main, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = candidate_call(main, list(argv))
    return code, out.getvalue(), err.getvalue()


def check_behavior(project):
    sys.path.insert(0, str(Path("src").resolve()))
    package = candidate_call(importlib.import_module, "quota")
    remaining = getattr(package, "remaining", None)
    CHECK.assertTrue(callable(remaining), "quota.remaining is missing")
    for limit, used, expected in ((10, 3, 7), (0, 0, 0), (5, 5, 0), (5, 0, 5)):
        label = f"remaining({limit}, {used})"
        CHECK.assertEqual(returned(label, remaining, limit, used), expected, label)
    for limit, used in ((5, 6), (-1, 0), (5, -1), (True, 0), (5, False), ("5", 1), (5.0, 1)):
        with CHECK.assertRaises(ValueError, msg=f"remaining({limit!r}, {used!r}) must raise ValueError"):
            candidate_call(remaining, limit, used)
    module_name, _, attribute = project["scripts"]["quota-check"].partition(":")
    main = getattr(candidate_call(importlib.import_module, module_name), attribute, None)
    CHECK.assertTrue(callable(main), "the quota-check entry point does not resolve to a callable")
    CHECK.assertEqual(run_main(main, ["10", "3"])[:2], (0, "7\n"), "quota-check 10 3")
    for argv in ([], ["10"], ["10", "3", "1"], ["x", "1"], ["5", "6"], ["-1", "0"]):
        code, out, err = run_main(main, argv)
        CHECK.assertEqual((code, out), (2, ""), f"quota-check {argv} must return 2 with empty stdout")
        CHECK.assertTrue(err.strip(), f"quota-check {argv} must write a diagnostic to stderr")
    for name, function in (("remaining", remaining), ("main", main)):
        CHECK.assertIsInstance(function, FunctionType, f"{name} is not a plain function")
        defined, _ = functions(candidate_call(importlib.import_module, function.__module__).__file__)
        annotated(defined[function.__name__], name)


def new():
    CHECK.assertTrue(Path("pyproject.toml").is_file(), "pyproject.toml is missing")
    try:
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise AssertionError(f"pyproject.toml is not valid TOML: {exc}") from exc
    project = data.get("project", {})
    check_metadata(project, data)
    checker = check_dependencies(project, data)
    check_tool_settings(data, checker)
    check_ci(checker)
    check_sources()
    check_behavior(project)


def narrow():
    for name, digest in NARROW_TOOLCHAIN.items():
        CHECK.assertTrue(Path(name).is_file(), f"{name} was removed although the fix did not need it")
        CHECK.assertEqual(text_digest(name), digest, f"{name} changed although the fix did not need it")
    for name in MIGRATION_FILES:
        CHECK.assertFalse(Path(name).exists(), f"{name} added: a narrow fix must not migrate the toolchain")
    source = Path("windows.py").read_text(encoding="utf-8")
    try:
        ast.parse(source, filename="windows.py", feature_version=(3, 10))
    except SyntaxError as exc:
        raise AssertionError(f"windows.py uses syntax the project's Python 3.10 floor lacks: {exc.msg}") from exc
    spec = importlib.util.spec_from_file_location("windows", Path("windows.py").resolve())
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    candidate_call(spec.loader.exec_module, module)
    parse = module.parse_window
    for text, expected in (("0m", timedelta(0)), ("0h", timedelta(0)), ("0d", timedelta(0)),
                           ("15m", timedelta(minutes=15)), ("2h", timedelta(hours=2)),
                           ("1d", timedelta(days=1)), ("10d", timedelta(days=10))):
        label = f"parse_window({text!r})"
        CHECK.assertEqual(returned(label, parse, text), expected, label)
    for text in ("", "m", "5", "-5m", "05m", "00m", "5x", " 5m", "5m ", "5M", "1.5h"):
        with CHECK.assertRaises(ValueError, msg=f"parse_window({text!r}) must still raise ValueError"):
            candidate_call(parse, text)


if __name__ == "__main__":
    checks = {"new": new, "narrow": narrow}
    try:
        checks[sys.argv[1]]()
    except SystemExit as exc:
        raise AssertionError("candidate exited before contract checks completed") from exc
    print("contract passed:", sys.argv[1])
