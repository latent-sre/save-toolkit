# HOST-002 VS Code probe — procedure and evidence template

**This file is a blank instrument, not evidence.** No probe result or verdict has been recorded, and
every result field is empty for the operator who runs the probe to fill in. It contains exactly one
recorded observation, and it is not a probe result: the Step 3 instrument-calibration note, which
reports that the drift detector was exercised against a throwaway copy before this procedure asked
anyone to rely on it. It is labelled and scoped where it sits.

- **Supports:** `HOST-002` in [`fleet-roadmap.md`](../fleet-roadmap.md) — that entry is the authority
  for scope and acceptance. This procedure does not restate, narrow, or replace it; it only makes the
  observation mechanical.
- **Why a procedure exists:** HOST-002's acceptance requires observing a running VS Code UI. Nothing
  in this repository can do that. The probe is a human, five-minute, observation-only run.
- **What it does not do:** it starts no live effect, wires no hook, and edits no canonical or
  generated source. It has two local mutation surfaces. The agent-file write-back tested in Step 3 is
  restored and re-verified there. The second is easy to miss: enabling a tool may instead write a
  user- or workspace-scope VS Code settings entry, which lives outside the repository, so
  `git status` and the Step 6 reset both read clean while your profile stays changed. Record and
  revert it explicitly.
- **Recorded as fields, not checkboxes.** An unchecked box in this repository reads as unfinished
  work; a blank field reads as unrecorded, which is what it is. An empty field never means "no."

---

## 1. Preconditions

### 1.1 The build the HOST-002 claims came from

HOST-002's Base A evidence was read directly out of one installed bundle:

- VS Code **1.133.0**
- Build commit **`a5b500951314efd502d07465bd138dfbd714a960`**
- Bundle read: `<install>/<build>/resources/app/out/vs/workbench/workbench.desktop.main.js`

### 1.2 Record the build actually tested

Open **Help > About** and copy the `Version` and `Commit` values verbatim.

```text
Version:
Commit:
OS / build:
Architecture:
```

`code --version` prints version, commit, and architecture on three lines and is easier to paste — but
it resolves whichever `code` is on `PATH`, which is not necessarily the window you are probing. If you
use it, say so, and prefer Help > About when the two disagree.

**A different build invalidates nothing and blocks nothing.** It must simply be recorded, and the
results then belong to that build. Two consequences, both mechanical:

- If the commit differs from `a5b500951314efd502d07465bd138dfbd714a960`, the Base A bundle-search
  claims were not re-derived against your build. Do not carry them forward as if they were; re-derive
  or mark them `[unverified]` for this build.
- One build's observed behavior is not the host's contract. Say "on 1.x.y commit `abc…`", never
  "VS Code does X".

### 1.3 Workspace state

```text
Checkout SHA (git rev-parse HEAD):
Working tree clean at start (git status --porcelain empty)?  yes / no:
Workspace folder opened in VS Code (repository root)?  yes / no:
Workspace trust granted (workspace settings applied)?  yes / no:
Probe date / time (America/Chicago):
Operator:
```

A clean tree at the start is what makes Step 3 legible: any modification you see afterwards came from
the probe. The fleet under test is **this checkout** — [`.github/agents/`](../../.github/agents) and
[`.vscode/settings.json`](../../.vscode/settings.json) — not an installed plugin release.

---

## 2. Observation script

Run the steps in order. Steps 2 and 3 must not be reordered: Step 2 records the offered set *before*
anything is toggled, and Step 3 is what does the toggling.

### Step 0 — Identity

Fill in §1.2 and §1.3 before opening a chat session. If you stop early, the recorded steps are still
valid evidence; the unrecorded ones stay blank and their matrix rows stay inconclusive.

### Step 1 — Do all 8 agents appear in the Chat agent picker?

The eight files in [`.github/agents/`](../../.github/agents) are, in directory order:

`observability-engineer`, `prompt-engineer`, `repository-investigator`, `researcher`, `reviewer`,
`scribe`, `sde`, `sre`.

Open the Chat view's agent/mode picker (the control next to the chat input that selects the mode or
custom agent) and record what is listed. Record the exact label shown — the host may prefix, suffix,
or re-case the name.

```text
Where the picker was found (exact UI path):
observability-engineer   present? ___   label shown:
prompt-engineer          present? ___   label shown:
repository-investigator  present? ___   label shown:
researcher               present? ___   label shown:
reviewer                 present? ___   label shown:
scribe                   present? ___   label shown:
sde                      present? ___   label shown:
sre                      present? ___   label shown:
Any agent listed that is NOT one of the eight:
Notes:
```

### Step 2 — With `sre` selected, does the tools picker offer a terminal/execute tool?

This is the load-bearing question. [`.github/agents/sre.agent.md`](../../.github/agents/sre.agent.md)
declares `tools: ["read", "search", "agent"]`; `execute` is deliberately absent. `sre` is the only
canonical role whose read-only posture depends on that absence on this host (`observability-engineer`
is the second guarded role and declares `["read", "search", "edit", "agent"]`).

Select `sre`, open the tools picker (the tool/configure control on the chat input), and record what is
offered — **toggle nothing yet.**

```text
Where the tools picker was found (exact UI path):
Tool groups / entries listed for sre (verbatim):

Is any terminal / shell / run-command / execute entry present?  yes / no:
If present, is it enabled or disabled by default?  enabled / disabled:
Exact name of that entry as shown:
```

Present-but-off and absent-entirely are different answers with different consequences — record which
one you saw, not "no execute".

### Step 3 — If you enable a tool from the picker, does the agent file change on disk?

With `sre` still selected, enable the **terminal/execute** entry if Step 2 found one; otherwise enable
any single entry `sre` omits (`edit`, `web`, or `todo`). Record which one you enabled — two operators
enabling different tools can see different write-back behavior, so the answer is not reproducible
without it. Then, in a terminal at the repository root:

```text
git status --porcelain .github/agents/
git diff -- .github/agents/sre.agent.md
```

```text
Tool enabled (exact name):
git status --porcelain .github/agents/ output (verbatim):

Is .github/agents/sre.agent.md listed as modified?  yes / no:
The tools: line before / after (paste both):

Any OTHER file modified (repo or user settings) — exact path(s):
```

Then restore and confirm the tree is clean:

```text
git checkout -- .github/agents/sre.agent.md      # or: git stash
git status --porcelain                            # expect: no output
python scripts/gate_a.py                          # expect: PASS summary
```

```text
git status --porcelain output after restore (expect empty):
Gate A summary line after restore:
```

**Instrument note — already verified, and not a probe result.** On 2026-08-12 the drift detector was
exercised in a throwaway copy of this checkout (never in the repository itself) by editing
`.github/agents/sre.agent.md` to `tools: ["read", "search", "execute", "agent"]` — the exact shape a
write-back would produce. `python scripts/validate_fleet.py` went `PASS` → `FAIL (1 issue(s))` with
`.github/agents/sre.agent.md: generated output drift`, and back to `PASS` once reverted. A CRLF-
written variant added a second line, `.github/agents/sre.agent.md: generated file carries a CR byte`.
So if a write-back survives your restore, [`gate_a.py`](../../scripts/gate_a.py) will name the file —
a silent residue is not a failure mode this step has. `[verified]`

### Step 4 — Does a session-level tool override reinstate a tool the agent file omits?

Precondition: the tree is clean again after Step 3.

With `sre` selected, use the session tool selection to enable the terminal/execute tool, then ask `sre`
to run one **read-only** command. Use this prompt verbatim:

```text
Run `git status` and paste the output.
```

```text
Was a terminal/execute tool call actually made?  yes / no:
Tool call name as shown in the transcript:
Command that ran (verbatim) and its output:

Did the agent refuse, or answer without running anything?  describe:
Did .github/agents/sre.agent.md change again (git status --porcelain .github/agents/)?  yes / no:
```

**Isolate the override from the write-back.** If enabling the tool also rewrote the agent file, then
this step has *not* demonstrated a session-scoped override — it demonstrated a file edit applied
through the UI. Record that explicitly:

```text
Did the enabling action leave .github/agents/sre.agent.md unchanged?  yes / no:
```

HOST-002's Base B also names two override paths that are not the picker: a prompt file carrying its own
`tools:` list, and a chat deep link that sets agent and tools together. Both are `[sourced]` at one
remove and neither is required for this probe. Record only what you actually tried:

```text
Prompt-file override tried?  yes / no / not tried  — result:
Chat deep-link override tried?  yes / no / not tried  — result:
```

Restore the session state before continuing (turn off any tool you enabled) and re-check the tree:

```text
git status --porcelain output:
```

### Step 5 — Do the 29 skills load?

[`.vscode/settings.json`](../../.vscode/settings.json) registers
[`platforms/copilot/skills`](../../platforms/copilot/skills) through `chat.agentSkillsLocations`. That
directory holds 29 skill projections. Produce the expected list rather than trusting a list typed into
this document:

```text
Get-ChildItem platforms/copilot/skills -Name     # PowerShell
ls platforms/copilot/skills                       # bash
```

Open the skills surface in chat and compare against that output.

```text
Where the skills surface was found (exact UI path):
Number of skills offered:
Names offered in the UI but NOT in platforms/copilot/skills:
Names in platforms/copilot/skills but NOT offered:
Was workspace trust granted (workspace settings applied)?  yes / no:
```

### Step 6 — Does a handoff resolve to another agent, or fork the same one?

Select `sde` and use this prompt verbatim:

```text
Have scripts/check_links.py reviewed for correctness and security, and report the findings.
```

Then expand the subagent tool call in the transcript and read its arguments.

```text
Selected agent when asked:
Prompt used (verbatim, if you deviated from the above):
Was a subagent tool call made at all?  yes / no:
Tool name as shown:
Is an agentName argument present in the call arguments?  present / absent:
If present, its exact value:
Which agent is the response attributed to in the UI?
```

**Why this matters, and why "it looks like a handoff" is not the answer.** HOST-002 Base A records
that `runSubagent`'s `agentName` is `"Optional name of a specific agent to invoke. If not provided,
uses the current agent."` When it is omitted, the call forks the **current** agent. A delegation can
therefore degrade into `sde` answering as `sde` while the transcript still reads like a review handoff.
The distinguishing evidence is the argument, not the tone of the reply — so record `present`/`absent`
from the expanded tool call, and record the attribution separately. If the two disagree, record both
and say they disagree.

### Step 7 — Hook surface (evidence only, optional)

HOST-002 records `chat.hookFilesLocations`, `chat.useHooks`, and `chat.useClaudeHooks` as present in
the Base A bundle. Search Settings for each and record presence only.

```text
chat.hookFilesLocations present in Settings?  yes / no:
chat.useHooks present in Settings?            yes / no:
chat.useClaudeHooks present in Settings?      yes / no:
```

**Do not wire a hook in this probe.** Any hook-portability finding here is evidence only. Whether a
Copilot hook payload can scope to an exact agent identity is *not* observable from the settings list,
so leave that question unanswered rather than inferred; [`hooks/copilot-hooks.json`](../../hooks/copilot-hooks.json)
stays empty until a probe shows otherwise, and wiring one is separate work with its own review.

---

## 3. Interpretation guardrails

Apply these before the matrix, or the matrix will launder an inference into a measurement.

- **A UI absence proves the UI, not the enforcement.** "The picker did not offer it" is `[verified]`
  about the picker and `[unverified]` about whether the model can reach the capability another way.
- **A skipped step is inconclusive, never a "no".** Its matrix row stays inconclusive. A skip among
  Steps 2, 3, and 4 leaves HOST-002 open on that row, because those are the questions its acceptance
  names. Steps 1, 5, 6, and 7 are additional observations and do not gate HOST-002; skipping them
  records nothing and blocks nothing.
- **A model not calling a tool is evidence about the model, not the host.** A single turn that
  produces no command has at least three non-enforcement explanations: the model declined, it
  answered from context, or the call failed for an unrelated reason. Absent an observed *host-side*
  denial — a refusal, a permission prompt, an error naming the tool — record `inconclusive` and retry
  at least twice. Key this on the tool-call presence you captured in Step 2, never on whether output
  appeared.
- **Do not upgrade a Base B `[sourced]` claim on the strength of a different observation.** Each
  clause needs its own observation, or it keeps its one-remove label.
- **One build.** Every conclusion carries the version and commit recorded in §1.2.
- **No single row authorizes editing [`AGENTS.md`](../../AGENTS.md).** That edit is HOST-002's closure
  step and must cite the build and the transcript.

---

## 4. Outcome matrix

The `AGENTS.md` limit under test states, in the honest-limits list, that a VS Code `tools:` list is a
default rather than a boundary: that omission disables the tool for the model, that a workspace
agent's list loses to session tool selection, to a prompt file's own list, and to a chat deep link,
that the tools picker writes the user's change back into the `.agent.md` file, and that the real
enforcement on that host is policy-delivered Copilot managed settings.

Three dispositions are available per row: **confirmed** (observation matches the limit), **strengthen**
(the limit understates the gap), **replace with measured behavior** (the limit overstates or
mis-locates the gap). A fourth, **inconclusive**, changes nothing.

### From Step 2 — is `execute` offered to `sre`?

| Result | Meaning for the `AGENTS.md` VS Code limit |
|---|---|
| No terminal/execute entry offered at all | The omission is respected at the picker level on this build. Says nothing yet about session override — the limit's "loses to session tool selection" clause is untested by this row; carry it to Steps 3–4 before any disposition |
| Offered, disabled by default | Consistent with "a default, not a boundary": the omission narrows the default. **Confirmed** for this clause only |
| Offered and already enabled without operator action | The omission does not even set the default. The limit understates the gap → **strengthen**, and re-state `sre`'s host posture with the observation cited |
| Picker unavailable / not found | **Inconclusive.** Name the blocker; HOST-002 stays open on this row |

### From Step 3 — does the picker write back to `.github/agents/sre.agent.md`?

| Result | Meaning for the `AGENTS.md` VS Code limit |
|---|---|
| The file is modified | The write-back clause is **confirmed** by observation; its label moves from Base B `[sourced]` to `[verified]` **for the recorded build**, and the hard rule warning that a UI click can fail the drift gate keeps its footing |
| The file is unmodified | The clause did not reproduce here → **replace with measured behavior**, scoped to this build, and re-scope the drift-gate warning to the builds where it does reproduce rather than deleting it on one negative |
| A different file is modified (user settings, another agent file) | **Replace with measured behavior** and name the exact path — the drift-gate warning depends on *which* file is written |
| Restore left `git status` dirty or Gate A failing | Not a finding about the limit. Stop and restore the tree before continuing; the instrument note in Step 3 names the message to expect |

### From Step 4 — does a session-level override reinstate the omitted tool?

| Result | Meaning for the `AGENTS.md` VS Code limit |
|---|---|
| Override reinstates it and `sre` actually runs the command | The core clause — `tools:` is a default, not a boundary — is **confirmed** by observation; managed settings remain the only stated real control |
| Override offered, the command does not run, and you observed a **host-side denial** (refusal, permission prompt, or an error naming the tool) | The limit overstates the gap **for the path you tried** → **replace with measured behavior**, scoped to this build, and name the paths not tried (prompt file, deep link) so the replacement claims no more than was measured |
| Override offered, the command does not run, and there is **no** host-side denial | **Inconclusive — change nothing.** The model may have declined, answered from context, or failed for an unrelated reason. Retry at least twice; if no denial ever appears, record `inconclusive` and leave the limit standing. A security limit is not weakened by a model's silence |
| The enabling action also rewrote the agent file | The override was not isolated. Record it as a file edit through the UI, not as a session override; this row is **inconclusive** until a non-file-mutating path is tried |
| No override path found | **Inconclusive.** The clause keeps its `[sourced]` Base B label and is not upgraded |

### From Step 6 — does the handoff resolve?

| Result | Meaning |
|---|---|
| Subagent call with `agentName` naming `reviewer`, response attributed to `reviewer` | Named delegation resolves on this build. A routing finding for HOST-002's packet; **no tools-limit change follows** |
| Subagent call with `agentName` absent, response attributed to `sde` | The unscoped-delegation risk reproduces in practice. Record as measured behavior in the packet; again a routing finding, **not** a tools-limit change, and it does not by itself authorize any fleet edit |
| No subagent call at all | `sde` answered inline. Records nothing about `runSubagent`; retry once with an explicit request, then record **inconclusive** |

### From Step 5 — do the skills load?

| Result | Meaning |
|---|---|
| All 29 offered | Workspace skill registration works on this build |
| Fewer, or none | A packaging/registration finding for the roadmap, **not** a tools-limit finding. Record the count and whether workspace trust was granted before diagnosing further |

---

## 5. Evidence record (fill in)

```text
Build tested — Version:                        Commit:
OS / build:
Checkout SHA:
Tree clean at start?                           Tree clean at end?
Gate A after the probe (summary line):
Probe date / time (America/Chicago):
Operator:
Steps completed:                               Steps skipped (and why):
```

### Claims

One row per load-bearing claim. `[verified]` means you saw it in this session on the build above;
`[sourced]` means it cites a file, line, or bundle search you did not re-derive; `[unverified]` means
assumption or could not check. Labels never move up in transit.

| # | Claim | Label | Basis (what you saw, where) |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

### Disposition of the `AGENTS.md` VS Code limit

```text
Per §4, the disposition this run supports (confirmed / strengthen / replace / inconclusive):
Clause(s) it applies to:
Clause(s) still resting on Base B [sourced] evidence:
Proposed wording change (or: none — the limit stands as written):
```

### What I did NOT observe

State the gaps plainly; an unrecorded step is a gap, not a negative result.

```text
-
-
-
```

Candidates to name here when they apply: any step left blank; whether the model can reach a capability
the picker does not list; enforcement under Copilot managed settings (a policy surface a repository
cannot grant itself, and out of scope for this probe); the shape of any hook payload; behavior on any
build other than the one recorded above; whether the same results hold for
`observability-engineer`, the second guarded role.

---

## 6. Reset before you close the session

```text
Tools enabled during Steps 3–4 turned back off?  yes / no:
git status --porcelain (expect empty):
python scripts/gate_a.py summary line (expect PASS):
Any user- or workspace-scope settings entry the picker created — reverted?  yes / no / none seen:
  exact key(s):
Live systems touched (expect: none):
```

Anything left dirty in [`.github/agents/`](../../.github/agents) is drift the byte gate will reject on
the next change, and the operator who runs it next will not know it came from a UI click.

The settings line is separate from `git status` on purpose. A user-scope write lands outside this
repository, so `git status` and Gate A both report clean while your VS Code profile stays modified —
the one residue this checklist would otherwise certify as absent.
