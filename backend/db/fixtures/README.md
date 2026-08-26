# Fixtures de base de datos

`001_catalogo_territorial_inegi.sql` es el catálogo territorial reproducible
de SOFTWARE-PA. Usa claves naturales INEGI, no conserva IDs internos y aplica
UPSERT idempotente. Su metadata y checksum están en el archivo JSON homónimo.

El fixture debe cargarse después del bootstrap `001` y antes del dominio demo.
La carga aborta si el catálogo activo final no contiene exactamente 32
entidades federativas y 2,478 municipios/alcaldías con claves únicas.

Los Excel de `fuentes_locales/` no forman parte de este fixture ni se copian al
repositorio.
