# syntax=docker/dockerfile:1.7
FROM node:22.19.0-bookworm-slim@sha256:cff78eb5aa1cf27dc2b6aeea9d31366415a43e9a9ea0ddec00d780b2b66fad0f AS codex-package

RUN npm install --global --ignore-scripts @openai/codex@0.148.0

FROM python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=codex-package \
    /usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/ \
    /opt/route001/codex-runtime/
COPY evals/codex_harness.py /opt/route001/evals/codex_harness.py
COPY evals/codex_hook_recorder.py /opt/route001/evals/codex_hook_recorder.py
COPY evals/codex_model_catalog.py /opt/route001/evals/codex_model_catalog.py
COPY evals/codex_routing_grade.py /opt/route001/evals/codex_routing_grade.py
COPY evals/codex_runtime.py /opt/route001/evals/codex_runtime.py
COPY evals/codex_snapshot.py /opt/route001/evals/codex_snapshot.py
COPY evals/codex_trial.py /opt/route001/evals/codex_trial.py
COPY evals/graders.py /opt/route001/evals/graders.py
COPY evals/run_codex_routing.py /opt/route001/evals/run_codex_routing.py
COPY evals/conformance/codex-terra-routing-linux-v1.json \
    /opt/route001/evals/conformance/codex-terra-routing-linux-v1.json

RUN printf '%s  %s\n' \
        ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074 \
        /opt/route001/codex-runtime/bin/codex \
      | sha256sum --check --strict \
    && chmod 0555 \
        /opt/route001/codex-runtime/bin/codex \
        /opt/route001/codex-runtime/bin/codex-code-mode-host \
        /opt/route001/codex-runtime/codex-path/rg \
        /opt/route001/codex-runtime/codex-resources/bwrap \
    && useradd --no-create-home --no-user-group --uid 65532 --gid nogroup route001 \
    && find /opt/route001/evals -type d -exec chmod 0555 {} + \
    && find /opt/route001/evals -type f -exec chmod 0444 {} +

USER 65532:65532
WORKDIR /
ENTRYPOINT ["/usr/local/bin/python3.12", "-I", "-S", "-B", "/opt/route001/evals/run_codex_routing.py", "--manifest", "/opt/route001/evals/conformance/codex-terra-routing-linux-v1.json", "--repo-root", "/source", "--codex-bin", "/opt/route001/codex-runtime/bin/codex", "--private-root", "/run/route001"]
