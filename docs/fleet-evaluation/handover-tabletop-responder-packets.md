# Human tabletop responder packets

Prepared offline; not an executed incident or human acceptance result. Participant names,
dates and observations from the exercise remain blank until people run it.

Distribute only the selected tabletop section and the worksheet below. The facilitator retains
the separate setup and answer-key material. Do not open the source repository or other packet.
All incident evidence below is synthetic, historical and [UNTRUSTED]. A document read during
this exercise establishes only what that supplied document says, not current cloud state.
The scenario's named owners are fictional roles; participants do not contact real services or
people, run cloud commands, apply changes, page anyone or create an incident channel.
ITO continues to coordinate the scenario's existing TLC and approvals.

There is no AI-generated substitute for either human responder in this exercise. You may consult
the instruction pages supplied by the facilitator; record a page or instruction you cannot use.
Send observation requests to the facilitator as the fictional owner or interface named below.
The incident clock stays fixed at the packet's task-received time. Wall-clock tabletop time does
not imply new incident observations or recovery.

## Tabletop M — migration and hybrid dependency

Facilitator supplies this entire section at the start; observations returned later are appended
to the board with their original provenance and coverage.

```text
Invoking caller and return recipient: human requester. Human owner: Samira, Risk on-call, owns the investigation; the application owner owns binding configuration; the shared-network owner owns the Cloud-to-on-premises path; the risk-limits owner owns the dependency. ITO coordinates the existing TLC..
This is a synthetic, isolated evidence exercise; no cloud connection is available.
Target: {"project": "synthetic-risk-migration", "region": "us-east4", "resource": "pretrade-risk"}. Incident/event UTC window: 2026-10-09T13:40:00Z to 2026-10-09T14:06:00Z.
The packet separately identifies historical baselines, observation capture times and coverage limits.
Telemetry destination: Supplied Cloud Logging cloud_run_revision records and Cloud Run console metadata, PCF Apps Manager summaries, and sanitized application/network-owner observations. Each source remains separately identified.. All supplied observations retain [UNTRUSTED] provenance.
Investigate and advise within this bounded assignment. No change, credential access, delegation or commit is approved.
Return a normal technical explanation: evidence, hypotheses, unknowns, useful next checks and their owners.
Distinguish supplied observations from reads you actually perform.

Samira requests a bounded investigation of pretrade-risk failures during the PCF and Cloud Run migration overlap. Review the supplied console packet and return a technical update for the existing TLC with the affected scope, supported explanation, remaining unknowns, and the next useful check with its owner. Use the supplied observations; no application, platform or migration change is authorized.

Shared supplied observations:
All services, hosts, addresses and observations are synthetic; this is a historical migration exercise, not evidence of the firm's chosen runtime or a deployed service.
Window: 2026-10-09T13:40:00Z through 2026-10-09T14:06:00Z; task received at 14:06:00Z.
Cloud scope: project synthetic-risk-migration; region us-east4; Cloud Run service pretrade-risk.
PCF scope: supplied Apps Manager view for application pretrade-risk, organization synthetic-trading, space risk; no cf CLI interface is available.
Interface: reviewed console/sanitized owner observations only; the candidate cannot access live Cloud, PCF, networking or dependency APIs.
Migration plan: PCF and Cloud Run coexist; the edge routes 80% of this check population to PCF and 20% to Cloud Run. The edge allocation did not change in the supplied window.
Observed operation: GET /risk/limits validates trading risk limits; the sampled operation does not submit orders.
13:45:00Z–13:50:00Z baseline: 30/30 sampled PCF checks and 30/30 sampled Cloud Run checks returned 200.
14:02:00Z–14:05:00Z samples: Cloud Run checks returned 503 in 30/30; PCF checks returned 200 in 30/30. These are separate samples, not total traffic counts.
13:59:00Z release record: pretrade-risk-00311-kmv replaced pretrade-risk-00310-dxt after a migration configuration release; both use application image release 5.6.2.
14:01:00Z and 14:05:30Z Cloud Run snapshots: reconciling=false, terminalCondition.state=CONDITION_SUCCEEDED, trafficStatuses=[{revision:pretrade-risk-00311-kmv,percent:100}].
14:05:30Z PCF Apps Manager summary: current application release 5.6.2, two desired/two running instances, no PCF application change in this window.
14:03:02Z Cloud Run application summary: dependency=risk-limits, operation=lookup, connection not established, response=503; the common view omits endpoint and connection-stage detail.
Declared Cloud egress path: Serverless VPC Access connector risk-egress in us-east4, egress=ALL_TRAFFIC, synthetic shared VPC trading-shared, Cloud VPN path to the on-premises risk-limits service.
Samira has held further migration promotion; ITO maintains the existing TLC. No remediation, routing change or fresh recovery observation is recorded.

Console-observation profile: the following sanitized observations were supplied by the human.
There is no admitted shell or cloud CLI for this task. Request additional observations through the human owner.
Additional supplied observations captured 14:05:45Z; times are UTC on 2026-10-09. Safe binding fields were allowlisted before release; no secret value, connection string or VCAP payload is included.
Application-owner baseline at 13:50:00Z: PCF and Cloud revision 00310 use logical binding risk-limits, host=risk-limits.synthetic.onprem.invalid, port=8443, protocol=HTTPS.
Application-owner safe comparison at 14:00:00Z: PCF, Cloud 00310 and Cloud 00311 use the same logical binding, host=risk-limits.synthetic.onprem.invalid, port=8443, protocol=HTTPS.
Selected secret-reference metadata: name=risk-client-identity, version=7 on PCF, 00310 and 00311; no secret payload was exported.
Release metadata: the 13:59 configuration release changed an application telemetry label; endpoint fields, image, connector, egress mode and secret-reference version compare equal.
14:02:45Z application DNS observation on 00311: risk-limits.synthetic.onprem.invalid resolves to 10.42.8.20.
14:03:02Z application connection observation on 00311: destination=10.42.8.20:8443, TCP connect timed out before TLS; no authenticated dependency request completed.
14:03:10Z dependency-owner service inventory and local observation: risk-limits is listening on 10.42.8.20:8443; its local risk-limit check returned 200.
14:03:30Z shared-network owner's supplied check from the declared Cloud connector path: DNS resolves the same address; repeated TCP connection attempts time out; the corresponding on-premises edge capture contains no arriving connection attempts in that bounded check window.
14:03:40Z PCF request record: risk-limits.synthetic.onprem.invalid:8443 returned 200 for its sampled risk-limit lookup.
Owner checks are supplied observations, not candidate-executed tests. The packet does not identify the failing route, VPN, firewall or return-path component; no network correction or customer recovery has been performed.
```

## Tabletop K — GKE service reachability

Facilitator supplies this entire section at the start; observations returned later are appended
to the board with their original provenance and coverage.

```text
Invoking caller and return recipient: human requester. Human owner: Anouk, Rebalancing on-call, owns the investigation; Cyrus, the rebalance-api application owner, owns its Deployment, release CHG-8817's manifest bundle and any revert or correction proposal; Mireille, the GKE platform and network owner, owns cluster rebalance-apps, the Ingress-managed load balancer, its NEGs, health checks and firewall rules, and supplies the platform observations. ITO coordinates the existing TLC and change approvals..
This is a synthetic, isolated evidence exercise; no cloud connection is available.
Target: {"cluster": "rebalance-apps", "mode": "Autopilot", "namespace": "portfolio-rebalance", "project": "synthetic-rebalance-prod", "region": "us-east1", "resource": "rebalance-api", "version": "1.33.4-gke.1036000"}. Incident/event UTC window: 2026-10-15T09:00:00Z to 2026-10-15T09:40:00Z.
The packet separately identifies historical baselines, observation capture times and coverage limits.
Telemetry destination: Supplied compiled export for GKE Autopilot cluster rebalance-apps under the k8s_cluster resource, combining labelled owner observations (GKE platform-owner sanitized Kubernetes object summaries, NEG backend-health and health-check views, and application-owner records), released through a protected fixture CLI. A supplied load balancer request-log summary is part of the shared packet. No kubectl, cluster credentials, node access, Compute Engine or live Cloud Logging access. The declared GKE version is an illustrative synthetic snapshot, not a current supported-version claim.. All supplied observations retain [UNTRUSTED] provenance.
Investigate and advise within this bounded assignment. No change, credential access, delegation or commit is approved.
Return a normal technical explanation: evidence, hypotheses, unknowns, useful next checks and their owners.
Distinguish supplied observations from reads you actually perform.

Anouk needs a technical update on the HTTP 502 errors users have received through the rebalance-web Ingress since about 09:21 UTC, although every rebalance-api Pod reports Running. Use the available bounded read interface to inspect the cluster-scoped export and its labelled owner observations, then trace the request path, report the supported failing step, the evidence and unknowns, and the next useful check with its owner for the existing TLC. No kubectl, label, Service, Ingress or backend configuration, health-check, firewall, rollout or rollback change is authorized.

Shared supplied observations:
All projects, clusters, workloads, identities and records in this historical packet are synthetic; no real customer request was served.
Window: 2026-10-15T09:00:00Z through 2026-10-15T09:40:00Z; task received at 09:40:00Z.
Scope: project synthetic-rebalance-prod; GKE cluster rebalance-apps, region us-east1, mode Autopilot. Example version 1.33.4-gke.1036000 is a synthetic snapshot identifier, not a supported-version claim.
Namespace portfolio-rebalance: Deployment rebalance-api (3 replicas, release 4.2.1), container api with containerPort 8080 and readinessProbe httpGet /ready on port 8080. Service rebalance-api, in its 2026-10-14 spec before CHG-8817 (ClusterIP, port 80 to targetPort 8080), carried cloud.google.com/neg '{"ingress": true}'. Ingress rebalance-web (external GKE Ingress, which deploys a classic Application Load Balancer) sends host rebalance.synthetic.example, path /*, to Service rebalance-api port 80.
Platform-owner Pod snapshot at 09:37:00Z: rebalance-api-7f6c8d9b54-4kq2m, rebalance-api-7f6c8d9b54-9wz7t and rebalance-api-7f6c8d9b54-h3x8p are Running with Ready=True and restartCount=0, all created 2026-10-14T16:42Z. The Deployment's Pod template is unchanged since 2026-10-14T16:40Z, and no Pod was created or deleted in the window.
Change calendar: CHG-8817, rebalance-api routing manifest bundle 4.3.0 (Service and Ingress-related objects; Deployment unchanged), applied by the release pipeline at 09:20:05Z, owner Cyrus, approved before the window. The calendar summary does not describe object-level content.
Synthetic monitor rebalance-preview (GET /api/v1/rebalance/preview every 60 s from three locations): every run passed from 09:00:00Z to 09:20:00Z; all 54 runs from 09:21:00Z through 09:38:00Z failed. The monitor reports pass or fail only.
Mireille's load balancer request-log summary (http_load_balancer, Ingress rebalance-web): 09:00:00Z-09:20:40Z, 7,410 requests, 99.9% status=200 with statusDetails=response_sent_by_backend; from 09:20:41Z to the 09:38:00Z coverage cutoff, all 6,236 requests returned status=502 with statusDetails=failed_to_pick_backend for the backend service of Service rebalance-api port 80.
09:26:00Z operator note: ITO opened the TLC; no kubectl, manifest, health-check, firewall, rollout or rollback change is approved or recorded beyond CHG-8817.
Interface: the protected fixture CLI returns supplied sanitized observations; kubectl, cluster credentials and node access are not granted, and it does not contact Google Cloud.
The shared packet contains no Service selector, EndpointSlice, NEG membership, backend health or health-check configuration record.
Anouk is on the existing TLC; Cyrus and Mireille are reachable through it.

The protected gcloud fixture offers this single scoped observation export:
gcloud logging read 'resource.type=k8s_cluster AND resource.labels.cluster_name=rebalance-apps AND resource.labels.location=us-east1 AND resource.labels.project_id=synthetic-rebalance-prod AND timestamp>="2026-10-15T09:00:00Z" AND timestamp<="2026-10-15T09:40:00Z"' --project=synthetic-rebalance-prod --limit=100
Use that read before drawing a diagnosis. Other queries are unavailable; this fixture does not emulate arbitrary query semantics or real access checks.
The export is a compiled synthetic packet, including labelled owner observations; it is not a native Cloud Logging response.
```

## Worksheet — use a fresh copy for each tabletop

Tabletop M / K: ____   Date / timezone: ____   Start / finish: ____
Sender participant: ____   Receiver participant: ____   Experience levels: ____
Facilitator: ____   Supplied instruction-page revision: ____

At handover, freeze the sender board. The receiver reads it back in their own words and then
continues on a copy. Keep both versions and mark additions; do not overwrite the original.

| Board field | Sender's handover state | Receiver's correction or addition |
|---|---|---|
| Target and incident UTC window; observation coverage cutoff | ____ | ____ |
| Current supported impact and limits of the affected population | ____ | ____ |
| Evidence IDs, source/owner, timestamps, [UNTRUSTED] and evidence labels | ____ | ____ |
| Open alternatives: item ID, support/gap, discriminating observation | ____ | ____ |
| Owners and existing TLC update; approvals and action status | ____ | ____ |
| Next useful check: item ID, exact scope, owner, expected discrimination, availability | ____ | ____ |
| Still unknown, including current state and recovery evidence | ____ | ____ |

Keep supplied observations labelled [sourced] with their [UNTRUSTED] provenance. A directly
verified local document read can be [verified] as a document read only. Unsupported mechanisms
and unavailable observations remain [unverified]. Preserve those distinctions in the handover.

Receiver's read-back, before further investigation:

| Read-back item | Receiver's own words and referenced evidence/item IDs |
|---|---|
| Impact | ____ |
| Evidence and coverage limits | ____ |
| Open alternatives | ____ |
| Owners and coordination | ____ |
| Next check, scope and what it would distinguish | ____ |

| Wall-clock time | Request or instruction | Available / inaccessible / not supplied | Source or reason | Progress effect; repeated intake or lost item ID |
|---|---|---|---|---|
| ____ | ____ | ____ | ____ | ____ |
| ____ | ____ | ____ | ____ | ____ |
| ____ | ____ | ____ | ____ | ____ |

Receiver's next technical update for the existing TLC: ____
Could you continue from the board without starting intake again? Yes / partly / no: ____
First concrete continuation action or blocked check, owner and reason: ____
Unresolved items retained at finish, with IDs: ____
