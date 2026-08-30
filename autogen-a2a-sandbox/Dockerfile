FROM python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/interop-sandbox

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --root-user-action=ignore --requirement requirements.txt

COPY interop_sandbox ./interop_sandbox
COPY cases ./cases
COPY tests ./tests

USER 65532:65532

CMD ["python", "-m", "interop_sandbox.dependency_probe"]
