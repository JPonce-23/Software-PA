# Build fixed upstream GDAL on the same pinned Debian/Python base. Never mix
# sid libraries into trixie. This candidate requires native QA before integration.
FROM python:3.11-slim-trixie@sha256:65bd3d9f1d7fa268dd1909973ba7eb4bdf41f6dcf2cfbe76ba9528b170f3fd79 AS gdal-build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake curl ca-certificates libproj-dev libgeos-dev \
    libsqlite3-dev libspatialite-dev libexpat1-dev libkml-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
COPY native/build-gdal.sh /usr/local/src/build-gdal.sh
RUN sh /usr/local/src/build-gdal.sh

FROM python:3.11-slim-trixie@sha256:65bd3d9f1d7fa268dd1909973ba7eb4bdf41f6dcf2cfbe76ba9528b170f3fd79
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libproj25 proj-data libgeos-c1t64 libsqlite3-0 libspatialite8t64 \
    libexpat1 libkmlbase1t64 libkmldom1t64 libkmlengine1t64 zlib1g \
    && rm -rf /var/lib/apt/lists/*
COPY --from=gdal-build /opt/gdal /opt/gdal
RUN echo /opt/gdal/lib > /etc/ld.so.conf.d/software-pa-gdal.conf && ldconfig \
    && ln -s /opt/gdal/bin/ogrinfo /usr/local/bin/ogrinfo \
    && ln -s /opt/gdal/bin/ogr2ogr /usr/local/bin/ogr2ogr \
    && ln -s /opt/gdal/bin/gdalinfo /usr/local/bin/gdalinfo
ENV GDAL_DATA=/opt/gdal/share/gdal
LABEL org.software-pa.gdal.version="3.13.3" \
      org.software-pa.gdal.source-sha256="5e0c388d83da2d686cc00a40272882432cdb54edff43d4af173e532844a0a0ea"
COPY native/check-gdal.py /usr/local/lib/software-pa/check-gdal.py
RUN python /usr/local/lib/software-pa/check-gdal.py
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
