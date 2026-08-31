# Docker-backed local verification

> **Status: live.** This is a conditional verification contract, not production authority.

Docker-backed local verification is allowed and recommended when the acting lane already has Bash
or execute authority and an official image exercises the real tool or runtime more faithfully than
a substitute or missing host binary. It does not grant production-change authority or widen tools.

- Pin an exact image version and record its resolved reference plus the tool version.
- Use `--rm` and `--network none` by default.
- Pass the minimum artifact set through a read-only bind mount or stdin; never mount the Docker
  socket or forward credentials.
- Record the command, exit status, and material diagnostics.

Match the conclusion to the exercised boundary: static validation does not prove runtime
connectivity, authentication, telemetry delivery, persistence, recovery, or production readiness.
