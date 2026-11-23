# ExcelJS para SSALFER

ExcelJS4.4.0 oficial tiene Elliptic6.5.4 en su bundle vía crypto-browserify; actualizar a Elliptic6.6.1 deja CVE-2025-14505 sin parche. El dashboard utiliza hojas, tipos, imágenes PNG, estilos y descarga XLSX. SheetJS CE no reproduce esa exportación con imágenes/estilos, por lo que se reconstruye ExcelJS con sus fuentes npm verificadas por el lock.

`entry.cjs` expone el mismo Workbook y enums, desde fuentes modernas. Los navegadores admitidos ya requieren AbortController, optional chaining y Blob. No se añaden polyfills globales. uuid se fija a11.1.1 por CVE-2026-41907; Acorn8 procesa su sintaxis moderna sin modificar fuentes del proveedor. `crypto.cjs` ofrece únicamente createHash, getHashes y randomBytes, las tres funciones usadas por lib/utils/encryptor.js. create-hash incluye SHA-512; randombytes usa WebCrypto getRandomValues y falla si no existe, sin aleatoriedad débil. No se sustituyen algoritmos de protección de hojas. El grafo Browserify real debe excluir elliptic, crypto-browserify, browserify-sign y create-ecdh.

Desde este directorio, con Node22.23.2/npm10.9.8:

```
npm ci --ignore-scripts --no-audit --no-fund
node build.cjs --check
```

Para cambiar intencionalmente un artefacto revisado: `node build.cjs`, verificar auditorías y actualizar manifiestos SS09. No usar npm update, install sin lock ni scripts de terceros. runtime-graph.json registra cada módulo incluido, su hash fuente, paquetes, versiones e integridad; es inventario del artefacto, no SBOM del contenedor. El lock también contiene herramientas de build y dependencias Node de ExcelJS que no se distribuyen: un aviso en ellas debe clasificarse separadamente. Conservar auditoría de build; no ocultar sus avisos.

ExcelJS mantiene MIT; se conservan todas las licencias runtime en ExcelJS-build-LICENSES.txt. saxes5.0.1 omite su licencia del tar npm: se incluye desde el commit/tag oficial fijado en license-sources.json. La reconstrucción no debe depender de ninguna ruta absoluta local y no se copian las herramientas/node_modules a la imagen frontend.

La dependencia general crypto-browserify de Browserify se reemplaza explícitamente en package.json/lock por el paquete local privado `@ssalfer/crypto-build-disabled` (1.0.0). Browserify solo necesita resolver su ruta al construir el mapa por defecto; este módulo lanza un error si alguien intenta ejecutarlo. El mapa efectivo continúa usando `crypto.cjs`. No es un parche ni una nueva versión upstream de crypto-browserify: elimina por completo del árbol instalado crypto-browserify3.12.1, browserify-sign4.2.6, create-ecdh4.0.4 y elliptic6.6.1, sin proveer sus APIs. El override `$crypto-browserify` conserva la resolución relativa al proyecto y `npm ci` funciona desde una ruta nueva. No editar node_modules ni aplicar parches postinstall. Los dos archivos locales se verifican por SHA-256 en runtime-graph.json; el verificador rechaza la reintroducción de esas implementaciones a cualquier profundidad. En la campaña histórica se reportó identidad byte por byte para 79 paquetes; la reconstrucción vigente se identifica a continuación.

La integridad offline no demuestra que no haya nuevas vulnerabilidades. En CI/revisión: reconstrucción exacta, verificador, pruebas XLSX/dashboard y SCA online del lock con fecha/fuentes de avisos. El gate clasifica los dos alcances y ahora falla ante cualquier hallazgo, incluido tooling, además de errores/datos SCA inválidos. No existe aceptación implícita de alertas bajas.

## Reconstrucción vigente — Etapa 3A, 11 de noviembre de 2026

Se generó un lock nuevo porque no se recuperó el lock final original. Node 22.23.2 y npm 10.9.8; instalación con scripts de ciclo de vida deshabilitados. No se utilizaron audit fix, update ni instalaciones globales.

El bundle vigente es un **ARTEFACTO NUEVO** respecto al final histórico: SHA-256 cd738e64c8d89615473b662ba0bc8fdd8b07d6baa29837b3225986529bba7a57, con 337 módulos y 78 paquetes runtime. No coincide con el final histórico 0134b3a97126bfc32201e67fe378e578e7117223bd2aadde225ac768e8cc6402. No se cambiaron fuentes para forzar aquella identidad.

El lock vigente tiene SHA-256 6af3a0a619037bb404b7d9b5c251730474d5400a114e696b163e03b40a3e3620. Se verificaron las integridades SHA-512 de los 271 tarballs de registro y sus versiones instaladas. La auditoría npm del lock del 11/11/2026 devuelve cero hallazgos; es un snapshot, no una garantía permanente ni una auditoría nativa.

La instalación limpia repetida y build.cjs --check conservaron los cuatro outputs idénticos. Los verificadores y pruebas XLSX reales se ejecutaron sobre este artefacto, incluyendo protección SHA-512, imágenes, fórmulas, estilos, impresión, filas/columnas y ausencia de WebCrypto. El stub privado sigue fallando cerrado.

Para comprobar el snapshot de auditoría, usar verify.py --audit-file con el JSON completo de npm audit del mismo lock; el gate falla también ante avisos de tooling o errores de auditoría. La evidencia de esta campaña reside en el expediente de Etapa 3A. Los inventarios SS-09 finales se actualizarán junto con los componentes nativos; no se certifican todavía.
