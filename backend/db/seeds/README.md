# Dominio demo objetivo

`backend/db/seed.sql` exige esquema `033`, catálogo territorial `32/2478`, un
administrador creado con `scripts/create_admin.py` y dominio funcional vacío.
No crea cuentas ni contiene secretos.

La ejecución soportada instala también el archivo documental QA y valida su
hash:

```bash
APP_ENV=test DB_NAME=software_pa_seed_test SEED_OBJECTIVE_CONFIRM=1 \
  python scripts/seed_objective_demo.py
```

Los nombres, parcelas y valores provenientes de Excel conservan filas/columnas
en `trazabilidad_fuente`. Toda ampliación, geometría o dato que no es literal de
fuente está marcado `SINTÉTICO QA` en observaciones/trazabilidad.
