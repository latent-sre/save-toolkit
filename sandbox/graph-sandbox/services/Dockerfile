FROM python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GRAPH_SANDBOX_CONTAINER=1

RUN groupadd --gid 10001 sandbox \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin sandbox \
    && install -d --owner=10001 --group=10001 --mode=0700 /data

WORKDIR /app
COPY services/requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY services/sandbox_services /app/sandbox_services
COPY tests/contract/test_services_contract.py /app/tests/contract/test_services_contract.py
COPY tests/integration/test_services_integration.py /app/tests/integration/test_services_integration.py

USER 10001:10001
EXPOSE 8080 8081 8082

CMD ["python", "-m", "sandbox_services.checkout"]
