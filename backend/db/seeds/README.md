# Dominio demo objetivo

`backend/db/seed.sql` exige Baseline V1 (`schema_migrations=001`), catálogo territorial `32/2478`, un
administrador creado con `scripts/create_admin.py` y dominio funcional vacío.
No crea cuentas ni contiene secretos.

La ejecución soportada usa exclusivamente el modelo canónico:

```bash
APP_ENV=test DB_NAME=software_pa_seed_test SEED_OBJECTIVE_CONFIRM=1 \
  python scripts/seed_objective_demo.py
```

Los valores de prueba registran su origen en `trazabilidad_fuente`. No se
crean `bien_afectado`, campos planos de RAN/FIFONAFE ni responsables
duplicados en `proyecto_nucleo`.
