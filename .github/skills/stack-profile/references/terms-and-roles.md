# Terms and roles

| Term or role | Team meaning and boundary |
|---|---|
| Blast radius | Reach across users/requests/services/environments; name targets and counts. Small scope never lowers a production-change tier, which follows reversibility and access-path effects. |
| Golden signals | Latency, traffic, errors, saturation. RED: rate/errors/duration for requests; USE: utilization/saturation/errors for resources. |
| Human release owner | Assigned production executor and rollback owner; named on the change record when required. Incident fast path may defer that record, not the role. Default holder/rota remains unrecorded. |
| Platform team | Operates PCF internals under the parent platform boundary. Escalate evidence; the fleet does not operate the foundation. |
| Human security incident owner | Receives suspected compromise/abuse escalation. Preserve evidence instead of restarting; no fleet agent owns security response. Title/rota remains unrecorded. |
| ITO (IT Operations) | Runs the open TLC: requests updates, pages responder-named teams and approves incident changes. It does not investigate or direct investigation. The team has no standing incident lead or commander. |
| TLC (Techline Chat) / bridge | Existing incident coordination channel. Carry it forward; provide findings/specialist requests there without opening another channel or assigning command to the responder. ITO approves incident changes there. |
