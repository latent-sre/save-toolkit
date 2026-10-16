# Breaking HTTP changes

Use when a consumer contract changes incompatibly. Keep the service's existing versioning policy;
choose a migration from actual consumers and their release cadence.

1. Identify the changed contract, affected consumers and compatibility evidence. Reuse approval
   already covering the break; otherwise return the concrete decision to the caller.
2. Prefer compatible expansion, consumer migration and evidence-backed retirement. Rolling
   deployments, open browser tabs and external clients may need overlapping contracts.
3. Introduce another API version when consumers cannot migrate together. Agree the overlap,
   deprecation signals, retirement evidence and recovery path; no fixed path prefix or version count
   applies to every service.
4. Record intentional compatibility-check exceptions with their reason and owner; preserve the
   gate for other breaks. When using `oasdiff`, scope its ignore entries to the accepted change.

For HTTP deprecation, `Deprecation`, `Sunset` and successor-document links are available conventions;
use the service's documented retirement behavior. An added route alone does not justify migrating
unrelated contracts.
