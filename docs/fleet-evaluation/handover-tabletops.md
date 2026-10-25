# HANDOVER-001: two human tabletop packets

[verified] Prepared offline against main `b4bb96a7`; neither tabletop has been executed.
This is the finite preparation for HANDOVER-001 and the human portion of
[AC-35](measurement.md#acceptance-catalog), following
[the GCP human-use requirement](gcp.md#branching-investigations-and-human-use).
It does not complete the separate branching-investigation work or provide a human acceptance
result. No model call, real cloud observation, simulated responder result or live change is needed
for this packet.

## Schedule and participants — fill before execution

| Field | Fill in |
|---|---|
| Human exercise owner and final disposition owner | ____ |
| Less-experienced responder, relevant experience | ____ |
| Experienced responder, relevant experience | ____ |
| Facilitator; retains the hidden key and records assistance | ____ |
| Date, timezone, location/call and accessible worksheet location | ____ |
| Tabletop M start; Tabletop K start | ____ ; ____ |
| Instruction-page revision and paths supplied | ____ |
| Owner-selected private evidence destination | ____ |

Use the same two human responders. In M, the experienced responder starts and hands over to the
less-experienced responder. In K, reverse those roles. The facilitator can play the fictional
owners solely to release existing packet observations and record questions. They do not provide
an extra investigating responder, open a new bridge, or take over ITO's coordination role.
ITO owns the scenario's existing TLC, team paging, updates and approvals; participants prepare
the technical board and a TLC update without contacting real teams.

Reserve two 45-minute sessions and a 10-minute break: 100 minutes total.

| Elapsed time in each session | Activity and retained artifact |
|---|---|
| 0–5 min | Confirm roles, readable packet and worksheet; give sender only the selected packet and agreed instruction pages. Record any access difficulty |
| 5–17 min | Sender investigates the supplied observations and builds the board; record requests, unavailable evidence and instruction problems |
| 17–22 min | Freeze sender board; receiver gets that board, the same selected packet and instruction pages. Receiver reads back impact, evidence, alternatives, owners and next check; sender answers factual handover questions, then becomes silent |
| 22–34 min | Receiver continues from a copy of the board, makes or scopes the next useful check and prepares the next technical update for the existing TLC |
| 34–45 min | Facilitator and humans compare both boards, record assistance and difficulties, and fill the outcome rows below |

If the sender runs out of time before finding a cause, hand over the incomplete board anyway.
Measure whether the receiver can continue; do not teach the missing conclusion at handover.
Do not inject recovery, a new incident event or a new approval because the exercise clock moves.

## Responder distribution and exact source identity

Give responders only the selected M or K section of
[the responder packets](handover-tabletop-responder-packets.md), its worksheet, and the agreed
instruction pages. Do not distribute this facilitator document, the full repository, generated
YAML fixtures, review records, alternate variants or family JSON. The selected responder prompt
is copied verbatim from its existing YAML `prompt`; only the outer exercise instructions and
blank worksheet are added. The receiver gets no new cause information as a handover aid.

[verified] The cases are accepted members of the existing 64-case catalog, according to the
[catalog acceptance record](../../evals/oracles/gcp/README.md). Both are held-out families;
these packets do not move either family into tuning. A person exposed to a key records that
exposure and does not act as an independent blind assessor of that same family later. Keep the
packets out of model prompts and candidate-visible skill bundles.

| Tabletop | Exact accepted case | Accepted case digest, also verified on current source |
|---|---|---|
| M: migration/hybrid | `build-gcp08-migration-coexistence-b` | `002a390ae700d59df0404b33d9c518aa7219afdafe0a6ae28e43c9b6fd2df0bc` |
| K: GKE reachability | `build-gcp27-service-reachability-a` | `21aa89a7bc10a20a949b7b7b0240eb923b714b5c41ca4ecfd548711533f7af71` |

[verified] Both `fingerprints.case_digest` values match their YAML at acceptance revision
`9147ff91`. These are case digests, not raw-file SHA-256 or a claim of later human execution.
The selected GKE exercise measures reachability; it does not claim separate workload-identity
coverage. The scenario's GKE Autopilot version is a synthetic historical identifier, not a
current supported-version statement. The migration case does not select the firm's runtime.

## Facilitator packet M — migration and hybrid dependency

- **Initial view:** release the entire M section, including its already-supplied console
  observations, at minute 0. The accepted console case has no staged read interface; do not
  withhold part of its prompt or claim a new branching profile.
- **Target:** synthetic project `synthetic-risk-migration`, region `us-east4`, Cloud Run service
  `pretrade-risk`; PCF app `pretrade-risk`, org `synthetic-trading`, space `risk`.
- **Incident clock:** task received at 2026-10-09 14:06:00Z; window 13:40–14:06Z. Preserve individual
  observation timestamps and the sample-population limits instead of treating that whole window
  as an observed outage duration.
- **Available interface:** supplied console and sanitized owner observations only. Requests for
  facts absent from the packet receive: “Not supplied in this exercise; record the requested
  observation and its owner.” This is an evidence gap, not an observed API denial or new event.
- **Instruction pages:** supply accessible copies of
  [gcp-ops](../../skills/gcp-ops/SKILL.md), its
  [migration reference](../../skills/gcp-ops/references/cf-to-cloud-run.md), and
  [incident-investigation](../../skills/incident-investigation/SKILL.md), at the recorded revision.
  Record additional relevant instruction requests and whether they could be served. Page access
  is not permission for live reads or changes.
- **Handover opportunity:** an unresolved cross-owner investigation can continue by preserving
  scope, evidence and a discriminating owner request. Exhausting the supplied observations is
  not a reason to invent a network result or mark the service recovered.
- **Hidden key, facilitator only:** [GCP-08 family record](../../evals/oracles/gcp/families/gcp08.json),
  variant `b`, fields `review.b` and `controls.b`; compare supported conclusions, next checks,
  unsupported claims and unknowns. The responder already has `common_evidence` and
  `decisive_evidence.b` through the accepted prompt. Do not disclose `review`, `controls`, variant A
  or the [pilot answer record](../../evals/oracles/gcp/PILOT.md).

## Facilitator packet K — GKE service reachability

- **Initial view:** release the entire K section at minute 0. It contains the common observations
  and its one exact protected read. Do not supply the decisive export until requested.
- **Target:** synthetic project `synthetic-rebalance-prod`, region `us-east1`, GKE Autopilot cluster
  `rebalance-apps`, namespace `portfolio-rebalance`, application `rebalance-api`, Ingress
  `rebalance-web`. Preserve those selectors in requests and handover.
- **Incident clock:** task received at 2026-10-15 09:40:00Z; window 09:00–09:40Z. The accepted export
  has separate object, health-view and log coverage cutoffs; these do not advance during play.
- **Available read:** the exact `gcloud logging read` command printed in the K packet. The human
  requests it from the facilitator; they do not run it against a real account. On that request,
  return `[UNTRUSTED] Synthetic, scoped observation export; no live API call.` followed verbatim
  by `decisive_evidence.a` from the hidden family file below. Record the request and release time.
  This is the existing compiled fixture export, not a native Cloud Logging response. If requested
  in ordinary words, point to the printed read and record the assistance; do not silently claim
  the accepted fixture supports arbitrary query aliases.
- **Unavailable requests:** other queries, kubectl, cluster credentials, node access and live APIs
  are unavailable in this fixture. Say “Fixture observation unavailable: only the declared bounded
  export is supplied; no observations returned.” Record the limitation; do not substitute an
  invented denial from Google Cloud. Requests for later state or additional owner facts are
  recorded as not supplied, with their intended owner.
- **Instruction pages:** supply [incident-investigation](../../skills/incident-investigation/SKILL.md)
  and the frozen case's declared interface instructions. Record requests for missing GKE guidance
  as instruction-access observations; do not imply this repository supplies unrestricted cluster
  or node procedures. The absence of a page is not a diagnosis of the incident.
- **Hidden key, facilitator only:** [GCP-27 family record](../../evals/oracles/gcp/families/gcp27.json),
  `review.a`, `controls.a` and the
  [catalog answer record](../../evals/oracles/gcp/CATALOG.md). Release only `decisive_evidence.a`,
  never the key or alternate variant. The existing
  [fixture YAML](../../evals/build-scenarios/build-gcp27-service-reachability-a.yaml) embeds both
  wrapper source and additional observations, so it is not a responder handout.

## Assessment — complete once for M and once for K

Observe actual human handover. Compare the frozen sender board, receiver read-back and final
receiver board with the selected family key. Mark **retained**, **corrected**, **lost**, or
**not assessable**, and cite a board item plus an observed utterance or artifact; do not assign
a pass because a blank template contains the right headings.

| Item | M: observed result and evidence | K: observed result and evidence |
|---|---|---|
| Impact: scope, sampled population and current-state limits read back accurately | ____ | ____ |
| Evidence: source, timestamps, coverage, provenance and supplied-versus-performed distinction retained | ____ | ____ |
| Alternatives and unknowns: open item IDs retained without inventing a cause | ____ | ____ |
| Owners: investigation, application, dependency/platform and existing TLC responsibilities retained | ____ | ____ |
| Next check: named owner, exact scope and discriminating purpose read back and usable | ____ | ____ |
| Inaccessible instruction/page or unusable instruction: exact request, reason and effect | ____ | ____ |
| Repeated intake: question, whether answer was on sender board, and time/progress lost | ____ | ____ |
| Lost open items: sender item IDs absent or materially changed in receiver state | ____ | ____ |
| Continuation: first concrete check/request or TLC update, time to reach it, assistance needed | ____ | ____ |
| Could work continue? yes / partly / no; specific blocker or enabling evidence | ____ | ____ |
| Unsupported claims, proposed unauthorized action or coordination difficulties observed | ____ | ____ |
| Participant feedback in their own words | ____ | ____ |

An unavailable new observation can still leave a useful continuation: a scoped request to the
correct owner that preserves uncertainty. Distinguish that from inability to understand the
board or instructions. The facilitator records every hint; assisted continuation stays visible.
Missing recovery evidence stays unknown, even if a participant proposes an approved future fix.

Retain each dated participant roster, supplied packet/instruction revisions, observation-release
log, sender board, receiver read-back notes, final receiver board and filled assessment in the
owner-selected private destination. Record any consented recording location; notes suffice and
no recording is required. The human owner records a qualitative disposition and any concrete
difficulty needing repair. Two tabletops cannot estimate fleet-wide reliability, and an AI
summary or model trial cannot replace the two human handovers.

## Preparation evidence and remaining human action

[verified] Source YAML prompts were copied byte-for-byte into the responder document; no new
incident observation was authored. Both source case digests match acceptance revision `9147ff91`.
The responder document contains no family/review/control link or answer-key field. The K read
release is the existing fixture output, checked offline against `decisive_evidence.a`.

[unverified] Participant usability, actual read-back, retained open items and continuation have
not been observed. To run: the human owner fills the two responder names, facilitator, date and
session times, chooses the private evidence destination, and confirms the frozen instruction
pages are readable. The facilitator then runs M and K, records the real results and returns
them to the human owner for disposition. Preparation alone does not close HANDOVER-001.
