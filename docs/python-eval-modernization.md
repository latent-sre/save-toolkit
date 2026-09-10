# Python and eval modernization — 2026-09-10

The measured first step is Python 3.14 in CI, current FastAPI, and a bounded Inspect AI + Inspect
SWE integration. The native fleet evaluator stays in place until its contracts have equivalent
evidence on a replacement. This branch is based on machinery PR #259, not the paperwork branch.

The separate [sandbox runtime upgrade](sandbox-runtime-upgrade.md) records the follow-up work
on the existing graph and AutoGen/A2A applications; it does not expand the Inspect pilot's scope.

## Runtime and dependency findings

- [verified] The unchanged repository passes on CPython 3.14.7: 674 tests passed, 5 skipped,
  1,055 subtests, 93.56 seconds. That is compatibility evidence, not a benchmark: the prior 3.12
  run took 92.86 seconds, but there were no repeated controlled timing trials.
- [sourced] Python 3.14.7 is the current maintenance release checked against the
  [official release page](https://www.python.org/downloads/release/python-3147/).
  Installed uv 0.11.31 only knew about 3.14.6; an isolated latest uv installed 3.14.7.
- [verified] Inspect AI 0.3.263 cannot resolve alongside FastAPI 0.116.1: it requires >=0.119.0.
  FastAPI 0.141.1 resolves with Inspect SWE 0.2.70 and the existing full development requirements.
  The latest FastAPI also removes the 123 deprecated `asyncio.iscoroutinefunction` warnings seen
  in the baseline. The HTTP fixture checks pass after the update.
- [sourced] Current FastAPI requires Pydantic v2; Pydantic v1 is unsupported on Python 3.14.
  See the [migration contract](https://fastapi.tiangolo.com/how-to/migrate-from-pydantic-v1-to-pydantic-v2/).
  [verified] The inspected HTTP assets already use v2; no v1 model migration was needed.
- [verified] Importing Inspect SWE is insufficient to prove readiness: an actual bridge request
  failed without the optional Anthropic SDK. It is now an explicit dependency, imported at task
  load time so absence is reported before sandbox startup. SDK 1.4.0 was checked with this bridge.
- [verified] The Python 3.14 sandbox image reports 3.14.7 and is recorded by digest in
  `evals/inspect-compose.yaml`. No global Python replacement or production runtime change was made.

## What Inspect replaces, and what it does not

The [documented Inspect SWE contract](https://inspect.aisi.org.uk/tutorial.html) supplies agents
as Inspect solvers in a sandbox. [Upstream Claude implementation](https://github.com/meridianlabs-ai/inspect_swe/blob/0.2.70/src/inspect_swe/_claude_code/claude_code.py)
confirms sandbox execution, proxied model requests, configurable versions, and retries that must
be disabled explicitly for a single attempt. The installed 0.2.70 signatures were also inspected.
Context7 supplied the public API contract; GitHits supplied source and package metadata.

| Existing responsibility | Direction | What remains to prove |
|---|---|---|
| Scheduling, epochs, progress, logs, viewing | Use Inspect in the pilot | Compare failure recovery and retained evidence before retiring native run publication |
| Agent execution and container lifecycle | Use Inspect SWE for the artifact pilot | Plugin packaging, actual advertised tools, hooks, credential boundary, and agent identity |
| Deterministic artifact scoring | Reuse seven existing fixture checks | Port the remaining nine checks without silently weakening coverage |
| Native Skill/Task routing and helper return | Keep the native runner | A proxied model conversation is not evidence of native host parity |
| Rubric judge and calibration | Keep current calibrated judge | Preserve calibration receipt, evidence quotations, model identity, and INCONCLUSIVE semantics |
| Source/provenance identity | Record scenario hash and package versions in the pilot | Bind full candidate/plugin and evaluator identities before acceptance use |

The pilot uses ordinary Claude Code, not the installed Save Toolkit plugin. Its score explicitly
says `artifact_only`, records omitted checks, and never promotes a candidate. Sandbox timeouts and
runtime exceptions remain sample errors, rather than being converted into agent PASS/FAIL scores.
It re-stages probe-owned input files after the agent finishes.

## Code improvements worth pursuing

The local static pass used Ruff 0.16.6 with `F,B,UP,SIM` and a Python 3.14 target. It reported
102 suggestions across scripts/evals. Three unused imports were removed; 99 suggestions remain.
The largest categories were 49 percent-formatting suggestions and 23 nested-with suggestions.
Those counts are lint output, not 102 validated defects. The six loop-closure warnings inspected
were synchronous test callbacks consumed within their loop iteration, not observed late-binding bugs.

1. **Move eval infrastructure to Inspect incrementally.** `build_probe.py` is 3,228 lines and the
   judge 901; the useful reduction is moving scheduling, sandbox lifecycle, and log handling to a
   maintained library while retaining the fleet-specific assertions. A thin pilot establishes the
   API before a replacement. Adding another orchestration framework would increase overlap.
2. **Use existing dependencies before adding more.** HTTPX, JSON Schema, PyYAML, and Pydantic are
   already present. Typed scenario/result boundaries could replace some loose-dictionary checking,
   but only with a negative-fixture parity test: validation order and failure wording are contracts.
   Do not introduce a second schema definition that can drift from the current validator.
3. **Keep the hook guard dependency-free.** Its isolated `python -I -S` execution is an installation
   contract. Adding Rich, Pydantic, or a YAML library there would break deployed hooks. The deliberately
   restricted frontmatter grammar also must not become general YAML without compatibility evidence.
4. **Use Python 3.14 features where they remove work.** Inspect already selects stdlib Zstandard
   support on 3.14 instead of its older-Python ZIP dependency. There is no measured CPU bottleneck
   supporting free-threaded Python or interpreter pools here. Native eval subprocess/API latency
   dominates; unbounded concurrency would also change cost and identity assumptions.
5. **Do not blindly modernize filesystem checks.** Cached `Path.info` cannot replace fresh stat calls
   around mutable fixtures, symlinks, and credential cleanup. Keep containment and reparse-point
   behavior covered on Windows. Similarly, new type-alias syntax would raise the deployed runtime
   floor where some scripts still intentionally support 3.11.

## Remaining limitations

PR #260 review follow-up: a Docker regression reproduced replacement of Python, test, and Bash
inside the original root container. The pilot now runs with a read-only system filesystem and all capabilities dropped;
the same regression proves all three replacements are denied and a missing solution scores zero.
Grading also fixes PATH and disables Python user-site/startup-path injection. Writable tmpfs mounts
allow fixture setup and agent installation without granting writes to system executables.
Inspect's root helper and agent retain the original root uid with zero effective capabilities.
Read-only system mounts protect grader binaries while writable temporary paths support installation.
Both sandbox FastAPI declarations now match the canonical 0.141.1 pin. The repository-only
dependency alignment test moved out of the container suite into ordinary CI and covers all three
sandbox requirements files. Their Python/Uvicorn/SSE upgrades remain a separate branch.
The additional executable-tampering regression and protection add 51 eval lines, raising that
ceiling from 11,503 to 11,554 without changing the skill or agent ceilings.

- [verified] Initial pilot Python 3.14.7 suite: 682 passed, 7 skipped, 1,055 subtests, one upstream warning,
  95.58 seconds. Two skips are the separately passed opt-in Docker smoke cases; the other five
  were already present. Gate A passed 4/4, all 76 native scenario definitions validated, and
  `uv pip check` reported all 129 installed development packages compatible.

- [verified] On this Windows host, Inspect's optional control server warns that `socket.AF_UNIX`
  is absent. The evaluation and log path still work. Do not claim the control surface was tested.
- [verified] Both opt-in Docker smoke tests passed in 91.21 seconds: a scripted correct solution
  passed all seven artifact checks; a response without a solution failed. These ran the real
  Claude Code binary through Inspect SWE with a mock provider, not a paid language model.
- [verified] An upstream Starlette/AnyIO deprecation warning remains after the FastAPI upgrade.
- [unverified] No paid model comparison, native-plugin parity run, free-threaded benchmark, or
  CI/Linux result is established by the local tests. The scripted bridge tests measure infrastructure.
- The larger dependency set is deliberate adoption cost: use the constrained test subset, rather
  than installing unrelated graph/autogen sandbox frameworks in CI. Package resolution alone does
  not prove every repository-owned sandbox application works on 3.14.
- The eval line ceiling increases from 11,288 to 11,503 for the pilot and its regression tests
  (220 net lines added, using five lines of existing headroom). Retire that
  additive cost as equivalent native infrastructure can be removed; do not count a pilot as a net
  simplification yet.

The next framework batch is recorded in [LangGraph upgrade verification](langgraph-upgrade.md).
