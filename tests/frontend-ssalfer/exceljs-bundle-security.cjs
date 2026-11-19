'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const {webcrypto,createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../..');
const artifact=fs.readFileSync(path.join(root,'frontend-ssalfer/js/vendor/exceljs-4.4.0-ssalfer.min.js'),'utf8');
const original=()=>execFileSync('git',['show','0989bfbe422d149519a52cdf20b643c6bf8576c5:frontend-ssalfer/js/vendor/exceljs-4.4.0.min.js'],{cwd:root,encoding:'utf8',maxBuffer:5*1024*1024});
const png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6P5QAAAAASUVORK5CYII=';
test('unused general crypto dependency fails closed instead of providing signing/ECDH',()=>{
 assert.throws(()=>require(path.join(root,'frontend-ssalfer/tools/exceljs/crypto-build-disabled/index.cjs')),
  /GENERAL_CRYPTO_DISABLED_FOR_EXCELJS_BUILD/);
});
function realm(source,{secure=true}={}){
 const context=vm.createContext({console,setTimeout,clearTimeout,setImmediate,clearImmediate,crypto:secure?webcrypto:undefined,TextEncoder,TextDecoder});
 context.self=context;context.window=context;
 vm.runInContext(source,context);return context;
}
async function sample(context){
 return vm.runInContext(`(async()=>{
 const w=new ExcelJS.Workbook();w.creator='SSALFER';w.created=new Date('2026-11-10T12:00:00Z');
 const s=w.addWorksheet('Datos ñ');s.addRow(['Texto','Número','Fecha','Fórmula']);
 s.addRow(["'=SUM(A1:A2)",123.5,new Date('2026-11-10T00:00:00Z'),{formula:'B2*2',result:247}]);
 s.getCell('A1').font={bold:true,color:{argb:'FFFFFFFF'}};s.getCell('A1').fill={type:'pattern',pattern:'solid',fgColor:{argb:'FF285438'}};
 s.getCell('C2').numFmt='yyyy-mm-dd';s.views=[{state:'frozen',ySplit:1}];s.getColumn(1).width=45;
 s.pageSetup={orientation:'landscape',fitToPage:true,fitToWidth:1,fitToHeight:0};
 const image=w.addImage({base64:'${png}',extension:'png'});s.addImage(image,{tl:{col:0,row:4},ext:{width:800,height:200}});
 await s.protect('synthetic-password',{spinCount:2});
 // Conditional-formatting IDs exercise uuid.v4 from the patched dependency.
 s.addConditionalFormatting({ref:'B2',rules:[{type:'dataBar',minLength:0,maxLength:100,gradient:true,cfvo:[{type:'min'},{type:'max'}],color:{argb:'FF285438'}}]});
 return w.xlsx.writeBuffer();})()`,context);
}
function normalized(w){
 const s=w.getWorksheet('Datos ñ');return {creator:w.creator,created:w.created.toISOString(),name:s.name,
  values:s.getSheetValues().map(row=>row?.map(v=>Object.prototype.toString.call(v)==='[object Date]'?v.toISOString():v)),
  font:s.getCell('A1').font,fill:s.getCell('A1').fill,numFmt:s.getCell('C2').numFmt,
  view:s.views,column:s.getColumn(1).width,page:s.pageSetup,
  images:s.getImages().map(i=>({range:{tl:i.range.tl?.model,br:i.range.br?.model,ext:i.range.ext,editAs:i.range.editAs},image:w.getImage(i.imageId)}))};
}
test('graph is bound to artifact and lock; signing and ECDH modules absent',()=>{
 const g=JSON.parse(fs.readFileSync(path.join(root,'frontend-ssalfer/tools/exceljs/runtime-graph.json')));
 assert.equal(createHash('sha256').update(artifact).digest('hex'),g.sha256);
 for(const name of ['elliptic','crypto-browserify','browserify-sign','create-ecdh']){
  assert.ok(!g.packages.some(p=>p.name===name));assert.ok(!artifact.includes(name));
 }
 assert.ok(g.packages.some(p=>p.name==='uuid'&&p.version==='11.1.1'));
 assert.ok(!fs.existsSync(path.join(root,'frontend-ssalfer/js/vendor/exceljs-4.4.0.min.js')));
});
test('actual XLSX matches official ExcelJS: cells, dates, formula, style, images, print/freeze',async()=>{
 const baseline=realm(original()),next=realm(artifact),before=await sample(baseline),after=await sample(next);
 const Reader=baseline.ExcelJS.Workbook;
 const a=new Reader(),b=new Reader();await a.xlsx.load(before);await b.xlsx.load(after);
 // Normalize cross-realm objects and binary image data for structural comparison.
 assert.deepEqual(JSON.parse(JSON.stringify(normalized(b))),JSON.parse(JSON.stringify(normalized(a))));
 assert.equal(b.getWorksheet('Datos ñ').sheetProtection.algorithmName,'SHA-512');
 assert.equal(b.getWorksheet('Datos ñ').sheetProtection.spinCount,2);
 const protection=b.getWorksheet('Datos ñ').sheetProtection;
 let expected=createHash('sha512').update(Buffer.concat([Buffer.from(protection.saltValue,'base64'),Buffer.from('synthetic-password','utf16le')])).digest();
 for(let i=0;i<2;i++){const counter=Buffer.alloc(4);counter.writeUInt32LE(i);expected=createHash('sha512').update(Buffer.concat([expected,counter])).digest();}
 assert.equal(protection.hashValue,expected.toString('base64'));
 assert.ok(b.getWorksheet('Datos ñ').conditionalFormattings.length);
});
test('browser worksheet protection requires secure randomness and fails closed without WebCrypto',async()=>{
 const c=realm(artifact,{secure:false});
 await assert.rejects(vm.runInContext("(async()=>{const w=new ExcelJS.Workbook();await w.addWorksheet('A').protect('p',{spinCount:1});})()",c),/Secure random|crypto|getRandomValues/i);
});
