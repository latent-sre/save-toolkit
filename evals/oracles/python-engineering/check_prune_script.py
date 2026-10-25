"""Outcome checks for build-python-engineering-small-script.

The script must stay one standard-library file that runs alone with `python -I`, keep its original
--keep behavior, and implement --older-than (outside the newest --keep AND older than DAYS) and
--dry-run (prints `would delete <path>`, deletes nothing).
"""

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path("tools/prune_backups.py")
DAY = 86400

tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
imported = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imported |= {alias.name.split(".")[0] for alias in node.names}
    elif isinstance(node, ast.ImportFrom):
        assert not node.level, "the script must not use relative imports"
        imported.add((node.module or "").split(".")[0])
outside = imported - set(sys.stdlib_module_names)
assert not outside, f"the script must run on a bare interpreter; non-stdlib imports: {sorted(outside)}"


def seed(directory):
    now = time.time()
    ages = {"a.tar.gz": 1, "b.tar.gz": 2, "c.tar.gz": 4, "d.tar.gz": 6, "e.tar.gz": 9, "f.tar.gz": 20}
    for name, days in ages.items():
        path = directory / name
        path.write_bytes(b"x")
        os.utime(path, (now - days * DAY, now - days * DAY))
    (directory / "notes.txt").write_text("keep me", encoding="utf-8")


def run(script, *args):
    return subprocess.run(
        [sys.executable, "-I", "-B", str(script), *args],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )


def remaining(directory):
    return sorted(path.name for path in directory.iterdir())


with tempfile.TemporaryDirectory() as tmp:
    deployed = Path(tmp) / "host" / "prune_backups.py"
    deployed.parent.mkdir()
    shutil.copy2(SCRIPT, deployed)
    result = run(deployed, "--help")
    assert result.returncode == 0, f"the copied single file does not run alone: {result.stderr[-400:]}"

    archives = Path(tmp) / "dry"
    archives.mkdir()
    seed(archives)
    before = remaining(archives)
    result = run(deployed, str(archives), "--keep", "2", "--older-than", "5", "--dry-run")
    assert result.returncode == 0, f"dry run failed: {result.stderr[-400:]}"
    planned = {Path(match).name for match in re.findall(r"(?m)^would delete (.+?)\s*$", result.stdout)}
    assert planned == {"d.tar.gz", "e.tar.gz", "f.tar.gz"}, f"dry run planned {sorted(planned)}"
    assert remaining(archives) == before, "the dry run deleted files"

    archives = Path(tmp) / "real"
    archives.mkdir()
    seed(archives)
    result = run(deployed, str(archives), "--keep", "1", "--older-than", "5")
    assert result.returncode == 0, f"pruning failed: {result.stderr[-400:]}"
    assert remaining(archives) == ["a.tar.gz", "b.tar.gz", "c.tar.gz", "notes.txt"], remaining(archives)

    archives = Path(tmp) / "keep-only"
    archives.mkdir()
    seed(archives)
    result = run(deployed, str(archives), "--keep", "4")
    assert result.returncode == 0, f"--keep alone failed: {result.stderr[-400:]}"
    assert remaining(archives) == ["a.tar.gz", "b.tar.gz", "c.tar.gz", "d.tar.gz", "notes.txt"], remaining(archives)
    assert "deleted" in result.stdout, "the original deletion report disappeared"
print("prune script: PASS")
