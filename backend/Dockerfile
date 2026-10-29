FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 ssalfer && useradd --uid 10001 --gid ssalfer --no-create-home ssalfer

COPY --chown=root:root . .
RUN mkdir -p /app/uploads && chown ssalfer:ssalfer /app/uploads
ENV PYTHONDONTWRITEBYTECODE=1
USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--no-proxy-headers"]
