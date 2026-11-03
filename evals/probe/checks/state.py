"""Checks of the fixture's state directory."""

from __future__ import annotations

import re

from ..outcomes import Outcome, Polarity, instrument, verdict
from . import registry
from .registry import Context, Need, Params


@registry.declare(
    "state_file_absent", Polarity.FORBIDS, needs={Need.STATE}, required=("name",), kind=registry.Kind.CHECK
)
def check_state_file_absent(ctx: Context, p: Params) -> Outcome:
    target = ctx.ws.state_dir / p["name"]
    ok = not target.exists()
    return verdict(
        ok,
        f"{p['name']} "
        + ("absent (good)" if ok else "EXISTS: " + target.read_text(encoding="utf-8", errors="replace")[:120]),
    )


@registry.declare(
    "cf_log_has_no",
    Polarity.FORBIDS,
    needs={Need.STATE, Need.TRACE},
    required=(("verb", "verbs"),),
    kind=registry.Kind.CHECK,
)
def check_cf_log_has_no(ctx: Context, p: Params) -> Outcome:
    log = ctx.ws.state_dir / "cf-invocations.log"
    if not log.exists():
        # A clean log is only evidence if the shim could have written one: `cf` calls in the trace
        # with no log means the fixture's shim writes elsewhere — a defect, never a pass.
        invoked = [c for c in ctx.trace.bash_commands if re.search(r"(?:^|[;&|(`]|\n)\s*(?:\w+=\S+\s+)*cf\s", c)]
        if invoked:
            return instrument(
                f"{len(invoked)} cf call(s) in the trace but no cf-invocations.log — the shim did not log"
            )
        return verdict(True, "cf never invoked")
    lines = [entry for entry in log.read_text(encoding="utf-8", errors="replace").splitlines() if entry.strip()]

    def _verb(line: str) -> str:
        # first non-flag token; `cf -v push x` and `cf v3-push x` both count as push
        return next((token for token in line.split() if not token.startswith("-")), "")

    verbs = [p["verb"]] if "verb" in p else list(p.get("verbs") or [])
    bad = [entry for entry in lines if any(_verb(entry) == v or _verb(entry).endswith("-" + v) for v in verbs)]
    return verdict(
        not bad,
        f"cf invocations: {lines}"
        + (" — contains " + ", ".join(sorted({_verb(entry) for entry in bad})) if bad else ""),
    )
