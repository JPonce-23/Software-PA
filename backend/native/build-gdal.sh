#!/bin/sh
# Runs only in the dedicated Docker build stage, after explicit build approval.
set -eu
archive=/tmp/gdal-3.13.3.tar.gz
curl --fail --location --proto '=https' --tlsv1.2 --retry 3 \
  https://github.com/OSGeo/gdal/releases/download/v3.13.3/gdal-3.13.3.tar.gz -o "$archive"
echo '5e0c388d83da2d686cc00a40272882432cdb54edff43d4af173e532844a0a0ea  /tmp/gdal-3.13.3.tar.gz' | sha256sum -c -
mkdir /tmp/gdal-source
tar -xzf "$archive" -C /tmp/gdal-source --strip-components=1
cmake -S /tmp/gdal-source -B /tmp/gdal-build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/gdal \
  -DBUILD_TESTING=OFF -DBUILD_APPS=ON \
  -DBUILD_PYTHON_BINDINGS=OFF -DBUILD_JAVA_BINDINGS=OFF -DBUILD_CSHARP_BINDINGS=OFF \
  -DGDAL_USE_EXTERNAL_LIBS=OFF -DGDAL_USE_GEOS=ON -DGDAL_USE_SQLITE3=ON \
  -DGDAL_USE_SPATIALITE=ON -DGDAL_USE_EXPAT=ON -DGDAL_USE_LIBKML=ON -DGDAL_USE_ZLIB=ON \
  -DGDAL_USE_TIFF_INTERNAL=OFF -DGDAL_USE_GEOTIFF_INTERNAL=OFF \
  -DGDAL_USE_JPEG_INTERNAL=OFF -DGDAL_USE_PNG_INTERNAL=OFF \
  -DGDAL_USE_CURL=OFF -DGDAL_USE_NETCDF=OFF -DGDAL_USE_HDF4=OFF -DGDAL_USE_HDF5=OFF \
  -DGDAL_BUILD_OPTIONAL_DRIVERS=OFF -DOGR_BUILD_OPTIONAL_DRIVERS=OFF \
  -DGDAL_ENABLE_DRIVER_GTIFF=OFF -DGDAL_ENABLE_DRIVER_VRT=OFF \
  -DOGR_ENABLE_DRIVER_GEOJSON=ON -DOGR_ENABLE_DRIVER_SHAPE=ON \
  -DOGR_ENABLE_DRIVER_KML=ON -DOGR_ENABLE_DRIVER_LIBKML=ON \
  -DOGR_ENABLE_DRIVER_SQLITE=ON -DOGR_ENABLE_DRIVER_GPKG=ON
cmake --build /tmp/gdal-build --parallel 2
cmake --install /tmp/gdal-build
mkdir -p /opt/gdal/share/build-evidence
cp /tmp/gdal-build/CMakeCache.txt /opt/gdal/share/build-evidence/
cp /tmp/gdal-source/LICENSE.TXT /opt/gdal/share/build-evidence/
cp /tmp/gdal-source/NEWS.md /opt/gdal/share/build-evidence/
