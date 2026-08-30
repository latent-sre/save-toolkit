FROM python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4

ARG SANDBOX_SOURCE_REVISION
LABEL org.opencontainers.image.revision=${SANDBOX_SOURCE_REVISION} \
      org.opencontainers.image.title="autogen-a2a-sandbox" \
      org.opencontainers.image.version="autogen-a2a-sandbox/v1"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUTOGEN_A2A_RUNTIME_MARKER=autogen-a2a-sandbox-container/v1

WORKDIR /opt/interop-sandbox

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --root-user-action=ignore --requirement requirements.txt

COPY interop_sandbox ./interop_sandbox
COPY cases ./cases
COPY tests ./tests
COPY activate.py ./activate.py

RUN printf '%s\n' 'autogen-a2a-sandbox-container/v1' > /opt/interop-sandbox/.runtime-marker \
    && chmod 0444 /opt/interop-sandbox/.runtime-marker \
    && mkdir -p /state/checkpoints /state/decisions /evidence \
    && chown -R 65532:65532 /state /evidence

USER 65532:65532

CMD ["python", "-m", "interop_sandbox.dependency_probe"]
