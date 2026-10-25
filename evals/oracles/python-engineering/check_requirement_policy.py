"""Outcome checks for build-python-engineering-requirement-policy.

The policy uses requirement syntax (PEP 508 names and extras; PEP 440 specifiers). The cases cover
name normalization, zero padding, post and local releases, wildcard exclusion, compatible release,
extras, whitespace and comments: a hand-rolled comparison misses several of them. Environment
markers are left out: evaluating them on the checking host or rejecting them is a product decision
the prompt does not settle. Imports outside the standard library must be declared as runtime dependencies.
"""

import ast
import contextlib
import io
import json
import re
import sys
import tempfile
import tomllib
from pathlib import Path

from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))
import depcheck.cli as cli

INVENTORY = {
    "requests": "2.31.0",
    "urllib3": "2.0.7",
    "idna": "3.9",
    "Django": "4.3.0",
    "typing_extensions": "4.15.0",
    "zope.interface": "8.2",
    "bar-lib": "2.0.post1",
    "torch": "2.3.0+cu121",
    "uvicorn": "0.29.0",
    "attrs": "25.4.0",
    "click": "8.1.8",
    "foo": "1.0",
}
POLICY = """# platform policy, reviewed quarterly
requests>=2.31,<3

urllib3!=2.0.*
idna>=3.10
django~=4.2.0
Typing.Extensions<4.10
zope-interface>=8.0
bar_lib>2.0
torch==2.3.0
uvicorn[standard]>=0.30
attrs >= 23.1 , < 26
notinstalled>=1.0
foo==1.0.0
"""
VIOLATIONS = {"urllib3", "idna", "django", "typing-extensions", "bar-lib", "uvicorn"}
CLEAN_POLICY = "requests>=2.31,<3\nzope-interface>=8.0\ntorch==2.3.0\nfoo==1.0.0\nattrs>=23.1\n"


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = candidate_call(cli.main, argv)
        except SystemExit as exc:
            code = exc.code
    return (0 if code is None else code), out.getvalue()


def reported(stdout):
    return {normalize(line.split()[0]) for line in stdout.splitlines() if line.strip()}


with tempfile.TemporaryDirectory() as tmp:
    inventory = Path(tmp) / "inventory.json"
    inventory.write_text(json.dumps(INVENTORY), encoding="utf-8")
    policy = Path(tmp) / "policy.txt"
    policy.write_text(POLICY, encoding="utf-8")
    clean = Path(tmp) / "clean.txt"
    clean.write_text(CLEAN_POLICY, encoding="utf-8")

    code, stdout = run(["check", str(inventory), str(policy)])
    assert code == 1, f"violations present, expected exit 1, got {code!r}"
    assert reported(stdout) == VIOLATIONS, f"reported {sorted(reported(stdout))}, expected {sorted(VIOLATIONS)}"

    code, stdout = run(["check", str(inventory), str(clean)])
    assert code == 0, f"no violations, expected exit 0, got {code!r}"
    assert not stdout.strip(), f"no violations, expected empty stdout, got {stdout!r}"

    code, stdout = run(["list", str(inventory)])
    assert code == 0 and "requests 2.31.0" in stdout, "the existing list command changed"

stdlib = set(sys.stdlib_module_names)
imported = set()
for source in Path("depcheck").rglob("*.py"):
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module.split(".")[0])
third_party = imported - stdlib - {"depcheck"}
project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
declared = {normalize(re.split(r"[\s\[<>=!~;@]", spec, maxsplit=1)[0]) for spec in project.get("dependencies", [])}
undeclared = {normalize(name) for name in third_party} - declared
assert not undeclared, f"runtime imports not declared in [project].dependencies: {sorted(undeclared)}"
print("requirement policy: PASS")
