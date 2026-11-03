"""One attempt's life as an explicit state machine, written to `attempt.json` at each transition, so
an attempt that raised shows where it stopped (RUNNER-001).

`prepared -> served -> seeded -> invoked -> observed -> probed -> graded -> published` is the path of
an attempt that becomes its slot's run; `void` (rule 1), `stopped` (rule 5) and `incomplete` are
where one leaves it. `attempt.json` keeps the fields its readers have always had (`attempt`, `state`,
`reason`, `recorded_at`) and adds the phase and the log of transitions.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import layout, records, rules
from .records import AttemptState


class Phase(enum.StrEnum):
    PREPARED = "prepared"
    SERVED = "served"  # the measured inputs are staged as the image the trial is served
    SEEDED = "seeded"  # the fixture repository and state exist
    INVOKED = "invoked"  # the CLI ran, once per turn
    OBSERVED = "observed"  # the trace, git facts and services were read
    PROBED = "probed"  # the probes ran in the workspace; stage 4 separates them from grading
    GRADED = "graded"
    PUBLISHED = "published"
    VOID = "void"  # rule 1: the attempt was not the candidate declared
    STOPPED = "stopped"  # rule 5: the grading machinery failed, so the scenario's trials stop
    INCOMPLETE = "incomplete"  # the attempt raised before it was graded


# Where each phase may go. The failure phases are reachable from any phase an attempt can be in.
_NEXT: dict[Phase, frozenset[Phase]] = {
    Phase.PREPARED: frozenset({Phase.SERVED}),
    Phase.SERVED: frozenset({Phase.SEEDED}),
    Phase.SEEDED: frozenset({Phase.INVOKED, Phase.OBSERVED}),  # a service that never starts skips the CLI
    Phase.INVOKED: frozenset({Phase.OBSERVED}),
    Phase.OBSERVED: frozenset({Phase.PROBED, Phase.GRADED}),
    Phase.PROBED: frozenset({Phase.GRADED}),
    Phase.GRADED: frozenset({Phase.PUBLISHED, Phase.VOID, Phase.STOPPED}),
    Phase.PUBLISHED: frozenset(),
    Phase.VOID: frozenset({Phase.PUBLISHED}),  # a voided attempt is still published and kept (rule 7)
    Phase.STOPPED: frozenset({Phase.PUBLISHED}),
    Phase.INCOMPLETE: frozenset(),
}
_FAILURES = frozenset({Phase.VOID, Phase.STOPPED, Phase.INCOMPLETE})


class IllegalTransition(ValueError):
    pass


@dataclass
class Attempt:
    """One attempt's state: its number, where it is, and every transition so far."""

    run_dir: Path
    number: int
    phase: Phase = Phase.PREPARED
    phases: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def begin(cls, run_dir: Path, number: int) -> Attempt:
        attempt = cls(run_dir, number)
        attempt.phases.append({"phase": Phase.PREPARED, "at": records.utc_now()})
        attempt.write(AttemptState.FINAL)
        return attempt

    @classmethod
    def read(cls, run_dir: Path) -> Attempt | None:
        """The attempt `run_dir` recorded, or None when it recorded no phases (an older runner's)."""
        saved = layout.read_object(run_dir / "attempt.json") or {}
        phases = saved.get("phases")
        if not isinstance(phases, list) or type(saved.get("attempt")) is not int:
            return None
        try:
            phase = Phase(str(saved.get("phase")))
        except ValueError:
            return None
        return cls(run_dir, saved["attempt"], phase, list(phases))

    def advance(self, phase: Phase, note: str | None = None) -> None:
        """Move to `phase` and record it. A failure phase is reachable from anywhere; any other move
        must be one the machine allows, so a step the runner skipped is a defect, not a record."""
        if phase not in _FAILURES and phase not in _NEXT[self.phase]:
            raise IllegalTransition(f"attempt {self.number}: {self.phase} cannot move to {phase}")
        if self.phase in (Phase.PUBLISHED, Phase.INCOMPLETE):
            raise IllegalTransition(f"attempt {self.number}: {self.phase} is terminal")
        self.phase = phase
        self.phases.append({"phase": phase, "at": records.utc_now(), **({"note": note} if note else {})})
        state = rules.rule_7_attempt_kept("raised") if phase is Phase.INCOMPLETE else AttemptState.FINAL
        self.write(state, note if phase is Phase.INCOMPLETE else None)

    def write(self, state: AttemptState, reason: str | None = None) -> None:
        record_state(self.run_dir, self.number, state, reason, phase=self.phase, phases=self.phases)


def record_state(
    run_dir: Path,
    number: int,
    state: AttemptState,
    reason: str | None = None,
    *,
    phase: Phase | None = None,
    phases: list[dict[str, Any]] | None = None,
) -> None:
    """Write `attempt.json` for `run_dir`, keeping the phase log an earlier write recorded there, and
    carry the state into the attempt's v1 record (rule 7)."""
    if phase is None or phases is None:
        saved = layout.read_object(run_dir / "attempt.json") or {}
        phase = phase if phase is not None else _saved_phase(saved)
        phases = phases if phases is not None else list(saved.get("phases") or [])
    layout.write_json(
        run_dir / "attempt.json",
        {
            "attempt": number,
            "state": state,
            **({"reason": reason} if reason else {}),
            **({"phase": phase, "phases": phases} if phase is not None else {}),
            "recorded_at": records.utc_now(),
        },
        ascii_only=True,
    )
    records.update_record(
        run_dir,
        lambda record: record["attempt"].update(number=number, state=state, **({"reason": reason} if reason else {})),
    )


def _saved_phase(saved: dict[str, Any]) -> Phase | None:
    try:
        return Phase(saved["phase"]) if "phase" in saved else None
    except ValueError:
        return None
