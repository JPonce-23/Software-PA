# Evaluación técnica - Corte 3: Seguridad inmediata

Fecha: 2026-08-04

## 1. **Trabajo vigente identificado**

`ESTADO_PROYECTO.md` todavía marca como próximo paso la validación funcional
del Subcorte 2C. En esta conversación el usuario informa que 2C ya fue
validado y aprobado; con esa actualización, el siguiente trabajo del plan
vigente es el **Corte 3 - Seguridad inmediata**.

Alcance vigente confirmado en `ESTADO_PROYECTO.md`:

- Rotar credenciales y `SECRET_KEY` expuestos en historial.
- Crear el `.env` local de cada entorno y documentar configuración y
  recuperación.
- No copiar credenciales actuales a documentación nueva.

El Corte 4 sigue separado: cookies HttpOnly o equivalente, sesiones,
revocación, logout real, registro de accesos, bloqueo por intentos, expiración
por inactividad y pruebas completas de autenticación.

## 2. **Resumen de la propuesta evaluada**

Propuesta evaluada:
`docs/propuestas/2026-08-04-corte-3-seguridad-inmediata-propuesta.md`.

La propuesta separa el trabajo en:

- 3A: rotación y bootstrap seguro, documentación, eliminación de credenciales
  fijas de instalación y validación de placeholders.
- 3B: preparación de autenticación formal con endpoints, metadatos de usuario,
  política de contraseñas y cambios de frontend.

Durante esta evaluación se corrigió la propuesta para dejar explícito que sólo
3A es viable sin aprobación adicional. La rotación real de secretos por
ambiente requiere custodia externa y no puede declararse completada por cambios
de repositorio. 3B queda diferido al Corte 4 o a una aprobación funcional
posterior.

## 3. **Hallazgos de auditoría**

| ID | Hallazgo | Severidad | Decisión |
| --- | --- | --- | --- |
| C3-01 | `backend/scripts/create_admin.py` contiene credenciales fijas de desarrollo y puede crear una cuenta insegura en un entorno compartido. | Alta | Aprobada con ajustes: eliminar valores fijos y exigir variables/prompt. |
| C3-02 | `backend/db/seed.sql` crea un admin con hash conocido. | Alta | Aprobada con ajustes: retirar credencial operativa del seed. |
| C3-03 | `backend/app/auth.py` exige `SECRET_KEY`, pero no rechaza placeholders de `.env.example`. | Alta | Aprobada: validar placeholders/longitud en arranque. |
| C3-04 | La rotación real de secretos no se puede ejecutar ni verificar desde el repo sin valores/custodio por ambiente. | Alta | Pendiente de validación operativa; no bloquea hardening de repositorio. |
| C3-05 | Login, sesiones, bloqueo por intentos y logout real no existen. | Media | Rechazada para este corte: pertenece a Corte 4. |
| C3-06 | JWT sigue en `localStorage`. | Media | Rechazada para este corte: `ESTADO_PROYECTO.md` lo ubica en Corte 4. |
| C3-07 | Pruebas dependen de credenciales fijas de desarrollo. | Media | Aprobada con ajustes: fixtures deben crear/usar usuario de prueba sin credencial operativa codificada como bootstrap. |
| C3-08 | El esquema real tiene migraciones 004-007, `usuario` sin campos de bloqueo y sin tablas de sesión/acceso. | Informativa | Confirma que no debe implementarse 3B sin migración aprobada. |

## 4. **Matriz de evaluación**

| Área | Resultado | Evidencia | Ajuste requerido |
| --- | --- | --- | --- |
| Funcional | Aprobada con ajustes | Corte 3 pendiente es seguridad inmediata; 3B cruza a Corte 4. | Implementar sólo 3A de repositorio. |
| Modelo de datos | Aprobada | `usuario` actual basta para retirar credenciales fijas; no se requieren cambios de dominio. | No crear migración 008 en este subcorte. |
| Migraciones | Aprobada | Esquema real registra 004, 005, 006 y 007; no hay cambio de esquema requerido para 3A. | No ejecutar migraciones. |
| ORM | Aprobada | `models.Usuario` soporta creación de admin seguro con campos actuales. | Mantener sin cambios salvo que 3B se apruebe. |
| Contratos | Aprobada | `UsuarioCreate` y `Token` no requieren cambios para 3A. | No implementar política formal de contraseña todavía. |
| Servicios | Aprobada con ajustes | `auth.py` centraliza hash/JWT y puede validar configuración. | Rechazar `SECRET_KEY` insegura al importar. |
| Endpoints | Aprobada | `/api/auth/login` y `/api/usuarios` no necesitan cambios para 3A. | No agregar `/me` ni `/logout` en este corte. |
| Autorización | Aprobada | Gestión de usuarios sigue admin-only; `usuario_tramo` no se altera. | Mantener RBAC y territorio intactos. |
| Frontend | Aprobada | Cambios de `localStorage` pertenecen a Corte 4. | No modificar frontend en 3A. |
| Pruebas | Aprobada con ajustes | `test_auth.py` y `conftest.py` usan credenciales de desarrollo. | Adaptar a variables de prueba o fixture robusto. |
| Documentación | Aprobada | `README.md` y `docs/migraciones.md` ya cubren partes, pero falta rotación completa. | Documentar bootstrap seguro y checklist. |

## 5. **Resultado de los gates**

| Gate | Resultado | Evidencia |
| --- | --- | --- |
| Funcional | Pasa con ajuste | 3A atiende Corte 3 sin reabrir 2A/2B/2C; 3B queda fuera. |
| Datos | Pasa | No hay cambio de esquema ni datos operativos; no se infieren relaciones. |
| Seguridad | Pasa con ajuste | Se retiran credenciales fijas de bootstrap y se valida `SECRET_KEY`; rotación real queda operativa. |
| Arquitectura | Pasa | Cambios concentrados en config/bootstrap/docs/tests. |
| Migración | Pasa | No aplica migración para 3A. |
| Pruebas | Pasa con ajuste | Se requiere actualizar pruebas de auth/bootstrap y ejecutar suite relevante. |

## 6. **Propuesta corregida**

Implementar únicamente el subalcance 3A de repositorio:

1. Endurecer `backend/app/auth.py` para rechazar `SECRET_KEY` vacía,
   placeholder o demasiado corta.
2. Reescribir `backend/scripts/create_admin.py` para no contener credenciales
   fijas, usar variables/prompt, validar datos mínimos, usar fecha con zona y
   asegurar que los triggers se rehabiliten aun ante error.
3. Retirar la creación de admin de `backend/db/seed.sql`; conservar catálogos y
   datos territoriales semilla.
4. Actualizar `.env.example`, `README.md` y `docs/migraciones.md` sin secretos.
5. Adaptar pruebas para no depender de credenciales de bootstrap fijas.
6. No tocar frontend, sesiones, cookies, bloqueo por intentos ni migraciones.

## 7. **Decisión de viabilidad**

**Propuesta viable con alcance corregido.**

No es viable implementar la propuesta completa porque incluye decisiones de
Corte 4 y rotación operativa de secretos que exige valores/custodia externa.
Sí es viable implementar 3A como hardening de repositorio y documentación,
dejando el estado final como implementación parcial hasta que la rotación real
se ejecute y valide en cada ambiente.

## 8. **Plan final de implementación**

1. Registrar estado Git inicial.
2. Cambiar validación de `SECRET_KEY`.
3. Reescribir script de bootstrap admin.
4. Quitar admin conocido de `seed.sql`.
5. Adaptar fixtures/pruebas de autenticación.
6. Actualizar documentación operativa.
7. Ejecutar pruebas relevantes de backend.
8. Ejecutar validaciones estáticas de secretos y diff.
9. Actualizar `ESTADO_PROYECTO.md` sólo con lo realmente implementado:
   3A de repositorio parcial, rotación operativa pendiente.

## 9. **Cambios realizados**

| Archivo | Cambio | Justificación |
| --- | --- | --- |
| `backend/app/auth.py` | Agrega validación de `SECRET_KEY` contra ausencia, placeholders y longitud menor a 32 caracteres. | Evitar arranque con `.env.example` o secretos triviales. |
| `backend/scripts/create_admin.py` | Reescribe bootstrap admin sin credenciales fijas; usa variables/prompt, valida configuración, fecha con zona y rehabilitación de triggers. | Crear primer administrador sin dejar credenciales conocidas en código. |
| `backend/db/seed.sql` | Retira creación de admin y hash conocido; exige admin activo previo para auditoría. | Separar datos semilla de credenciales operativas. |
| `.env.example` | Agrega variables placeholder no sensibles para bootstrap admin; no conserva `ADMIN_PASSWORD` persistente. | Documentar configuración necesaria sin valores reales. |
| `README.md` | Documenta bootstrap seguro, validación de `SECRET_KEY` y que `seed.sql` ya no crea usuarios. | Reducir errores operativos de instalación. |
| `docs/migraciones.md` | Agrega checklist de rotación de secretos por ambiente y actualiza instalación nueva. | Cubrir el pendiente del Corte 3 sin revelar secretos. |
| `backend/tests/conftest.py` | Permite `TEST_ADMIN_EMAIL` y `TEST_ADMIN_PASSWORD` para credenciales de prueba por ambiente. | Evitar acoplar pruebas al bootstrap operativo fijo. |
| `backend/tests/test_auth.py` | Usa fixture de credenciales y agrega pruebas de hardening de `SECRET_KEY` y bootstrap. | Validar reglas nuevas. |
| `backend/tests/test_reportes_y_endpoints_especiales.py` | Usa fixture de credenciales en reautenticaciones internas. | Mantener pruebas compatibles con credenciales por ambiente. |
| `docs/propuestas/2026-08-04-corte-3-seguridad-inmediata-propuesta.md` | Corrige alcance: 3A viable, rotación real y 3B pendientes. | Alinear propuesta con gates y Corte 4. |
| `ESTADO_PROYECTO.md` | Registra 2C validado por continuidad, 3A de repositorio implementado y rotación operativa pendiente. | Mantener continuidad real sin declarar rotación no ejecutada. |

## 10. **Migraciones y compatibilidad**

No se creó ni ejecutó migración. El esquema real fue verificado por consultas
de solo lectura:

- `schema_migrations`: `004`, `005`, `006`, `007`.
- `usuario`: 16 columnas actuales, sin metadatos de sesión/bloqueo.
- `evento_acceso` y `sesion_usuario`: no existen.

Compatibilidad:

- Instalaciones existentes conservan usuarios y tokens actuales mientras no se
  rote `SECRET_KEY`.
- Instalaciones nuevas deben crear admin con `scripts/create_admin.py`; el
  seed operativo ya no crea usuarios.
- `seed.sql` ahora requiere un administrador activo antes de insertar datos
  semilla auditables.
- No se modificaron tablas operativas, relaciones territoriales, reglas 2A/2B
  ni navegación 2C.

## 11. **Pruebas y validaciones**

| Validación | Comando | Resultado | Estado |
| --- | --- | --- | --- |
| Esquema real | `docker compose exec -T db ... SELECT version ... information_schema.columns ...` | 004-007 aplicadas; sin tablas de sesión/acceso. | Aprobada |
| Sintaxis sin `.pyc` | `python3 -c "import ast, pathlib; ..."` | Sin errores. | Aprobada |
| Auth focalizado | `docker compose exec -T backend pytest tests/test_auth.py` | 28 passed, 1 advertencia Starlette. | Aprobada |
| Reportes/asignación | `docker compose exec -T backend pytest tests/test_reportes_y_endpoints_especiales.py` | 11 passed, 1 advertencia Starlette. | Aprobada |
| Bootstrap sin variables | `docker compose exec -T backend python scripts/create_admin.py` | Falla cerrado: exige `ADMIN_PASSWORD` o terminal interactiva. | Aprobada |
| Suite backend completa | `docker compose exec -T backend pytest` | 110 passed, 1 advertencia Starlette. | Aprobada |
| Frontend lint | `npx oxlint src` | Sin errores. Primer intento falló por DNS; reintento con red permitió resolver paquete. | Aprobada |
| Diff whitespace | `git diff --check` | Sin errores. | Aprobada |
| Búsqueda enfocada de secretos | `rg ... backend/app backend/scripts backend/db README.md docs/...` | Sin coincidencias de credenciales conocidas en archivos operativos tocados. | Aprobada |

## 12. **Riesgos restantes**

- La rotación real de `SECRET_KEY`, PostgreSQL, PgAdmin y cuentas
  administrativas no fue ejecutada; requiere custodia y valores por ambiente.
- JWT sigue en `localStorage`, sin revocación ni logout servidor. Esto queda
  pendiente para Corte 4.
- No hay registro de login exitoso/fallido ni bloqueo por cinco intentos;
  también pertenece al Corte 4.
- `seed.sql` ahora falla si se ejecuta antes de crear admin. Es intencional,
  pero exige seguir la documentación actualizada.
- El primer intento de `npx oxlint src` necesitó red porque el paquete no
  estaba disponible localmente.

## 13. **Actualización realizada en `ESTADO_PROYECTO.md`**

Se actualizó:

- Encabezado de próximo trabajo funcional.
- Estado de aceptación funcional de 2C, según continuidad indicada por el
  usuario.
- Registro de "Corte 3 - Seguridad inmediata: 3A de repositorio implementado".
- Lista de pendientes del Corte 3, dejando la rotación operativa como no
  completada.
- Trabajo técnico transversal y próximos pasos.

No se marcó el Corte 3 como terminado porque la rotación real por ambiente no
se ejecutó ni puede verificarse desde el repositorio.

## 14. **Estado final**

**Implementación parcial.**

El hardening de repositorio del Corte 3A fue implementado y validado con suite
backend completa, lint frontend y revisión de diff. La propuesta completa no
queda cerrada porque falta la rotación operativa de secretos por ambiente y
porque las capacidades de sesión, revocación, bloqueo e inactividad pertenecen
al Corte 4.
