import { expect, test } from '@playwright/test';

const adminEmail = process.env.TEST_ADMIN_EMAIL;
const adminPassword = process.env.TEST_ADMIN_PASSWORD;
const uatPassword = process.env.UAT_PASSWORD;

async function login(page, email, password) {
  if (!email || !password) throw new Error('Las credenciales E2E son obligatorias');
  await page.goto('/login');
  await page.getByLabel('Correo Institucional').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL('/dashboard');
}

async function csrfHeaders(page) {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'pa_csrf_dev' || cookie.name === '__Host-pa_csrf');
  expect(csrf).toBeTruthy();
  return { Origin: 'http://localhost:5173', 'X-CSRF-Token': csrf.value };
}

test('administración usa asignaciones por proyecto', async ({ page }) => {
  await login(page, adminEmail, adminPassword);
  await page.goto('/administracion/usuarios');
  await expect(page.getByRole('heading', { name: 'Usuarios y accesos' })).toBeVisible();
  await expect(page.getByText('uat.operador@pa.test')).toBeVisible();
  await expect(page.getByText('uat.visualizador@pa.test')).toBeVisible();
  await expect(page.getByText('uat.geografo@pa.test')).toBeVisible();
  await expect(page.getByText('MÉXICO-QUERÉTARO').first()).toBeVisible();

  await page.goto('/importaciones');
  await expect(page.getByRole('heading', { name: 'Importaciones geoespaciales' })).toBeVisible();
  await expect(page.getByRole('option', { name: 'Trazo del proyecto' })).toBeAttached();
  await expect(page.getByRole('option', { name: 'Núcleo agrario' })).toBeAttached();
  await expect(page.getByRole('option', { name: 'Parcela' })).toBeAttached();
});

for (const profile of [
  { role: 'operador', email: 'uat.operador@pa.test', canCapture: true, canUseGis: false },
  { role: 'visualizador', email: 'uat.visualizador@pa.test', canCapture: false, canUseGis: false },
  { role: 'geografo', email: 'uat.geografo@pa.test', canCapture: false, canUseGis: true },
]) {
  test(`RBAC objetivo para ${profile.role}`, async ({ page }) => {
    await login(page, profile.email, uatPassword);
    const projectsResponse = await page.request.get('/api/proyectos');
    expect(projectsResponse.ok()).toBe(true);
    const projects = await projectsResponse.json();
    expect(projects).toHaveLength(1);
    expect(projects[0].clave_proyecto).toBe('MEX-QRO');

    const nuclei = await (await page.request.get(`/api/proyectos/${projects[0].id_proyecto}/nucleos`)).json();
    const nucleus = nuclei.find((item) => item.nombre_nucleo === 'AHORCADO');
    await page.goto(`/proyecto-nucleo/${nucleus.id_proyecto_nucleo}`);
    await page.getByRole('tab', { name: 'Sensibilización' }).click();
    if (profile.canCapture) {
      await expect(page.getByRole('button', { name: 'Registrar actividad' })).toBeVisible();
    } else {
      await expect(page.getByRole('button', { name: 'Registrar actividad' })).toHaveCount(0);
    }

    const headers = await csrfHeaders(page);
    if (profile.role === 'visualizador') {
      const write = await page.request.post(`/api/proyecto-nucleo/${nucleus.id_proyecto_nucleo}/actividades`, {
        headers,
        data: { tipo_actividad: 'sensibilizacion', contexto_actividad: 'general' },
      });
      expect(write.status()).toBe(403);
    }
    if (profile.role === 'geografo') {
      await expect(page.getByRole('link', { name: 'Importaciones GIS' })).toBeVisible();
      const financial = await page.request.post(`/api/proyecto-nucleo/${nucleus.id_proyecto_nucleo}/afectaciones`, {
        headers,
        data: { tipo_afectacion: 'colectivo' },
      });
      expect(financial.status()).toBe(403);
    } else {
      await expect(page.getByRole('link', { name: 'Importaciones GIS' })).toHaveCount(0);
    }

    await page.goto('/administracion/usuarios');
    await expect(page).toHaveURL('/dashboard');
  });
}
