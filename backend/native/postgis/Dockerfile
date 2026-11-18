# Optional build candidate. Requires explicit approval before building/testing.
# Backport changes only postgis-3.so, preserving PG15 and extension SQL/catalogs.
FROM postgis/postgis:15-3.6@sha256:91098df530c92202d69193ded45dd47e6d0b6a3117a6398b0abe2be365f23550 AS backport-build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl patch python3 pkg-config clang-19 llvm-19-dev \
    postgresql-server-dev-15 libjson-c-dev libprotobuf-c-dev protobuf-c-compiler \
    libxml2-dev libpcre2-dev \
    libgeos-dev=3.14.1-2.pgdg13+1 libproj-dev=9.8.1-1.pgdg13+1 \
    && rm -rf /var/lib/apt/lists/*
COPY backport.json CVE-2026-73515.patch upstream-stable36.patch verify-source.py /opt/backport/
RUN curl --fail --location --proto '=https' --tlsv1.2 \
      https://download.osgeo.org/postgis/source/postgis-3.6.4.tar.gz -o /tmp/postgis.tar.gz \
    && echo 'ed8dc6679f1e06f7b113592b04cde2a7e00f1b1e681294c8ca2204058990cec6  /tmp/postgis.tar.gz' | sha256sum -c - \
    && mkdir /tmp/postgis && tar -xzf /tmp/postgis.tar.gz -C /tmp/postgis --strip-components=1 \
    && python3 /opt/backport/verify-source.py /tmp/postgis
WORKDIR /tmp/postgis
# Raster/topology/geocoder binaries remain inherited. Their SQL is unchanged.
RUN ./configure --with-pgconfig=/usr/lib/postgresql/15/bin/pg_config \
      --without-raster --without-topology --without-sfcgal \
    && make -j2 \
    && make -C postgis install DESTDIR=/opt/patched-install \
    && test -s /opt/patched-install/usr/lib/postgresql/15/lib/bitcode/postgis-3.index.bc \
    && test -s postgis/postgis-3.so \
    && ldd postgis/postgis-3.so > /tmp/build-linkage.txt \
    && ! grep -F 'not found' /tmp/build-linkage.txt

FROM postgis/postgis:15-3.6@sha256:91098df530c92202d69193ded45dd47e6d0b6a3117a6398b0abe2be365f23550
# Remove inherited JIT bitcode in this NEW image before installing the rebuilt
# module and its matching index. Existing images/containers remain untouched.
RUN rm -rf /usr/lib/postgresql/15/lib/bitcode/postgis-3 /usr/lib/postgresql/15/lib/bitcode/postgis-3.index.bc
COPY --from=backport-build /opt/patched-install/usr/lib/postgresql/15/lib/postgis-3.so /usr/lib/postgresql/15/lib/postgis-3.so
COPY --from=backport-build /opt/patched-install/usr/lib/postgresql/15/lib/bitcode/postgis-3 /usr/lib/postgresql/15/lib/bitcode/postgis-3
COPY --from=backport-build /opt/patched-install/usr/lib/postgresql/15/lib/bitcode/postgis-3.index.bc /usr/lib/postgresql/15/lib/bitcode/postgis-3.index.bc
COPY --from=backport-build /opt/backport /usr/share/software-pa/postgis-backport
COPY --from=backport-build /tmp/postgis/config.log /usr/share/software-pa/postgis-backport/config.log
RUN sha256sum /usr/lib/postgresql/15/lib/postgis-3.so > /usr/share/software-pa/postgis-backport/binary.sha256 \
    && ldd /usr/lib/postgresql/15/lib/postgis-3.so > /usr/share/software-pa/postgis-backport/runtime-linkage.txt \
    && ! grep -F 'not found' /usr/share/software-pa/postgis-backport/runtime-linkage.txt
LABEL org.software-pa.postgis.backport="CVE-2026-73515" \
      org.software-pa.postgis.upstream-commit="767fa40644253281f6d4e8b06811489b0a0f9b0d"
