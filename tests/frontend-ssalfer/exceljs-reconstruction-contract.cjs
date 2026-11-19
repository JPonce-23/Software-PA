'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const root = path.resolve(__dirname, '../..');
test('XLSX roundtrip preserves explicit types, rows/columns, styles, images, freeze, printing and protection', async () => {
    const context = vm.createContext({console, setTimeout, clearTimeout, setImmediate, clearImmediate,
        TextEncoder, TextDecoder, crypto: webcrypto});
    context.self = context; context.window = context;
    vm.runInContext(fs.readFileSync(path.join(root,
        'frontend-ssalfer/js/vendor/exceljs-4.4.0-ssalfer.min.js'), 'utf8'), context);
    async function contract() {
        const w = new ExcelJS.Workbook();
        const s = w.addWorksheet('Contrato ñ');
        s.columns = [
            {header:'Texto',key:'text',width:32}, {header:'Número',key:'number',width:18},
            {header:'Booleano',key:'boolean'}, {header:'Fecha',key:'date'},
            {header:'Fórmula',key:'formula'}, {header:'Vacío',key:'empty',hidden:true}
        ];
        s.addRow({text:"'=SUM(A1:A2)",number:1234.125,boolean:true,
            date:new Date('2026-11-11T12:34:56Z'),formula:{formula:'B2*2',result:2468.25},empty:null});
        s.getRow(2).height = 28;
        s.getCell('B2').numFmt = '#,##0.000';
        s.getCell('A2').font = {name:'Arial',bold:true,size:14};
        s.getCell('A2').alignment = {horizontal:'center',wrapText:true};
        s.getCell('A2').border = {bottom:{style:'thin',color:{argb:'FF285438'}}};
        s.mergeCells('A4:B4'); s.getCell('A4').value = 'Unido';
        s.views = [{state:'frozen',xSplit:1,ySplit:1}];
        s.pageSetup = {orientation:'landscape',paperSize:9,fitToPage:true,
            fitToWidth:1,fitToHeight:0,printArea:'A1:F12',printTitlesRow:'1:1'};
        const id = w.addImage({base64:'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6P5QAAAAASUVORK5CYII=',extension:'png'});
        s.addImage(id,{tl:{col:0,row:5},ext:{width:80,height:20}});
        await s.protect('synthetic-only',{spinCount:3,formatCells:false});
        const bytes = await w.xlsx.writeBuffer();
        const read = new ExcelJS.Workbook(); await read.xlsx.load(bytes);
        const a = read.getWorksheet('Contrato ñ'), image = read.getImage(a.getImages()[0].imageId);
        return {signature:Array.from(bytes.slice(0,4)),
            values:['A2','B2','C2','D2','E2','F2'].map(k => a.getCell(k).value),
            types:['A2','B2','C2','D2','E2','F2'].map(k => a.getCell(k).type),
            expectedTypes:[ExcelJS.ValueType.String,ExcelJS.ValueType.Number,ExcelJS.ValueType.Boolean,
                ExcelJS.ValueType.Date,ExcelJS.ValueType.Formula,ExcelJS.ValueType.Null],
            height:a.getRow(2).height,width:a.getColumn(1).width,hidden:a.getColumn(6).hidden,
            format:a.getCell('B2').numFmt,font:a.getCell('A2').font,
            alignment:a.getCell('A2').alignment,border:a.getCell('A2').border,
            merged:a.getCell('B4').value,views:a.views,page:a.pageSetup,
            imageCount:a.getImages().length,imageExtension:image.extension,imageBytes:image.buffer.length,
            protection:a.sheetProtection};
    }
    const result = JSON.parse(JSON.stringify(await vm.runInContext('('+contract.toString()+')()', context)));
    assert.deepEqual(result.signature,[0x50,0x4b,0x03,0x04]);
    assert.deepEqual(result.types,result.expectedTypes);
    assert.deepEqual(result.values,["'=SUM(A1:A2)",1234.125,true,
        '2026-11-11T12:34:56.000Z',{formula:'B2*2',result:2468.25},null]);
    assert.equal(result.height,28); assert.equal(result.width,32); assert.equal(result.hidden,true);
    assert.equal(result.format,'#,##0.000');
    assert.equal(result.font.name,'Arial'); assert.equal(result.font.bold,true); assert.equal(result.font.size,14);
    assert.equal(result.alignment.horizontal,'center'); assert.equal(result.alignment.wrapText,true);
    assert.equal(result.border.bottom.style,'thin'); assert.equal(result.merged,'Unido');
    assert.equal(result.views[0].state,'frozen'); assert.equal(result.views[0].xSplit,1); assert.equal(result.views[0].ySplit,1);
    assert.equal(result.page.orientation,'landscape'); assert.equal(result.page.paperSize,9);
    assert.equal(result.page.fitToWidth,1); assert.equal(result.page.fitToHeight,0);
    assert.equal(result.page.printArea,'A1:F12'); assert.equal(result.page.printTitlesRow,'1:1');
    assert.equal(result.imageCount,1); assert.equal(result.imageExtension,'png'); assert.ok(result.imageBytes>0);
    assert.equal(result.protection.algorithmName,'SHA-512'); assert.equal(result.protection.spinCount,3);
});
