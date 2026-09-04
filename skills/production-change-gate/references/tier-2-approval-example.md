# Tier 2 approval example

Read only when the caller explicitly asks for a worked example/template or is preparing a Tier 2/3
approval-request packet. Never load this file merely to evaluate an already-prepared real change
packet. The parent `SKILL.md` owns classification, blockers, the verdict, and execution authority.
This example is `[unverified]` shape, not evidence from a foundation and not approval for any real
action.

> **Requesting approval for a human release owner to apply a Tier 2 change.**
>
> **Target**: `checkout` app, `prod` space, foundation `pcf-east`.
> **Change**: scale from 4 -> 6 instances to absorb the 502 burst while the root cause is investigated.
> **Exact command**: `cf scale checkout -i 6`
> **Valid until**: `<UTC>` — after this deadline the change re-enters approval.
> **Blast radius**: no restart of existing instances (`-i` only adds); ~40s until new instances pass
> health checks. No config or code changes.
> **Verification**: `cf app checkout` shows `6/6 running`; 502 rate in the dashboard drops within 5 min.
> **Rollback**: `cf scale checkout -i 4` — this restores the desired instance count; it does not
> reverse in-flight requests, external effects, or transient rebalancing.
>
> This is Tier 2 (reversible live change), so a human release owner needs explicit approval for this
> specific apply. Immediately before execution, that owner rechecks the target, command, actor, and
> current configuration identity against the approval. After the attempt, the owner returns an
> `executed`, `not executed`, or `UNKNOWN` receipt.
> I do not apply live changes or perform the reconciliation query.
> Meanwhile I'll continue the Tier 0 investigation of what changed, which needs no approval.
