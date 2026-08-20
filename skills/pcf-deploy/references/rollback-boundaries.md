# Rollback boundaries

## What a revision contains

`[sourced]` Current CAPI associates a revision with its droplet, environment variables, process start
commands, and sidecars. Tasks are excluded. The rollback path copies retained revision state into a new
revision.

It does not establish restoration of:

- routes or route mappings;
- service bindings or service-side state;
- instance count, memory, disk, or log-rate scale;
- health-check configuration;
- database/schema migrations or data written by either version;
- messages, webhooks, files, or other external effects;
- work already performed by downstream consumers.

Implementation evidence: `cloudfoundry/cloud_controller_ng@9dc07af5a33d328b77a85c9e7bd4d1b88caa83bd`,
`app/models/runtime/revision_model.rb` and `app/actions/revision_resolver.rb`.

## Retention is two independent facts

`[sourced]` Revision rows and staged droplet blobs are pruned independently. Current default packaging
can retain up to 100 associated revisions while retaining only a smaller set of recent noncurrent
staged droplets. A revision is deployable only while its referenced droplet remains available/staged.
Therefore "100 revisions" never proves 100 rollback candidates.

Pinned retention evidence: `cloudfoundry/capi-release@3a412762973d477a84057c598cfab91f612ed7c7`
(`jobs/cloud_controller_clock/spec`, `jobs/cloud_controller_ng/spec`) carries the default packaging
values; `cloudfoundry/cloud_controller_ng@9dc07af5a33d328b77a85c9e7bd4d1b88caa83bd`
(`app/jobs/runtime/prune_excess_app_revisions.rb`, `lib/cloud_controller/bits_expiration.rb`) implements
the independent revision-row and droplet-bit pruning paths.

Record the target foundation's configured retention and verify the selected revision/droplet before
approval. Do not use a remembered default as target evidence.

## Data and schema

Application rollback does not undo migrations or data writes. Use expand -> backfill -> mixed-version
verification -> contract, and delay the destructive contract until the old code cannot return. Record
restore/forward-recovery evidence, data-loss bounds, and external side-effect reconciliation separately.

## Cancellation

Canceling an in-progress deployment and rolling back a completed release have different postconditions.
Cancellation can restore the original web process/droplet path while leaving environment or binding
changes. State the exact expected state and verify it; do not use "cancel" and "rollback"
interchangeably.
