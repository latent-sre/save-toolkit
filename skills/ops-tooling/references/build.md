# Build

Read this when assigning or managing implementation. The entrypoint owns the authority, evidence,
and phase-exit rules; [multi-component builds](./multi-component.md) adds the contract and ownership
rules when more than one component can build independently.

## Assign the builder

Spawn the typed `sde` agent with the requirements, design, exact repository paths and conventions,
and mission transaction. Shape every prompt with
[the spawn-prompt template](../assets/spawn-prompt.template.md). Fill every slot or state
`n/a — <reason>`:

- the checkpoint boundary;
- the acceptance criteria the builder self-verifies;
- exact file or component ownership;
- the design/contract artifact and version;
- the decision leash: reversible choices belong to the builder and are logged;
- the return contract, including changed files, checks and outputs, contract changes, risks, and
  unresolved gaps.

The builder returns only at the checkpoint or a material fork. A truly trivial scope should already
have exited this pipeline, but direct implementation still carries the same SRE lens: observability,
timeouts, idempotency, and a real dry-run for destructive behavior.

## Order and batch the work

For multi-component work, verify the thinnest end-to-end walking skeleton against the real contract
first. Then triage by blast radius: anything that can corrupt production state keeps per-slice
verification and review as a gate; lower-blast-radius independent slices build in batches and verify
once at the batch boundary.

Launch every independent builder in a batch together with disjoint file ownership. Each cites the
contract artifact rather than another builder's partial code. Tell `sde` which layer it owns; that
agent resolves its own implementation skills. Safety-critical code and all reviews stay at full
effort. Prefer updating a running builder's scope over stopping it. If a builder stops early,
inventory the partial writes and have its successor verify and finish them instead of starting over.

For three or more parallel batches, offer workflow orchestration as an explicit user opt-in. Do not
activate it automatically.

## Validate the checkpoint

Judge a builder packet by its fresh command and output evidence. Re-run the declared safety proofs
and one spot-check per batch, not the entire verification suite. Answer status questions from the
progress file named in project context; do not interrupt a running builder for status.

A packet short of its checkpoint receives one relaunch with the missing evidence or output named. A
second miss escalates to the user. Fix/re-review cycles stop after two rounds. At a third request,
stop changing code, restate the leading cause and strongest alternative, and run the cheapest
falsifier. Files a reviewer skipped while they were mid-edit remain queued for the next review.

For a safety-core defect, give the builder the finding and acceptance test, not a dictated
implementation. Prescribing an untested fix makes the builder's verification dependent on the same
reasoning that proposed it. Dictate only mechanical corrections.
