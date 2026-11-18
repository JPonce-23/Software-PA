# Bibliotecas locales del frontend

Se distribuyen los archivos del navegador y sus licencias, sin instalación en tiempo de ejecución.

| Biblioteca | Versión | Origen del paquete |
| --- | --- | --- |
| ExcelJS | 4.4.0 (SSALFER rebuild) | https://registry.npmjs.org/exceljs/4.4.0; recipe: tools/exceljs |
| html2canvas | 1.4.1 | https://registry.npmjs.org/html2canvas/1.4.1 |
| Leaflet | 1.9.4 | https://registry.npmjs.org/leaflet/1.9.4 |
| Bootstrap Icons | 1.13.1 | https://registry.npmjs.org/bootstrap-icons/1.13.1 |

ExcelJS se reconstruye desde un lock npm con integridad SHA-512, scripts de instalación deshabilitados y grafo de módulos verificable. El artefacto `exceljs-4.4.0-ssalfer.min.js` elimina crypto-browserify/Elliptic y conserva Workbook, imágenes, estilos y protección de hojas mediante create-hash/randombytes. Ver `frontend-ssalfer/tools/exceljs/README.md`; avisos transitivos completos en ExcelJS-build-LICENSES.txt. No es el archivo minificado oficial sin modificaciones.

ExcelJS crea el libro; html2canvas captura los gráficos visibles, incluidos los círculos dibujados en canvas. La licencia MIT de cada biblioteca se conserva junto a sus archivos. Leaflet e iconos locales evitan que su descarga externa retrase la apertura de pantallas; las teselas cartográficas mantienen su proveedor y atribución originales.

Documentación del autor de ExcelJS: https://github.com/exceljs/exceljs. Para actualizar una versión, revisar el contrato, verificar el paquete, conservar su licencia y repetir las pruebas de exportación o navegación correspondientes.

Reconstrucción vigente (11/11/2026): artefacto nuevo SHA-256 cd738e64c8d89615473b662ba0bc8fdd8b07d6baa29837b3225986529bba7a57, 337 módulos/78 paquetes runtime; no coincide con el bundle final histórico 0134b3a9…. Sus licencias efectivas están en ExcelJS-build-LICENSES.txt; identidad, reproducibilidad y pruebas propias en tools/exceljs/README.md y expediente de Etapa 3A.
