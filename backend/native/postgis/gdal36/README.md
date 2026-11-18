# Revisión +pa3 preparada en fuente; QA funcional pendiente

La cadena vigente de preparación es Debian3.10.3+dfsg-1 -> parche +pa2 intacto
-> security-metadata-pa3.patch. backport.json conserva la identidad +pa2;
backport-pa3.json fija el delta, sus fases y la interfaz interna acotada.
EHgetmetavalue recibe capacidad explícita en48llamadas; no se truncan valores.

F1 no compiló paquetes/bibliotecas/imágenes ni probó el negativo sobre +pa3.
Las pruebas futuras deben reutilizar los fixtures de3B.3-R por sus hashes.
La receta reutiliza corePostGIS/LLVM histórico por digest, mantienePG15/SONAME36
GEOS/PROJ fijados y captura fuente precompile separada del estado post-quilt.
El builder necesita acceso a ese artefacto local exacto:su disponibilidad remota
no está acreditada; no sustituirlo por otro digest ni reconstruircore en silencio.

## Antecedente +pa2 preservado como historia

# Backport ABI36: candidato de fuente, sin activar

Fuentes Debian3.10.3+dfsg-1 y fixes OSGeo con hashes en backport.json.
El parche combinado cubre CVE-2026-49014,8213,8212,8088,8087,8086,8084,4738.
Se adapta únicamente el contexto del hunk bCheckDims del netCDF; se conserva
el bloque de validación de dimensiones de3.10.3. Los commits c49254 y50eea
contienen el mismo diff: no aplicarlos dos veces. Se excluyen del parche
combinado fixtures Git binarios, conservados en los parches upstream.

prepare-source.py verifica seis hashes previos y posteriores. En modo
--debian, dpkg-source aplica y registra quilt para evitar doble aplicación.
La receta ../Dockerfile.gdal36-candidate mantiene el build Debian completo,
no desactiva raster/drivers, produce .deb de biblioteca/datos/plugins locales
y conserva PG15/PostGIS3.6.4, GEOS3.14.1, PROJ9.8.1 y el backport core+LLVM.
La etiqueta +pa1 identifica procedencia local; no significa update oficial.

**Revisión actual+pa2 solo en fuente, pendiente de compilación/QA.**
La revisión+pa1 se construyó y pasó ABI, netCDF, PostGIS, raster y033, pero
issue_14356.he4 cayó: el primer hunk9491e794 había coincidido en SWinqmaps
en lugar de SWinqfields. Se conserva esa imagen y su evidencia de fallo.
+pa2 restaura SWinqmaps y aplica el guard oficial en SWinqfields, sin cambiar
GDAL3.10.3/SONAME36. prepare-source.py verifica también los7 cuerpos de
función HDF exactos para impedir otra aplicación en contexto idéntico.
La imagen+pa2 y otra QA necesitan ampliación del máximo de un contenedor
nuevo autorizado, ya utilizado. No activar Compose ni modificar manualmente
el contenedor+pa1 para aparentar una validación del artefacto final.

La receta conserva hardening Debian, limita make a2jobs y excluye símbolos
debug innecesarios (-g0/noddebs) dentro del máximo8GiB adicional. La política
slim heredada omite docs/lintian en runtime; copyright permanece y los .deb
íntegros conservan NOTICE/changelogs para revisión de licencias. Nunca se
usan --force-depends, apt repair, falsos SONAME ni quitar raster/drivers para
forzar PASS. Dictamen y evidencias externas: /tmp/software-pa-libgdal36-20261110.

Las versiones de herramientas apt siguen siendo resoluciones del repositorio
al compilar: la receta captura buildinfo/changes/inventario, pero todavía no
existe un lock completo de esos .deb ni garantía de reproducción binaria.
Una compilación aceptada debe archivar todos los paquetes/hashes y metadatos
firmados o fijar un snapshot Debian/PGDG accesible. Si cambian las versiones
GEOS/PROJ retenidas, falla en lugar de mezclar ABI silenciosamente.
