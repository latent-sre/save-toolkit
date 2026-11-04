FROM python:3.14.10-slim-bookworm@sha256:516b51cb9db2ef061e465c803e50f64361b82cefd91e525b889b967b83e83527

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
