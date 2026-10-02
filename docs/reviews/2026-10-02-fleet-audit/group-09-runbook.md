# Group 09: runbook — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting audit HEAD `8cbf3664f87a314e0373be287a515a4f542e15b1` contains preceding reports. Initial tree clean; this bundle matched the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains skills before agents, three per group, six passes each, with findings committed before continuing.

**Conclusion:** the authoring method is operationally useful and preserves strong evidence, human-approval, and recovery boundaries. The importer has two confirmed Medium defects: a default-write race can replace another writer's file, and HTML line breaks inside code blocks are silently removed. Explicit forced replacement is intentional and tested; its inconsistent documentation is a separate Low policy/documentation issue. The fixes can remain local to the converter and its calibration.

All six bundle files were read completely: `SKILL.md`, both assets, both references, and the 506-line `scripts/confluence_to_runbook.py`. The bundle is 57,980 bytes/1,073 lines, approximately 7,673 whitespace-delimited words including code; the entrypoint is 114 lines/1,073 words. `[verified]` means current source inspection or identified local execution; `[sourced]` means supporting external evidence; `[unverified]` means target/model/runtime facts not established. Only this scratch report was written by this reviewer. Parent-owned probes used disposable local inputs. No CF command, Confluence request, installation, credential access, product repair, or paid/native evaluation occurred.

## Pass 1 — suitability, routing, and neighboring responsibilities

**Sources:** complete `SKILL.md`; template and exemplar; `agents/scribe.md:25-42,141-177`; `discovery-runbook-incident-update.yaml`; bounded operational-learning and postmortem references.

[verified] The skill serves a concrete authoring job: one operational task/failure mode with triage, action, verification, recovery, and escalation. It distinguishes contact/link/wording corrections from procedure changes, preserving unrelated structure and history while requiring a version increment for changed steps or branches (`SKILL.md:16-27`). This avoids imposing a full-template rewrite on a small correction.

[verified] Scribe owns documentation; it never runs even a read-only command merely to validate the document. Human/software-engineer execution of the offline converter is named separately. Active investigation routes to the responder's incident workflow; retrospectives use postmortem; accepted knowledge closeout uses operational-learning; automation suitability uses toil reduction before implementation. A supplied resolved-incident record can directly authorize a runbook edit without manufacturing a closeout identifier.

**Gap:** the positive discovery scenario checks intended selection, not actual native-host behavior. The historical exact-fields command-evidence scenario shares EL-01's previously recorded limitation. LEARN-01's provenance binding and POST-R01's follow-up semantics remain separately owned; no duplicates are raised here.

## Pass 2 — technical contracts and factual correctness

**Sources:** complete converter; `confluence-import.md`; `living-runbooks.md`; exemplar; current official Confluence/OpenAPI and curl documentation through Context7; curl upstream documentation through GitHits; original Google SRE and HTML-standard pages. External sources checked 2026-10-02.

[sourced] Atlassian documents the v2 single-page endpoint, requested body representations under `body`, and version number/creation timestamp. This supports the importer's page-JSON shape and provenance extraction: [Confluence page API](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/) and [official OpenAPI specification](https://dac-static.atlassian.com/cloud/confluence/openapi-v2.v3.json). The team's edition, permissions, actual rendered page, and attachments remain `[unverified]`; the reference already exposes the edition gap. No server response was fetched.

[sourced] Curl prompts for a password when `--user` contains only the username. Its `--fail-with-body` option returns an HTTP error while retaining the response body, supporting RUN-R02 below. Context7 and GitHits agree; GitHits served `curl/curl` commit `3ae15e6`: [user option](https://github.com/curl/curl/blob/3ae15e6/docs/cmdline-opts/user.md#L20) and [fail-with-body](https://github.com/curl/curl/blob/3ae15e6/docs/cmdline-opts/fail-with-body.md#L18). This is documentary evidence, not an installed-curl or authentication test.

[sourced] The historical playbook claim is accurately attributed to Google's reported experience, not demonstrated for this fleet: [SRE introduction](https://sre.google/sre-book/introduction/). The [on-call workbook](https://sre.google/workbook/on-call/) supports maintaining playbooks alongside alerts and postmortem learning. The local three-repeat automation trigger is a team heuristic, not an externally established universal threshold.

[verified] The exemplar correctly computes a 14.4-times burn as two percent of a 30-day budget per hour, treats p95 as diagnostic, and distinguishes running processes from successful user requests. It withholds restart without headroom evidence and avoids clearing a dependency from a sparse log count. Its fictional-service disclaimer and version-3 versus version-4 rehearsal distinction are clear. RUN-01/RUN-02 below concern actual converter behavior, not those illustrative platform claims.

## Pass 3 — authority, trust, failure, and recovery

**Sources:** `SKILL.md:29-64,83-109`; template approval banner `38-46`; exemplar `94-179`; import reference `7-10,75-89`; converter `135-151,343-352,397-419,462-502`; scribe command-evidence boundary.

[verified] The guidance separates sourced syntax from verified execution. Verification dates require the exact version, target, actor, time, and passing outcomes; untraversed branches remain untested. New documents start draft with null dates. Human review controls promotion. The copied approval banner preserves incident-fast-path exclusions, ITO's existing coordination channel, security escalation, and full-gate treatment of ineligible actions.

[verified] Recovery includes partial success, stop conditions, requested versus observed state, irreversible process replacement, and an explicit limit on repeated scaling. Inspection precedes destructive action. Runbook drafting cannot create approval or operational evidence. Imported pages are untrusted data; redaction and rendered-page comparison remain human/document-review obligations.

[verified] The converter fetches no links, serializes owner metadata safely, lengthens code fences around embedded backticks, rejects dangerous destination schemes, exposes unmapped sections, and counts unsupported media/macros/attachments. These are valuable protections. They do not certify arbitrary HTML fidelity or redact every secret automatically. Imported commands stay unverified and drafts require review, reducing the immediate impact of RUN-02 without eliminating its correctness defect.

**Gap:** actual rehearsal, staffed escalation contacts, source edition/permissions, platform readiness, and human approval were not tested. Preserve these gaps instead of treating a successful conversion or schema check as operational readiness.

## Pass 4 — LLM readability, instruction consistency, and context cost

**Sources:** complete bundle; conditional reference and exemplar loading in `SKILL.md:16-27,83-102`; template/example parallel sections.

[verified] The entrypoint provides a useful edit-size decision before the full authoring method. The template makes expected output, partial/failed routes, bounds, rollback, and contacts visible. The worked example demonstrates uncertainty and escalation rather than filling every missing fact with a plausible command. Its size is justified for first/thin drafts; it need not be loaded for contact-only edits. The converter is an execution asset, not required prompt context for every authoring turn.

**Recommendation RUN-R01 — Low, high confidence; documentation/policy clarification:** `SKILL.md:99-102` and `confluence-import.md:48-49` describe unconditional overwrite refusal, but converter `477-486` and `test_confluence_import.py:612-620` intentionally support `--force`, including replacement of a file containing history. State the actual default and the explicit override's consequences. If policy should limit forcing to disposable drafts, document that decision and implement a corresponding check separately. Do not characterize an explicitly forced replacement as an accidental default write, or silently remove a tested feature under a documentation correction.

**Deletion-first recommendation RUN-R03 — Low, high confidence:** consolidate repeated accretion/rehearsal explanations between entrypoint `83-93` and `living-runbooks.md:9-35` while retaining a short entrypoint trigger and full protocol in the reference. Keep the standalone template approval banner and claim-specific evidence rules; they have independent readers. Do not add another publishing schema or restore retired learning identifiers without an actual consumer requirement.

## Pass 5 — verification quality and coverage boundaries

**Sources:** `scripts/test_confluence_import.py`; `scripts/test_runbook_schema.py`; complete `probe_runbook_slots.py`; `build-scribe-writes-only-docs.yaml`; `test_build_probe.py:110-121`; `test_researcher_scribe_cases.py:17-45`; README `322-339`.

[verified] Converter tests cover draft metadata, invalid IDs/owners, heading precedence, unmapped content, macros/media, safe link destinations, titles, nested list ownership, reversed/restarted numbering, code fences, JSON metadata, missing bodies, existing-file refusal/force, and Unicode output. Schema tests bind exemplar/template keys and approval banners and preserve quoted date representation. The tests intentionally do not restore the removed closed-object/catalog schema; that retirement is a declared policy choice.

[verified] The document oracle checks typed frontmatter, filled slots, numbered expected outputs, routed outcomes, sourced placeholders, bounds, rollback association, reachable escalation, evidence labels, and template leftovers. Scope checks keep edits in docs and prohibit Bash/commits. Separate calibration rejects newly invented verified execution even outside numbered steps. These establish structural and bounded evidence properties, not whether a recovery branch is operationally safe. Regex verb/branch recognition still requires responder review; a matching channel name does not prove staffing.

The parent's frozen-source baseline under Python 3.14.7 remains **1,470 passed, 19 skipped, one warning, 2,690 subtests**; scenario validation **192 specifications/737 expectations**, both exit 0. Fresh parent probes in `group-09-runbook-probe-results.json` establish the two defects below. No full-suite rerun or native model trial was performed. Existing breadth does not cover the default-write interleaving or `<br>` within preformatted commands.

## Pass 6 — adversarial findings and smallest repairs

### RUN-01 — default output check and write are not one exclusive operation

**Confirmed implementation defect; Medium severity; high confidence.** Local evidence: converter `484-496`; promised history protection in `confluence-import.md:48-49`; existing static-file control in `test_confluence_import.py:612-620`.

**Trigger → consequence:** the requested output does not exist when `main()` checks it. Another writer creates it while conversion runs. `write_text()` then opens it for replacement, losing that writer's runbook/history despite the caller not using `--force`. A routine concurrent import or document writer is sufficient. The violated contract is the default refusal to overwrite an existing artifact, especially one whose history is evidence.

**[verified] Reproduction:** parent invoked the real module with owned temporary inputs. Absent output succeeded with exit 0. Pre-existing history failed with exit 1 and preserved history. Injecting competing creation during the real `convert()` call, after the precheck, produced exit 0 and lost the sentinel/history. Explicit `--force` also replaced history, retained as the intentional control. No product file was touched.

**Smallest fix:** in default mode, create the output exclusively at the actual write boundary and fail clearly if it already exists; retain the early check only as an optional convenience. Keep explicit force behavior separate from the default, and preserve UTF-8 draft/provenance output. This repair does not by itself promise transactional recovery from every disk/write failure.

**Verification:** retain absent-output success, pre-existing refusal with byte equality, and explicit-force behavior; add the deterministic competing-creation case and require nonzero exit with the competing file unchanged. No timing-sensitive parallel test or real shared directory is needed.

### RUN-02 — HTML breaks inside a code block concatenate commands

**Confirmed implementation defect; Medium severity; high confidence.** Local evidence: converter `173-219,243-247,256-268`; code-preservation intent at `103-110,343-352`; import reference `51-56,80-89`; related newline/fence tests `225-233` and anchor-break tests `481-500`.

**Trigger → consequence:** a rendered/export HTML command block uses `<br>` or `<br/>` for a line break. The parser's break handling flushes ordinary text but adds nothing to `_pre`; subsequent data are joined directly. `<pre>cf app demo<br>cf events demo</pre>` becomes the single line `cf app democf events demo`. The draft changes command bytes without a conversion-loss warning. Its draft/unverified status prevents any claim of safe execution, but authors must discover and repair an avoidable silent corruption.

**[verified/sourced] Reproduction:** parent called the real converter with three otherwise equivalent local inputs. A literal newline was preserved; `<br>` and `<br/>` each concatenated the two commands. No CF command was executed. The independent [HTML standard](https://html.spec.whatwg.org/multipage/text-level-semantics.html#the-br-element) defines `br` as a content line break, supporting the expected conversion.

**Smallest fix:** when a break occurs inside preformatted content, preserve it as a newline before the ordinary prose/anchor handling. Keep existing suppression rules, code fencing, unverified labels, and source provenance; do not globally change anchor-break behavior to repair code blocks.

**Verification:** compare exact fenced command bodies for literal newline, `<br>`, and `<br/>`, including nested code markup and adjacent blank lines. Retain anchor-label, nested-list, embedded-backtick, media/macro suppression, and unverified-marker controls. If an unsupported code representation cannot be preserved, report its loss explicitly instead of silently joining it.

**Recommendation RUN-R02 — Low, high confidence; wording correction:** import reference `25-28` should say that `--fail-with-body` returns an error **and still writes the error body**, rather than suggesting it prevents saving an error page. Require checking curl's exit status before conversion; retain the missing-`body.view.value` rejection. Official docs and upstream evidence above suffice; no authenticated HTTP reproduction is necessary.

**Caller next step:** record RUN-01/RUN-02 and the qualified recommendations in the existing AUDIT-001 disposition, assemble the group 09 reports, and commit before group 10. Repair, publishing, and operational rehearsal remain separate from this findings-only audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
