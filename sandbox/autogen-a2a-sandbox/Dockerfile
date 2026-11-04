FROM python:3.14.10-slim-bookworm@sha256:516b51cb9db2ef061e465c803e50f64361b82cefd91e525b889b967b83e83527

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
COPY Dockerfile ./Dockerfile

RUN printf '%s\n' 'autogen-a2a-sandbox-container/v1' > /opt/interop-sandbox/.runtime-marker \
    && chmod 0444 /opt/interop-sandbox/.runtime-marker \
    && mkdir -p /state/checkpoints /state/decisions /evidence \
    && chown -R 65532:65532 /state /evidence

USER 65532:65532

CMD ["python", "-m", "interop_sandbox.dependency_probe"]
