import { expect, test } from '@playwright/test';

const email = process.env.TEST_ADMIN_EMAIL;
const password = process.env.TEST_ADMIN_PASSWORD;

async function login(page) {
  if (!email || !password) throw new Error('TEST_ADMIN_EMAIL y TEST_ADMIN_PASSWORD son obligatorios');
  await page.goto('/login');
  await page.getByLabel('Correo Institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL('/');
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`expediente, representación y afectación en ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await login(page);

    const expedientesResponse = await page.request.get('/api/tramos-nucleos');
    expect(expedientesResponse.ok()).toBe(true);
    const expedientes = await expedientesResponse.json();
    expect(expedientes.length).toBeGreaterThan(0);
    const expediente = expedientes[0];

    await page.goto(`/expedientes/${expediente.id_tramo_nucleo}`);
    await expect(page.getByText('EXPEDIENTE DEL NÚCLEO EN EL TRAMO')).toBeVisible();
    await page.getByRole('tab', { name: 'Representación' }).click();
    await expect(page.getByRole('heading', { name: 'Órganos de representación y vigilancia' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Historial del padrón' })).toBeVisible();

    await page.getByRole('tab', { name: 'Flujo de liberación' }).click();
    await expect(page.getByRole('heading', { name: 'Secuencia de liberación' })).toBeVisible();

    const afectacionesResponse = await page.request.get(
      `/api/afectaciones?id_tramo_nucleo=${expediente.id_tramo_nucleo}`,
    );
    expect(afectacionesResponse.ok()).toBe(true);
    const afectaciones = await afectacionesResponse.json();
    if (afectaciones.length > 0) {
      await page.goto(
        `/expedientes/${expediente.id_tramo_nucleo}/afectaciones/${afectaciones[0].id_afectacion}`,
      );
      await expect(page.getByText(`AFECTACIÓN #${afectaciones[0].id_afectacion}`)).toBeVisible();
      await expect(page.getByText('SUBEXPEDIENTE', { exact: true })).toHaveCount(0);
    }

    const pageWidth = await page.evaluate(() => ({
      client: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
    }));
    expect(pageWidth.scroll).toBeLessThanOrEqual(pageWidth.client);
    await page.screenshot({ path: `test-results/expediente-alineado-${viewport.name}.png`, fullPage: true });
  });
}
