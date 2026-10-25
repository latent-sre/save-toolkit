# Ownership and dependency lookup

"Who owns payments", "how do I page them", and "what depends on ledger" are reads, not closeout.
Read the repository's documented knowledge index and component-card paths; absent a convention,
use `operations/index.md` and `operations/services/<app>.md` relative to the knowledge-repository
root. Report owner, escalation, and dependencies as `[sourced]` with the path, `last_reviewed`, and
`evidence_status`.

For "what depends on X", also search every component card's dependency table for X as outbound.
Name the cards searched and any disagreement with X's inbound rows. A missing reverse row makes
the dependency `[unverified]`, not absent.

When records are missing, name the inspected roots and expected path; do not claim absence outside
that scope or infer an owner from code paths, commit authors, or alert labels. During an active
incident, the same read belongs to `incident-investigation`.
