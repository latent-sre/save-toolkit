# Versioning: when oasdiff reports a breaking change

Read this only after `oasdiff breaking` reports an error for the change, or the caller asks for a
breaking change. Additive changes — a new operation, an optional field or parameter, a new enum
value the clients tolerate — need none of it.

1. **Stop and ask the caller.** Show the oasdiff output and who consumes the operation: the
   team's own UI shipped with it, scripts and automation, or other teams.
2. **Prefer expand and contract inside `/v1`.** Add the new field or operation beside the old one,
   move every consumer to it, then remove the old one in a later release. During a rolling deploy
   and while browser tabs keep an older UI open, old and new clients call the same instances, so
   both shapes stay served until the old one has no callers.
3. **Only when consumers outside the release cannot move in time, add `/v2`** beside `/v1`, with
   at most two versions live. Mark every `/v1` response with `Deprecation: @<unix-seconds>`
   (RFC 9745), `Sunset: <HTTP-date>` (RFC 8594) no earlier than the deprecation, and
   `Link: <successor-doc>; rel="deprecation"`. After the sunset date, `/v1` answers `410` problems.
4. **Record an accepted break** in an oasdiff ignore file passed with `--err-ignore`, each line
   the method, path and change text oasdiff printed, and name the reason and the caller who
   accepted it in the pull request. Never loosen `--fail-on` instead.
