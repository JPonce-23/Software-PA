FROM python:3.11-slim-trixie@sha256:65bd3d9f1d7fa268dd1909973ba7eb4bdf41f6dcf2cfbe76ba9528b170f3fd79

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 ssalfer && useradd --uid 10001 --gid ssalfer --no-create-home ssalfer

COPY --chown=root:root . .
# Source checkouts can be private (0600/0700). Only packaged code is made
# readable; .dockerignore excludes uploads, secrets and QA data.
RUN chmod -R a+rX /app && install -d -o 10001 -g 10001 -m 0700 /app/uploads
ENV PYTHONDONTWRITEBYTECODE=1
USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--log-config", "/app/logging.json", "--no-access-log", "--workers", "2"]
