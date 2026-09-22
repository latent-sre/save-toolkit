# Sources and applicability

Checked 2026-09-21 for this method. These sources guide analysis; they neither set company policy
nor demonstrate performance of this skill. Recheck when their advice becomes a disputed requirement,
the method changes, or target platform behavior matters. Use current platform documentation for
version-specific mechanisms.

| Primary source | Application here |
|---|---|
| [Google SRE: Non-Abstract Large System Design](https://sre.google/workbook/non-abstract-design/) | Concrete assumptions, capacity, failure domains and design tradeoffs; estimates remain models |
| [Google SRE: Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) | Overload, retry amplification, degraded operation and recovery after overload |
| [Google SRE: Testing for Reliability](https://sre.google/sre-book/testing-reliability/) | Discriminating tests and their coverage limits |
| [Google SRE: Implementing SLOs](https://sre.google/workbook/implementing-slos/) | User outcomes and stakeholder-owned reliability targets |

Public skill research informed the organization, not authority or defaults. The
[review template](https://github.com/magnus919/agent-skills/blob/504f33a079161b4550e616e670b5320cef94aaad/site-reliability-engineering/templates/reliability-design-review.md)
and [failure-mode example](https://github.com/daemon-blockint-tech/Agentic-Enteprises-Skill/blob/526df1c1377ee392ce2448c370d597c42da75402/site-reliability-engineer/references/release_reliability_chaos.md)
were inspected as ideas. This is an original, scoped method. Generic timing, rollout, incident-command
and production-action rules from those examples are not adopted.
