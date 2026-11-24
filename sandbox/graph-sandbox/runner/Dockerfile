FROM python:3.15.2-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9

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
