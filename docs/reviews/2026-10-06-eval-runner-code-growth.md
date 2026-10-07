# Eval runner code growth from the package split

Date: 2026-10-06. Compares the runner before the split, `432f0db5` (one file, `evals/build_probe.py`),
with `936f268c` (the `evals/build_probe.py` entry point and the `evals/probe/` package), on PR #328.
Roadmap item: EVAL-011. Under DEC-20 ([delivery plan](../fleet-evaluation/delivery.md)) the owner
reviews evaluation-code growth before work expands; this note is the input to that review.

## Conclusion

[verified] The runner grew 53% in lines, 23% in statements and 19% in code tokens, but its logic grew
about 5%. The rest is reformatting, the cost of turning one file into 16 modules, type annotations
for strict mypy, and features the split added on purpose. The split was expected to make the runner
smaller. It removed duplication, but less than each new module, type and declaration costs. The
owner's options are at the end.

## Method

Measured with Python 3.14.7 on the committed files:

- **Lines:** physical lines.
- **Statements:** `ast` statement nodes.
- **Code tokens:** Python tokens of the `ast.unparse` output, so layout and comments never count.

Docstrings are removed before statements and tokens are counted. The formatting effect is the old
file run through Ruff 0.16.10 with this repository's settings: 120 columns, Python 3.12. To repeat
the measurement at a later milestone, run this from the repository root with the revisions to compare
as arguments:

```python
import ast
import io
import subprocess
import sys
import tokenize

LAYOUT = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING,
          tokenize.ENDMARKER}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", check=True).stdout


def runner_size(rev: str) -> tuple[int, int, int]:
    """Lines, statements and code tokens of the eval runner at `rev`; docstrings and layout never count."""
    lines = statements = tokens = 0
    for name in git("ls-tree", "-r", "--name-only", rev, "evals/").split():
        if name != "evals/build_probe.py" and not (name.startswith("evals/probe/") and name.endswith(".py")):
            continue
        source = git("show", f"{rev}:{name}")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(
                    getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
                body[:1] = [] if len(body) > 1 else [ast.Pass()]
        lines += len(source.splitlines())
        statements += sum(isinstance(node, ast.stmt) for node in ast.walk(tree))
        tokens += sum(t.type not in LAYOUT for t in tokenize.generate_tokens(io.StringIO(ast.unparse(tree)).readline))
    return lines, statements, tokens


for rev in sys.argv[1:]:
    print(rev, *runner_size(rev))
```

## Results

[verified]

| Revision | Lines | Statements | Code tokens |
|---|---|---|---|
| `432f0db5`, before the split | 4,357 | 2,713 | 38,172 |
| `934de2a5`, the split | 6,526 (+50%) | 3,283 (+21%) | 44,266 (+16%) |
| `936f268c`, with the code-review fixes | 6,677 (+53%) | 3,350 (+23%) | 45,313 (+19%) |

The code-review fixes (`d4cc889f` and `936f268c`) account for 151 lines, 67 statements and 1,047
tokens of the growth.

### Where the lines went (+2,320)

- **Reformatting, 885.** Ruff takes the old file alone from 4,357 to 5,242 lines without changing its
  code. The file had 85 lines over 120 characters, the longest 199, and Ruff gives each argument of
  a call that does not fit its own line.
- **The entry point, 329.** It is a new file. 238 of its lines are the imports that re-export 212
  names, so code that imports `build_probe` keeps working.
- **The 16 modules, 1,106 more than the reformatted old file:** 174 lines of imports, 161 of
  docstrings, and about 770 of new code, blank lines included.

### Where the statements went (+637)

| Cause | Change |
|---|---|
| Imports between modules, and the entry point's re-exports | +194 |
| Function headers and returns, as 182 functions became 272 | +186 |
| Classes and their fields, as 8 classes became 33 | +146 |
| Logic: every other statement | +111 (+5%) |

### Where the code tokens went (+7,141)

| Cause | Change |
|---|---|
| Type annotations for strict mypy | +1,636 |
| Imports between modules, and the entry point's re-exports | +1,345 |
| `@declare(...)` on each of the 32 checks | +615 |
| Everything else: logic, class bodies, function headers and the review fixes | +3,545 (+10%) |

### What the split's new features cost

Gross sizes at `936f268c`; some of this replaced code the old file already had.

| Feature | Lines | Tokens |
|---|---|---|
| Grading loop: `Expectation`, `Graded`, `plan`, `assess` and their helpers | 177 | 1,371 |
| Subcommands, including the old-flag parser kept for compatibility (43 lines, 199 tokens) | 161 | 998 |
| Check declarations: `Need`, `CheckType`, `declare`, and the rules and lookups around them | 113 | 885 |
| Typed outcomes and enums (`outcomes.py`) | 141 | 805 |
| Pydantic record models | 122 | 739 |
| Patch guard on the entry point | 23 | 146 |

## Why the split did not shrink the runner

The split removed three kinds of duplication:

- the hand-kept tables of forbidding, requiring and regradable checks;
- the regrade's second grading loop;
- the "could not measure" text tests scattered through the file.

The expectation that the runner would get smaller counted those removals. It did not count the
imports, annotations and declarations each new module needs, or the reformatting. [verified] The net
figures above show the removals were smaller than the additions.

## Options for the owner (DEC-20)

- **Drop the entry point's re-export list and patch guard:** about −260 lines and −700 tokens. The
  11 test modules that import `build_probe` would import from `probe` instead.
- **Drop the old flat flags** (`--validate`, `--regrade DIR` and the rest): −43 lines and −199 tokens,
  but the old command lines stop working.
- **Judge growth by tokens or statements:** line counts mostly reflect the formatter.
- **Keep the types and the check declarations.** The declarations hold each check's polarity and the
  evidence it reads, which the result rules depend on; the types are what strict mypy checks.
