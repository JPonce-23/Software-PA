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
  test(`administración territorial y usuarios en ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await login(page);

    await page.goto('/administracion/territorio');
    await expect(page.getByRole('heading', { name: 'Administración territorial' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Proyectos' })).toBeVisible();
    await expect(page.locator('.admin-table tbody tr').first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await page.screenshot({ path: `test-results/administracion-territorial-${viewport.name}.png`, fullPage: true });

    await page.goto('/administracion/importaciones-geoespaciales');
    await expect(page.getByRole('heading', { name: 'Importaciones geoespaciales' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cargar archivo' })).toBeVisible();
    await expect(page.locator('.geo-import-list > button').first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await page.screenshot({ path: `test-results/importaciones-geoespaciales-${viewport.name}.png`, fullPage: true });

    await page.goto('/administracion/usuarios');
    await expect(page.getByRole('heading', { name: 'Administración de usuarios' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Nuevo usuario' })).toBeVisible();
    await expect(page.locator('.admin-table tbody tr').first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    await page.screenshot({ path: `test-results/administracion-usuarios-${viewport.name}.png`, fullPage: true });
  });
}
