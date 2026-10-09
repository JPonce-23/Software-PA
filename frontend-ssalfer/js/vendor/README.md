# Bibliotecas locales del frontend

Se distribuyen los archivos del navegador y sus licencias, sin instalación en tiempo de ejecución.

| Biblioteca | Versión | Origen del paquete |
| --- | --- | --- |
| ExcelJS | 4.4.0 | https://registry.npmjs.org/exceljs/4.4.0 |
| html2canvas | 1.4.1 | https://registry.npmjs.org/html2canvas/1.4.1 |
| Leaflet | 1.9.4 | https://registry.npmjs.org/leaflet/1.9.4 |
| Bootstrap Icons | 1.13.1 | https://registry.npmjs.org/bootstrap-icons/1.13.1 |

Los paquetes descargados se verificaron contra `dist.shasum` publicado en el registro. SHA-256 del archivo `exceljs-4.4.0.min.js`: `7e49da68588e250dbb8bba190d2caa8ab3787cc0284bda1d8b2f805c4df742c9`.

ExcelJS crea el libro; html2canvas captura los gráficos visibles, incluidos los círculos dibujados en canvas. La licencia MIT de cada biblioteca se conserva junto a sus archivos. Leaflet e iconos locales evitan que su descarga externa retrase la apertura de pantallas; las teselas cartográficas mantienen su proveedor y atribución originales.

Documentación del autor de ExcelJS: https://github.com/exceljs/exceljs. Para actualizar una versión, revisar el contrato, verificar el paquete, conservar su licencia y repetir las pruebas de exportación o navegación correspondientes.
