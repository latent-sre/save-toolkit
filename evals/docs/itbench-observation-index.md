# WP04 observable index profile

[sourced] `prepare-native --evidence-profile indexed-v1` and `--evidence-profile indexed-v2` add
the same deterministic, observable-only view to the unchanged released files. The default `raw`
profile retains its existing scenario and receipt format. Indexed scenarios have their selected
profile as a suffix, while their submitted benchmark case IDs remain unchanged. This is a different
evidence representation and prompt condition, not a raw-profile result or an index-only causal
experiment. The implementation is in [native.py](../itbench_adapter/native.py).

[sourced] `indexed-v2` is an opt-in execution profile. Its prompt expressly permits ordering
explicitly zoned, comparable timestamps using their stated zones, while prohibiting inferred
offsets or relationships to unknown-zone clocks. `indexed-v1` retains its original clock wording.
Both use the unchanged `indexed-v1` observation index format and decoder; the originals and all
derived files are identical for the same source manifest.

[sourced] `indexed-v3` retains the v2 clock guidance and adds the opt-in `lookup-catalog-v1`
extension to the underlying `indexed-v1` format. Its JSONL catalogs keep each observation's
provenance, context and payload together when the whole row fits the byte limit. Original files
and existing content locators, record tables, resource inventories and histories remain available.
V3 has distinct scenario IDs and receipt metadata; it does not change raw, v1 or v2 outputs.

[sourced] `indexed-v4` adds `resource-field-history-v1` to v3. It groups observed typed field
values across each exact resource's separate object and event streams, with a complete observation
ledger behind the occurrence positions. Valid embedded JSON object/array strings also have a
separate normalized view; exact literal strings remain available. This avoids searching raw
serialization whitespace to compare a configuration field. It introduces no new tool or service.

[sourced] `indexed-v5` selects `resource-field-history-v2`. It provides explicit whole-directory
resource/field search scopes and places complete small value histories directly in field entries,
with a complete paginated fallback for larger histories. The v1 field view and indexed-v4 outputs
remain available and unchanged; v5 has its own scenario and receipt identity.

[sourced] `indexed-v6` selects `lookup-catalog-v2` together with field-history v2. Object and event
catalog pages are grouped by exact reported resource identity, preventing neighboring resources
from sharing a selected JSONL file. Logs and alerts retain their existing flat catalogs. Every
record, duplicate, source link and clock remains available; this is a distinct execution profile.

The indexed prompt explains pagination, explicit UTC versus unknown-zone clocks, and that all
records are released together: later timestamps may exist in the bundle even though no additional
conversation turn will be released. Tools remain Read, Grep, Glob and Skill. No executable parser,
shell grant, external service or changed Linux sandbox is introduced.

## Prepare without model execution

```bash
.venv/bin/python evals/itbench_pilot.py prepare-native \
  --manifest evals/manifests/wp04-itbench-five.json \
  --source /path/to/validated-source-cache \
  --destination /path/to/new-indexed-fixtures \
  --receipt /path/to/indexed-preparation.json \
  --evidence-profile indexed-v1 \
  --max-prepared-bytes 2147483648
```

Select `--evidence-profile indexed-v2` and new destination/receipt paths to prepare the revised
clock prompt. Existing `raw` and `indexed-v1` preparations keep their original identities.
Select `--evidence-profile indexed-v3` for the additional lookup catalogs. Their JSONL files,
page metadata and extended index count toward the same prepared-byte budget.
Select `--evidence-profile indexed-v4` for resource field histories as well. All additional
directories, values, observation ledgers and occurrence locators count toward that byte budget.
Select `--evidence-profile indexed-v5` for the revised search scopes and inline histories.
Select `--evidence-profile indexed-v6` to also use resource-scoped object/event record catalogs.

The explicit byte budget covers serialized fixture YAML, including original and derived evidence.
The destination must be new and separate from the source cache. A failed preparation does not
publish a partial destination. This command does not run a candidate, grant spending or accept a
case. The normal admission, candidate/runtime binding and campaign gates still apply.

[verified] Stage only the selected generated indexed YAML in the isolated native runner's
`build-scenarios/` directory. The runner loads the catalog before filtering `--scenario`; keeping
all expanded multi-gigabyte fixtures there caused a measured memory-cgroup termination. Keep the
other generated cases outside that catalog, or in lossless archives with decoded hash verification.
The campaign launcher now checks that no other indexed case is expanded before a model run.

## Candidate-visible structure

Start at `observations/index.json`. It points to paginated sources, records and resource inventories.
Each table reports its total, offset, returned count and next page. Follow `next` until null;
one page is not complete coverage. Resource histories preserve source/physical order and keep all
duplicate observations. They do not claim a single temporal ordering across unknown-zone collector
times and embedded event clocks.

Records retain source path/hash and physical start/end lines, including multiline CSV records.
Actual resource kind/namespace/name/UID are distinct from an event's referenced subject and from
type names mentioned inside a CRD. Collector time, embedded event timestamps, creation time,
resource version and watch lifecycle remain separate fields.

Content pages are bounded. A record locator either identifies a complete line range or explicitly
identifies every numbered fragment and how to reconstruct the content. Fragments are not standalone
complete records. Kubernetes Body JSON is decoded; embedded configuration JSON strings and log
attribute strings remain literal. Original source files remain available for exact byte inspection.

The decoder supports Kubernetes object/event TSV, application-log TSV, alert arrays and successful
wrapped alert responses. Full alert response envelopes are preserved. Malformed inputs, unsupported
sources, failed response statuses, duplicate JSON keys, and exhausted byte limits fail explicitly.
No inferred clock offset, root ranking, causal interpretation or answer-guided selection is added.

## V3 lookup catalogs

[sourced] Start at `observations/index.json` → `extensions.lookup-catalog-v1.catalogs`. The
paginated category table lists `object`, `event`, `log` and `alert_snapshot`, with record counts,
full-payload and locator-only counts, and a `first` page metadata link. Empty categories have zero
counts and a null link. Each metadata page gives `total`, `offset`, `returned`, `rows` (the JSONL
file) and `next` (the next metadata page). Follow continuations until null; a page or search excerpt
does not establish complete coverage.

[sourced] Each JSONL line is one observation, including its unique record ID, source path/hash and
physical line span, existing typed context and clocks, resource identity when applicable, and
content locator. Every record appears once in its category, including repeated observations.
An alert snapshot remains one complete source observation, preserving its array or response
envelope. No category, resource kind, name, cause or scoring metadata selects the retained rows.

[sourced] `payload_complete:true` includes the complete decoded `fields` payload, so literal
searches can find observed names, timestamps, messages, status and configuration on the same line
without the original CSV quoting. Nested configuration strings and log strings remain literal
JSON string values. Each UTF-8 JSONL line and file fits the index's page byte limit. If the full
row exceeds that limit, `payload_complete:false` omits `fields` entirely and retains the content
locator for complete reconstruction, including every fragment. The same size rule applies to
every resource kind. Nothing is silently truncated, and an unmatched search cannot exclude
values in omitted payloads. Metadata that cannot fit also refuses preparation explicitly.

## V4 resource field histories

[sourced] Follow `observations/index.json` → `extensions.resource-field-history-v1.directory`.
The directory preserves exact resource identities and links each resource's `streams` table.
Object and event streams are separate. Each stream reports its observation count and links
`ledger`, `fields` and `views` tables; every table uses the existing total/offset/returned/next
pagination contract. The extension's `coverage` link describes whole-profile counts and limits.

[sourced] A ledger row retains the original record and adds a one-based `position`. Field entries
identify a `view` and JSON Pointer `path`, present/absent counts, and a `values` table. Values are
typed, distinguishing strings, booleans, numbers, null, containers and absence. Container values
retain object keys or array length; child paths retain contents and order. A value group's
occurrences use inclusive `[start, end]` position ranges, or a paginated `ranges_table`, with exact
occurrence and range counts. These positions refer to that stream's ledger. Grouping equal values
retains every observation, including nonconsecutive recurrence and duplicates.

[sourced] The `resource` view contains the actual resource body, unwrapping an explicit watch
envelope. `export` retains the other source columns and `watch` retains envelope fields. A string
that wholly parses as a strict JSON object/array gains a separate decoded view with a parent view
and source pointer. Its exact literal is still in the base view. Decode status distinguishes
ordinary strings, invalid JSON and size/depth limits. View availability is separate from field
absence: an unavailable decode is not an absent field. Field absence is calculated only across
observations where that view is available.

[sourced] Fractional/exponent numbers in the auxiliary decoded views use an exact signed integer
`coefficient` and integer `exponent`, meaning coefficient × 10^exponent. Equivalent spellings
share a value; unequal decimals and nonzero underflow values remain distinct. This does not change
the legacy source parser or base-view number representation. An unsupported numeric range marks
that auxiliary view unavailable; its original literal remains intact.

[sourced] Large typed values use complete bounded content locators. Original source links remain
available for exact-byte inspection. Base coverage is complete only for successfully prepared
inputs; normalization completeness is reported separately. Preparation refuses excessive structural
depth or total output size. Auxiliary JSON decoding has explicit depth, nested-layer and byte
limits, and never infers an offset, latest state, root cause or relationship between resources.

## V5 search scopes and inline histories

[sourced] The `resource-field-history-v2` extension supplies `resources_search.directory`, `glob`
and `resource_count`, alongside the first resource-directory page. Search that whole directory
for a bare name or `resource_path`, not a whitespace-dependent JSON expression or only the first
page. `resource_path` is a display label in namespace/kind/name form (kind/name for cluster-scoped
objects). Exact structured identity and UID remain authoritative; equal labels do not merge records.

[sourced] Each stream similarly supplies `fields_search.directory`, `glob` and `field_count`.
A field entry contains either the complete `values` list inline or `values_table` pointing to all
groups through the normal pagination contract. It never includes a partial preview. Individual
large values can still use `value_locator`; occurrence ranges can still use a separate complete
table. Searching field names across the declared directory covers all field-index pages, not every
external payload. Read the selected complete entry and any indicated value/occurrence locators.

[sourced] The inline decision uses the same serialized-entry sizing rule as the bounded table
writer. All groups must fit; otherwise the full table is used. The profile retains exact numbers,
view-availability/absence distinctions, source-bound ledgers, all duplicate observations and the
same tool/grading boundaries. Group counts and positions still do not establish chronology or cause.

## V6 resource-scoped record catalogs

[sourced] `extensions.lookup-catalog-v2.catalogs` lists all four categories with complete record,
full-payload and locator-only counts. Object/event categories link `resource_groups` and provide
whole-directory `resources_search` and `rows_search` descriptors. Each group retains its exact
reported kind/namespace/name/UID, display path, counts and first page metadata link. Each page
metadata repeats that identity beside total/offset/returned/rows/next; all JSONL rows in the page
belong to it. Continue through every group page needed for the comparison.

[sourced] An event group uses the referenced subject, while each row retains the actual Event's
identity separately. A missing UID stays unknown and is not merged with a known UID. Equal reported
identities with missing UID remain an unknown-UID group; grouping does not prove physical continuity.
Rows in one file may have different observation times and values. File identity prevents mixing
neighbors, but does not make the first row current or establish a causal relationship.

[sourced] Logs and alert snapshots keep their existing files and descriptors byte-for-byte. Their
named fields, including empty identifiers, remain part of each full row. Query filters still limit
what a negative search establishes. V1 catalogs remain the default; `scoped_lookup` is opt-in and
requires lookup catalogs to be enabled. There is no cause, entity-name or field-value selection.

## Evidence boundary and qualification

Manifest/hash/path checks run before indexing. The decoder accepts already validated observable
contents, not filesystem paths or evaluator bindings. Ground truth and scoring metadata never enter
the derived files. Keep the preparation receipt outside candidate fixtures; its hashes bind the
generated files and their profile.

[sourced] The v2 receipt distinguishes the execution condition (`evidence_profile: indexed-v2`)
from the underlying index format (`observation_index_profile: indexed-v1`). Each scenario's
`derived_evidence.profile` and candidate-visible `observations/index.json` retain `indexed-v1`.
`source_observation_profile` preserves the manifest's source profile independently of either
selection; source asset hashes and the manifest hash continue to bind provenance. V1 receipts
retain their existing fields without the new `observation_index_profile` field.

[sourced] V3 receipts identify `evidence_profile: indexed-v3`, `observation_index_profile:
indexed-v1` and `observation_index_extensions: [lookup-catalog-v1]`. Each scenario's
`derived_evidence.extensions` also names the extension, while its `profile` remains `indexed-v1`.
The root index extension reports complete record coverage separately from full-payload coverage.
The decoder's `lookup_catalog` option defaults to false; existing execution profiles do not enable it.

[sourced] V4 identifies both extensions in the scenario and receipt. Its field-history option is
also off by default. The field-history view covers Kubernetes resources and their subject events;
alerts and logs continue through the existing catalogs. Source-order positions do not establish
event-time order, and grouping repeated values does not remove their observations or establish a
single latest state. A history that has not been completely read remains a coverage gap.

Offline tests cover provenance, record identity, multiline CSV, duplicate/lifecycle observations,
misleading nested type names, paginated reconstruction, malformed/error inputs, byte limits, hidden
file separation, and raw-profile compatibility. These checks establish representation behavior only.
Whether the index improves diagnosis requires a separately bounded native comparison, source-bound
operational review and human exact-candidate disposition. Existing cases are development replays;
they cannot become fresh held-out evidence by changing the representation.

[verified] [Native preparation tests](../test_itbench_native.py) pin raw and indexed-v1 serialized
fixture and receipt hashes, and compare v2's full original/derived evidence with v1. They check
distinct v2 scenario IDs and receipt profiles, explicit-zone ordering guidance, the distinction
between later records and further conversational releases, and invalid-profile refusal.
[CLI tests](../test_itbench_cli.py) exercise opt-in profile selection and refusal before publication.
These checks do not establish a diagnosis-quality improvement for v2.

[verified] [Observation tests](../test_itbench_observations.py) cover v3 catalog provenance,
duplicate retention, complete small payloads, literal search, reconstruction of oversized records,
continuations, UTF-8 line/page bounds and byte budgets. Native tests also freeze v2's fixture and
receipt hashes and exercise v3 with hidden sources absent. These checks establish representation
behavior, not a diagnosis-quality improvement for v3.
