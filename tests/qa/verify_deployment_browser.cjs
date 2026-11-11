const assert = require('node:assert/strict');
const { chromium } = require('/opt/pr6-browser/node_modules/playwright');
const net = require('node:net');
const BASE = 'https://ssalfer.qa.invalid';
assert.equal(process.env.PR6_DEPLOY_QA, 'SYNTHETIC_DISPOSABLE_ONLY');
async function inaccessible(host, port) {
  await new Promise((resolve, reject) => {
    const socket = net.createConnection({host, port});
    socket.setTimeout(2000);
    socket.on('connect', () => {socket.destroy();reject(new Error(`unexpected direct access ${host}:${port}`));});
    socket.on('error', () => {socket.destroy();resolve();});
    socket.on('timeout', () => {socket.destroy();resolve();});
  });
}
(async () => {
  for (const [host, port] of [['backend',8000],['db',5432],['pgadmin',80],['ssalfer.qa.invalid',8000]]) await inaccessible(host,port);
  console.log('PASS ingress_cannot_connect_direct_backend_postgres_pgadmin');
  const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
  const context = await browser.newContext({ignoreHTTPSErrors:true,acceptDownloads:true});
  // Lab certificate trust was checked with a real CA verification by HTTPX.
  // Block external map tiles and other external requests in this browser smoke.
  await context.route('**/*',route => new URL(route.request().url()).hostname==='ssalfer.qa.invalid'?route.continue():route.abort());
  const page = await context.newPage(), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE+'/Index.html');
  await page.fill('#usuario',process.env.QA_USERNAME);
  await page.fill('#password',process.env.QA_PASSWORD);
  await Promise.all([page.waitForURL('**/dashboard.html'),page.click('#btnLogin')]);
  await page.locator('#btnExportarDashboardExcel:not([disabled])').waitFor({timeout:60000});
  const [download] = await Promise.all([page.waitForEvent('download'),page.click('#btnExportarDashboardExcel')]);
  const stream = await download.createReadStream(), chunks=[];
  for await (const chunk of stream) chunks.push(chunk);
  const data=Buffer.concat(chunks);
  assert.equal(data.subarray(0,2).toString(),'PK');
  assert.equal(download.suggestedFilename(),'SSALFER-dashboard.xlsx');
  assert.ok(data.length>1000);
  console.log('PASS browser_login_and_dashboard_xlsx_export',data.length);
  const mapResponse=page.waitForResponse(r=>r.url().endsWith('/api/proyectos/1/mapa')&&r.status()===200);
  await page.goto(BASE+'/pages/mapa.html?id_proyecto=1');
  await mapResponse;
  // The existing map explicitly uses Leaflet preferCanvas=true.
  await page.locator('#mapa .leaflet-overlay-pane canvas').first().waitFor({timeout:30000});
  await page.waitForFunction(() => [...document.querySelectorAll('#mapa .leaflet-overlay-pane canvas')].some(canvas => {
    const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
    for(let i=3;i<pixels.length;i+=4) if(pixels[i]>0) return true;
    return false;
  }));
  assert.equal(await page.locator('#selectorProyectoMapa').inputValue(),'1');
  assert.deepEqual(errors,[]);
  console.log('PASS browser_leaflet_map_with_confirmed_synthetic_geometry_no_page_errors');
  await browser.close();
})().catch(e=>{console.error(e.message);process.exit(1);});
