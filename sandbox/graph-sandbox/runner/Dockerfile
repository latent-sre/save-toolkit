FROM python:3.15.0-slim-bookworm@sha256:0e019bbdfb5d9874cb2389f1c2884b64aa2ac97c99960b5bc521cef978c0617d

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GRAPH_SANDBOX_CONTAINER=1

RUN groupadd --gid 65532 sandbox \
    && useradd --uid 65532 --gid 65532 --no-create-home --shell /usr/sbin/nologin sandbox \
    && install -d --owner 65532 --group 65532 --mode 0750 /state /evidence

WORKDIR /app
COPY runner/requirements.txt /app/runner/requirements.txt
RUN python -m pip install --no-cache-dir --no-compile -r /app/runner/requirements.txt

COPY runner /app/runner
COPY cases /app/cases
COPY tests/contract/test_runner_contract.py /app/tests/contract/test_runner_contract.py
COPY tests/recovery /app/tests/recovery
COPY tests/integration/test_runner_integration.py /app/tests/integration/test_runner_integration.py

USER 65532:65532

CMD ["python", "-m", "runner.main"]
