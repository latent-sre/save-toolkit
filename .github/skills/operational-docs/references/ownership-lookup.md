# Ownership and dependency lookup

Use this bounded read for an owner, paging route, or dependency recorded in a card, even while an
incident is open. The main session can do the read with this method, and an assigned local read
uses the same method in `repository-investigator`. Requests for incident decisions use
`incident-investigation`. Reporting a pager route grants no authority to page.

Read the supplied card path first. When only a component is named, use the repository's documented
knowledge index and component-card paths. Absent a convention, use `operations/index.md` and
`operations/services/<app>.md` relative to the knowledge-repository root. Report the requested fields
as `[sourced]` with the path, `last_reviewed`, and `evidence_status`.

For "what depends on X", also search every component card's dependency table for X as outbound.
Name the cards searched and any disagreement with X's inbound rows. A missing reverse row makes
the dependency `[unverified]`, not absent.

When records are missing, name the inspected roots and expected path; do not claim absence outside
that scope or infer an owner from code paths, commit authors, or alert labels.
