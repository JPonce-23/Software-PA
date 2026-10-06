// Fixture de lectura: comprueba respuestas desordenadas sin importar geometrías reales.
const {chromium}=require(process.env.QA_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict');
(async()=>{
    const browser=await chromium.launch({channel:'msedge',headless:true});
    try{
        const base='http://127.0.0.1:5184', context=await browser.newContext({viewport:{width:1440,height:1000}});
        const auth=await context.request.post(base+'/api/auth/sesiones',{headers:{Origin:base},form:{username:process.env.QA_USER,password:process.env.QA_PASSWORD}});assert.equal(auth.status(),200);
        const proyectos=await(await context.request.get(base+'/api/proyectos')).json();assert.ok(proyectos.length>=2,'Se requieren dos proyectos reales visibles para la prueba');
        const [a,b]=proyectos.map(p=>p.id_proyecto);const page=await context.newPage();const errores=[];
        page.on('pageerror',e=>errores.push(e.message));await page.route('**/api/**',route=>route.request().method()==='GET'?route.continue():route.abort());
        let liberar, recibida;const espera=new Promise(resolve=>{liberar=resolve;}), solicitud=new Promise(resolve=>{recibida=resolve;});
        await page.route('**/api/proyectos/*/mapa',async route=>{
            const pid=Number(route.request().url().match(/proyectos\/(\d+)\/mapa/)[1]);
            if(pid===a){recibida();await espera;}
            await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({type:'FeatureCollection',features:[{type:'Feature',geometry:{type:'LineString',coordinates:[[-99,19],[-99.01,19.01]]},properties:{tipo:'trazo_proyecto',id:pid,nombre:'Trazo de prueba de aislamiento'}}]})});
        });
        await page.goto(base+'/pages/mapa.html');await page.waitForLoadState('networkidle');
        await page.evaluate(()=>{window.qaCapas=[];const original=L.geoJSON;L.geoJSON=function(feature,...args){if(feature?.properties)qaCapas.push(feature.properties.id_proyecto);return original.call(this,feature,...args);};});
        await page.locator('#selectorProyectoMapa').selectOption(String(a));await solicitud;
        await page.locator('#selectorProyectoMapa').selectOption(String(b));await page.waitForFunction(pid=>window.qaCapas.includes(pid),b);
        liberar();await page.waitForLoadState('networkidle');
        assert.deepEqual(await page.evaluate(()=>window.qaCapas),[b],'La respuesta tardía no debe agregar capas del proyecto anterior');
        assert.equal(new URL(page.url()).searchParams.get('id_proyecto'),String(b));assert.deepEqual(errores,[]);
        console.log('AISLAMIENTO_MAPA_OK: respuesta anterior descartada antes de dibujar');
    }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
