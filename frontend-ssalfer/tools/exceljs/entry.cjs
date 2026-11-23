'use strict';
// Same browser Workbook and enums as ExcelJS' official browser entry. SSALFER
// already requires modern browsers (AbortController, optional chaining, Blob).
module.exports = Object.assign({Workbook: require('exceljs/lib/doc/workbook')},
    require('exceljs/lib/doc/enums'));
