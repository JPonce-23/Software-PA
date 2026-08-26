import { expect, test } from '@playwright/test';

const adminEmail = process.env.TEST_ADMIN_EMAIL;
const adminPassword = process.env.TEST_ADMIN_PASSWORD;

async function login(page, email = adminEmail, password = adminPassword) {
  if (!email || !password) throw new Error('Las credenciales E2E son obligatorias');
  await page.goto('/login');
  await page.getByLabel('Correo Institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL('/dashboard');
}

async function objectiveContext(page) {
  const projectsResponse = await page.request.get('/api/proyectos');
  expect(projectsResponse.ok()).toBe(true);
  const projects = await projectsResponse.json();
  const main = projects.find((item) => item.clave_proyecto === 'MEX-QRO');
  const empty = projects.find((item) => item.clave_proyecto === 'QRO-IRA');
  expect(main).toBeTruthy();
  expect(empty).toBeTruthy();

  const nucleiResponse = await page.request.get(`/api/proyectos/${main.id_proyecto}/nucleos`);
  expect(nucleiResponse.ok()).toBe(true);
  const nuclei = await nucleiResponse.json();
  expect(nuclei).toHaveLength(5);
  return { main, empty, nuclei };
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`Proyecto → Entidad → Municipio → Núcleo en ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await login(page);
    const { main, nuclei } = await objectiveContext(page);
    const collectiveNucleus = nuclei.find((item) => item.nombre_nucleo === 'SAN ILDEFONSO');
    const individualNucleus = nuclei.find((item) => item.nombre_nucleo === 'AHORCADO');
    expect(collectiveNucleus).toBeTruthy();
    expect(individualNucleus).toBeTruthy();

    await page.goto(`/proyectos?id_proyecto=${main.id_proyecto}`);
    await expect(page.getByRole('heading', { name: 'Proyecto → Entidad → Municipio → Núcleo' })).toBeVisible();
    await page.getByLabel('Entidad').selectOption({ label: 'Querétaro' });
    await page.getByLabel('Municipio').selectOption({ label: 'Pedro Escobedo' });
    await expect(page.getByRole('heading', { name: 'AHORCADO' })).toBeVisible();

    await page.goto(`/proyecto-nucleo/${collectiveNucleus.id_proyecto_nucleo}`);
    await expect(page.getByRole('heading', { name: 'SAN ILDEFONSO' })).toBeVisible();
    await page.getByRole('tab', { name: 'Derechos colectivos' }).click();
    await expect(page.getByRole('heading', { name: 'Afectaciones colectivas' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Asambleas del núcleo' })).toBeVisible();
    await expect(page.getByText('2 afectación(es)')).toBeVisible();
    await expect(page.getByText('Oficios: 4/4')).toBeVisible();

    const collectiveAffectations = await (await page.request.get(
      `/api/proyecto-nucleo/${collectiveNucleus.id_proyecto_nucleo}/afectaciones`,
    )).json();
    const primary = collectiveAffectations.find((item) => item.tipo_afectacion === 'colectivo');
    expect(primary).toBeTruthy();
    await page.goto(`/afectaciones/${primary.id_afectacion}`);
    await expect(page.getByRole('heading', { name: /Afectación colectivo/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Convenios' })).toBeVisible();
    await expect(page.getByText('2 vínculo(s)').first()).toBeVisible();
    await expect(page.getByText(/2 afectaciones · sin conflictos/i)).toBeVisible();

    await page.goto(`/proyecto-nucleo/${individualNucleus.id_proyecto_nucleo}`);
    await page.getByRole('tab', { name: 'Parcelas / Derechos individuales' }).click();
    await expect(page.getByRole('heading', { name: 'Parcelas y derechos individuales' })).toBeVisible();
    const parcel170 = page.locator('article.record').filter({ hasText: 'Parcela P-170' });
    await expect(parcel170).toContainText('sin geometría');
    await expect(page.getByText('4 afectación(es)')).toBeVisible();

    const width = await page.evaluate(() => ({
      client: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
    }));
    expect(width.scroll).toBeLessThanOrEqual(width.client);
  });
}

test('dashboard derivado sin duplicación N:M', async ({ page }) => {
  await login(page);
  const { main } = await objectiveContext(page);
  const response = await page.request.get(`/api/dashboard/kpi?id_proyecto=${main.id_proyecto}&anio=2025`);
  expect(response.ok()).toBe(true);
  const rows = await response.json();
  const byIndicator = Object.fromEntries(rows.map((row) => [row.indicador, row]));
  expect(byIndicator.nucleos.cantidad).toBe(5);
  expect(byIndicator.cop_colectivos.cantidad).toBe(2);
  expect(byIndicator.cop_individuales.cantidad).toBe(2);
  expect(byIndicator.fifonafe.cantidad).toBe(2);
  expect(byIndicator.indemnizaciones.cantidad).toBe(1);
  expect(byIndicator.pagos.cantidad).toBe(2);

  await page.goto('/dashboard');
  await page.getByLabel('Proyecto').selectOption(String(main.id_proyecto));
  await page.getByLabel('Año').selectOption('2025');
  await expect(page.getByRole('heading', { name: 'Dashboard del modelo objetivo' })).toBeVisible();
  await expect(page.locator('.kpi-card')).toHaveCount(rows.length);
  await expect(page.getByText(/vínculos N:M no multiplican indicadores/i)).toBeVisible();
});

test('mapa por proyecto y estado vacío sin gate geométrico', async ({ page }) => {
  await page.route('**/tile.openstreetmap.org/**', (route) => route.abort());
  await login(page);
  const { main, empty } = await objectiveContext(page);

  const geoResponse = await page.request.get(`/api/proyectos/${main.id_proyecto}/mapa`);
  expect(geoResponse.ok()).toBe(true);
  const geojson = await geoResponse.json();
  const types = new Set(geojson.features.map((feature) => feature.properties.tipo));
  expect(types).toEqual(new Set(['trazo_proyecto', 'nucleo_agrario', 'parcela']));

  await page.goto('/mapa');
  await page.getByLabel('Proyecto').selectOption(String(main.id_proyecto));
  await expect(page.getByRole('heading', { name: 'Mapa por proyecto' })).toBeVisible();
  await expect(page.locator('.map-frame')).toBeVisible();

  await page.getByLabel('Proyecto').selectOption(String(empty.id_proyecto));
  await expect(page.getByText('Proyecto sin geometrías', { exact: true })).toBeVisible();
  await expect(page.getByText('Puede capturarse todo el expediente aun cuando no exista cartografía.')).toBeVisible();
});
