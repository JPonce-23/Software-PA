# Contrato de API REST para Frontend — SOFTWARE-PA Baseline V1

**Versión:** 2.0.0 (Baseline V1 Canónico)
**Fecha de corte:** Septiembre 2026
**Audiencia:** Desarrolladores Frontend / Integración UI
**Alcance:** 29 Flujos Funcionales de Captura, Consulta, Cartografía y Reporteo

---

## 1. Principios de Integración y Seguridad

### 1.1 Autenticación y Sesiones
- **Mecanismo:** Cookies de sesión `HttpOnly` emitidas por el backend tras login exitoso.
- **Protección CSRF:**
  - El backend emite una cookie accesible por JS llamada `pa_csrf`.
  - Toda petición mutadora (`POST`, `PUT`, `PATCH`, `DELETE`) en rutas `/api/*` **debe** incluir el encabezado HTTP:
    ```http
    X-CSRF-Token: <valor_de_cookie_pa_csrf>
    ```
- **Formato:** Todas las peticiones mutadoras envían `Content-Type: application/json`.
- **Estatus de Sesión:** `GET /api/auth/sesion` permite verificar si el usuario sigue autenticado y obtener su perfil, rol y proyectos autorizados.

### 1.2 Control de Acceso Basado en Roles (RBAC) y Ámbitos de Proyecto
- **Roles del Sistema:**
  - `admin`: Administrador global del sistema. Acceso irrestricto de lectura y escritura a todos los proyectos y módulos de gestión de usuarios/catálogos.
  - `operador`: Capturista operativo. Acceso de lectura y escritura a los proyectos asignados explícitamente en `usuario_proyecto`.
  - `visualizador`: Consulta y reporteo. Acceso de solo lectura (`GET`) a los proyectos asignados.
  - `geografo`: Especialista SIG. Acceso de lectura a proyectos asignados y escritura en trazos cartográficos (`/api/proyectos/{id}/trazos`) e importaciones geoespaciales.
- **Validación de Ámbito:** Las operaciones sobre entidades vinculadas a un proyecto (e.g. `ProyectoNucleo`, `Afectacion`, `Asamblea`, `Convenio`, `TramiteRan`, etc.) verifican que el usuario posea permisos activos sobre el proyecto correspondiente.

### 1.3 Respuestas de Error Estándar
| Código HTTP | Causa Principal | Formato JSON |
|---|---|---|
| `401 Unauthorized` | Sesión no iniciada, expirada o inválida. | `{"detail": "No autenticado"}` |
| `403 Forbidden` | Rol insuficiente, proyecto no asignado o CSRF inválido. | `{"detail": "Operación no permitida para este rol"}` |
| `404 Not Found` | Recurso o ruta no encontrada / inactiva. | `{"detail": "Recurso no encontrado"}` |
| `409 Conflict` | Violación de regla de integridad relacional o clave única. | `{"detail": "La operación entra en conflicto con la integridad de los datos."}` |
| `422 Unprocessable Entity` | Error de validación de esquema Pydantic (campo faltante, tipo erróneo o campo no permitido por `extra='forbid'`). | `{"detail": [{"loc": ["body", "campo"], "msg": "...", "type": "..."}]}` |

---

## 2. Catálogos del Sistema

### 2.1 Catálogo Territorial INEGI
Utilizado para los selectores de Entidad Federativa y Municipio.
- `GET /api/catalogos/entidades` → Lista de 32 estados de la República.
- `GET /api/catalogos/municipios?id_entidad={id}` → Lista de municipios de la entidad (2,478 municipios oficiales).

### 2.2 Catálogos Operativos Dinámicos
Endpoint unificado: `GET /api/catalogos/operativos/{tipo_catalogo}`

Lista de los 20 tipos de catálogo disponibles:
1. `tipo_tenencia` (`ejido`, `comunidad`)
2. `residencia` (`naucalpan`, `atlacomulco`, `tula`, `queretaro`)
3. `tipo_tierra` (`uso_comun`, `parcelada`, `asentamiento_humano`, `otra`, `no_determinada`)
4. `tipo_gestion` (`PARCELA`, `TUC`)
5. `destino_superficie` (`tuc`, `sin_asignar`, `favor_nucleo`, `parcela_escolar`, `uaim`, `camino`, `canal`, `derecho_paso`, `servidumbre_paso`, `infraestructura`, `asentamiento_humano`, `parcela_ejidal`, `solar`, `otro`)
6. `tipo_titularidad_unidad` (`nucleo_agrario`, `persona`, `copropiedad`, `no_determinada`, `otra`)
7. `tipo_asamblea` (`anuencia`, `retiro_fondos`, `otra`)
8. `contexto_asamblea` (`cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`, `retiro_fondos`, `otro`)
9. `resultado_convocatoria` (`celebrada`, `no_celebrada`, `suspendida`, `diferida`, `otro`)
10. `tipo_cop_operativo` (`cop_original`, `ampliacion`, `ampliacion_remanente`, `modificatorio`)
11. `calidad_compareciente_convenio` (`ejidatario`, `comunero`, `posesionario`, `avencindado`, `representante`, `otro`)
12. `estado_registral_orv` (`no_ingresada`, `en_proceso`, `prevenida`, `inscrita`, `otro`)
13. `organo_orv` (`comisariado`, `consejo_vigilancia`)
14. `cargo_orv` (`presidente`, `secretario`, `tesorero`, `secretario_1`, `secretario_2`)
15. `calidad_integrante_orv` (`propietario`, `suplente`)
16. `tipo_evento_ran` (`ingreso`, `reingreso`, `prevencion`, `subsanacion`, `desistimiento`, `calificacion`, `inscripcion`, `otro`)
17. `tipo_evento_fifonafe` (`oficio_fifonafe_dgaopr`, `oficio_dgaopr_representacion`, `respuesta_representacion_dgaopr`, `respuesta_dgaopr_fifonafe`, `solicitud_retiro_individual`, `acuse_retiro_individual`, `resolucion_retiro_individual`, `otro`)
18. `estado_requisito_documental` (`pendiente`, `en_revision`, `aprobado`, `rechazado`, `no_aplica`)
19. `tipo_acreditacion_derecho_individual` (`certificado_derechos_agrarios`, `certificado_parcelario`, `sentencia_tribunal_agrario`, `escritura_publica`, `contrato_enajenacion`, `otro`)
20. `motivo_no_afecta_tuc` (`fuera_derecho_via`, `error_topografico`, `acuerdo_asamblea`, `otro`)

---

## 3. Matriz de los 29 Flujos Funcionales

---

### Flujo 1: Autenticación y Sesión
- **Pantalla / Vista:** Login, Header de Usuario, Guardia de Rutas
- **Endpoints:**
  - `POST /api/auth/sesiones` (Login)
  - `GET /api/auth/sesion` (Verificar sesión actual)
  - `DELETE /api/auth/sesiones` (Logout)
- **Roles:** Público para login; autenticado para verificar/cerrar.
- **Request Body (Login):**
  ```json
  {
    "username": "operador.queretaro@pa.gob.mx",
    "password": "PasswordSeguro123!"
  }
  ```
  *(Nota: Se envía en formato `application/x-www-form-urlencoded` estándar OAuth2).*
- **Response Structure (`GET /api/auth/sesion`):**
  ```json
  {
    "id_usuario": 5,
    "nombre": "Alfredo",
    "apellido_paterno": "Cruz",
    "apellido_materno": "López",
    "correo": "alfredo.cruz@pa.gob.mx",
    "rol": "admin",
    "activo": true,
    "proyectos_asignados": [1, 2, 3]
  }
  ```

---

### Flujo 2: Gestión de Usuarios y Asignación de Proyectos
- **Pantalla / Vista:** Administración de Usuarios / Matriz de Acceso
- **Endpoints:**
  - `GET /api/usuarios`
  - `POST /api/usuarios`
  - `PATCH /api/usuarios/{id_usuario}`
  - `POST /api/proyectos/{id_proyecto}/usuarios` (Asignar proyecto)
  - `DELETE /api/proyectos/{id_proyecto}/usuarios/{id_usuario}` (Desasignar)
  - `POST /api/usuarios/{id_usuario}/desbloquear`
- **Roles:** `admin` exclusivamente.
- **Request Body (`POST /api/usuarios`):**
  ```json
  {
    "nombre": "Juan",
    "apellido_paterno": "Pérez",
    "apellido_materno": "Gómez",
    "correo": "juan.perez@pa.gob.mx",
    "contrasena": "PasswordComplejo123!",
    "rol": "operador"
  }
  ```

---

### Flujo 3: Administración de Proyectos
- **Pantalla / Vista:** Selector Global de Proyecto / Catálogo de Proyectos
- **Endpoints:**
  - `GET /api/proyectos`
  - `POST /api/proyectos`
  - `GET /api/proyectos/{id_proyecto}`
  - `PATCH /api/proyectos/{id_proyecto}`
- **Roles:** Lectura (`admin`, `operador`, `visualizador`, `geografo`); Escritura (`admin`).
- **Response Structure (`GET /api/proyectos/{id_proyecto}`):**
  ```json
  {
    "id_proyecto": 1,
    "clave_proyecto": "TREN-MAYA-T1",
    "nombre_proyecto": "Tren Maya Tramo 1",
    "descripcion": "Tramo Palenque - Escárcega",
    "activo": true,
    "creado_en": "2026-09-01T10:00:00Z"
  }
  ```

---

### Flujo 4: Selección y Navegación Proyecto → Núcleo Agrario (`ProyectoNucleo`)
- **Pantalla / Vista:** Directorio de Núcleos del Proyecto / Selección Operativa
- **Endpoints:**
  - `GET /api/proyectos/{id_proyecto}/nucleos`
  - `POST /api/proyectos/{id_proyecto}/nucleos`
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}`
  - `PATCH /api/proyecto-nucleo/{id_proyecto_nucleo}`
- **Roles:** Lectura (`READ_ROLES`), Creación/Edición (`admin`, `operador`).
- **Request Body (`POST /api/proyectos/{id_proyecto}/nucleos`):**
  ```json
  {
    "id_nucleo": 12,
    "id_residencia": 6,
    "tipo_intervencion": "liberacion_derecho_via",
    "estatus_operativo": "en_proceso"
  }
  ```
- **Response Structure (`GET /api/proyecto-nucleo/{id_proyecto_nucleo}`):**
  ```json
  {
    "id_proyecto_nucleo": 14,
    "id_proyecto": 1,
    "id_nucleo": 12,
    "id_residencia": 6,
    "tipo_intervencion": "liberacion_derecho_via",
    "estatus_operativo": "en_proceso",
    "activo": true,
    "nucleo": {
      "id_nucleo": 12,
      "nombre_nucleo": "SAN JOSE DE LOS ENCINOS",
      "id_municipio": 15,
      "id_tipo_tenencia": 1,
      "clave_inegi": "220140001"
    }
  }
  ```

---

### Flujo 5: Expediente y Ficha General de Proyecto-Núcleo
- **Pantalla / Vista:** Ficha del Núcleo / Referencias Documentales de Entrada
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/referencias`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/referencias`
  - `PATCH /api/referencias/{id_referencia}`
- **Request Body (`POST .../referencias`):**
  ```json
  {
    "tipo_referencia": "oficio_peticion",
    "numero_referencia": "SEGOB/DGAOPR/2026/045",
    "fecha_referencia": "2026-02-15",
    "descripcion": "Solicitud de intervención para liberación de predios"
  }
  ```

---

### Flujo 6: Responsables Operativos (`ProyectoNucleoResponsable`)
- **Pantalla / Vista:** Equipo de Trabajo Asignado al Núcleo (1:N)
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/responsables`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/responsables`
  - `PATCH /api/responsables/{id_responsable}`
- **Request Body (`POST .../responsables`):**
  ```json
  {
    "rol_desempenado": "enlace_operativo",
    "nombre": "María Luisa",
    "primer_apellido": "Santos",
    "segundo_apellido": "Vega",
    "cargo": "Visitador Agrario",
    "telefono": "4421234567",
    "correo_electronico": "maria.santos@pa.gob.mx",
    "fecha_inicio": "2026-01-15",
    "fecha_fin": null
  }
  ```

---

### Flujo 7: Órgano de Representación y Vigilancia (ORV)
- **Pantalla / Vista:** Comisariado y Consejo de Vigilancia
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/orv`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/orv`
  - `PATCH /api/orv/{id_orv}`
- **Request Body (`POST .../orv`):**
  ```json
  {
    "numero_orv": "ORV-2026-001",
    "inicio_vigencia": "2026-01-01",
    "fin_vigencia": "2029-01-01",
    "id_estado_registral": 30,
    "fecha_inscripcion_ran": "2026-02-01",
    "folio_inscripcion_ran": "RAN-QRO-2026-9988"
  }
  ```

---

### Flujo 8: Integrantes del ORV y Personas
- **Pantalla / Vista:** Mesa Directiva del Ejido / Padrón de Integrantes
- **Endpoints:**
  - `POST /api/proyectos/{id_proyecto}/personas` (Crear persona)
  - `GET /api/orv/{id_orv}/integrantes`
  - `POST /api/orv/{id_orv}/integrantes`
  - `PATCH /api/orv-integrantes/{id_orv_integrante}`
- **Request Body (`POST .../integrantes`):**
  ```json
  {
    "id_persona": 105,
    "id_organo": 32,
    "id_cargo": 34,
    "id_calidad": 39,
    "activo": true
  }
  ```

---

### Flujo 9: Padrón e Historial Agrario
- **Pantalla / Vista:** Padrón Histórico de Sujetos de Derecho
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/padrones`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/padrones`
  - `PATCH /api/padrones/{id_padron}`
- **Request Body (`POST .../padrones`):**
  ```json
  {
    "tipo_padron": "ejidatarios_vigentes",
    "total_sujetos": 120,
    "total_hombres": 80,
    "total_mujeres": 40,
    "fecha_corte": "2026-01-01",
    "fuente_padron": "RAN Delegación Querétaro"
  }
  ```

---

### Flujo 10: Parcelas Catastrales y Geometría PostGIS
- **Pantalla / Vista:** Mapeo de Parcelas Catastrales del Núcleo
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/parcelas`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/parcelas`
  - `GET /api/parcelas/{id_parcela}`
  - `PATCH /api/parcelas/{id_parcela}`
  - `PATCH /api/parcelas/{id_parcela}/geometria` (WKT / GeoJSON)
- **Request Body (`POST .../parcelas`):**
  ```json
  {
    "numero_parcela": "125",
    "superficie_documental_m2": "15420.50",
    "id_tipo_tierra": 79,
    "origen_informacion": "cartografia_ran"
  }
  ```

---

### Flujo 11: Unidades Agrarias Normalizadas y Titulares
- **Pantalla / Vista:** Módulo de Unidades Agrarias (Tierras de Uso Común, Parcelas Individuales, etc.)
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/unidades-agrarias`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/unidades-agrarias`
  - `GET /api/unidades-agrarias/{id_unidad_agraria}`
  - `PATCH /api/unidades-agrarias/{id_unidad_agraria}`
  - `GET /api/unidades-agrarias/{id_unidad_agraria}/titulares`
  - `POST /api/unidades-agrarias/{id_unidad_agraria}/titulares`
  - `PATCH /api/unidad-agraria-titulares/{id_unidad_titular}`
  - `DELETE /api/unidad-agraria-titulares/{id_unidad_titular}`
- **Request Body (`POST .../unidades-agrarias`):**
  ```json
  {
    "id_tipo_tierra": 78,
    "id_tipo_gestion": 8,
    "id_destino_superficie": 13,
    "id_tipo_titularidad": 83,
    "referencia_alfanumerica": "TUC-ZONA-NORTE",
    "id_parcela": null,
    "detalle": "Superficie de uso común colindante con derecho de vía",
    "fuente": "Padrón RAN 2026",
    "requiere_revision": false
  }
  ```
- **Response Structure:**
  ```json
  {
    "id_unidad_agraria": 45,
    "id_nucleo": 12,
    "referencia_normalizada": "TUC-ZONA-NORTE",
    "id_tipo_tierra": 78,
    "id_tipo_gestion": 8,
    "id_destino_superficie": 13,
    "id_tipo_titularidad": 83,
    "titulares": []
  }
  ```

---

### Flujo 12: Afectaciones y Relación N:M con Unidades Agrarias
- **Pantalla / Vista:** Expediente de Afectaciones (Polígonos Afectados)
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/afectaciones`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/afectaciones`
  - `GET /api/afectaciones/{id_afectacion}`
  - `PATCH /api/afectaciones/{id_afectacion}`
  - `GET /api/afectaciones/{id_afectacion}/unidades-agrarias`
  - `POST /api/afectaciones/{id_afectacion}/unidades-agrarias` (Vincular UA)
  - `PATCH /api/afectacion-unidades-agrarias/{id_afectacion_unidad}`
  - `DELETE /api/afectacion-unidades-agrarias/{id_afectacion_unidad}`
- **Request Body (`POST .../afectaciones`):**
  ```json
  {
    "tipo_afectacion": "colectivo",
    "superficie_preliminar_ha": "5.450000",
    "superficie_afectada_ha": "5.320000",
    "estatus_afectacion": "en_negociacion",
    "cadena_inicio": "KM 12+500",
    "cadena_fin": "KM 13+800"
  }
  ```
- **Request Body (`POST .../unidades-agrarias` de una afectación):**
  ```json
  {
    "id_unidad_agraria": 45,
    "superficie_preliminar_ha": "5.450000",
    "superficie_afectada_ha": "5.320000"
  }
  ```

---

### Flujo 13: Actividades de Campo y Seguimiento
- **Pantalla / Vista:** Bitácora de Visitas y Trabajos de Campo
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/actividades`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/actividades`
  - `PATCH /api/actividades/{id_actividad}`
- **Request Body (`POST .../actividades`):**
  ```json
  {
    "tipo_actividad": "recorrido_campo",
    "fecha_programada": "2026-09-15",
    "fecha_realizada": "2026-09-15",
    "estatus": "realizada",
    "descripcion": "Levantamiento topográfico complementario",
    "resultado": "Se acordó con ejidatarios la delimitación de mojones"
  }
  ```

---

### Flujo 14: Asambleas Agrarias
- **Pantalla / Vista:** Gestión de Asambleas Generales
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/asambleas`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/asambleas`
  - `GET /api/asambleas/{id_asamblea}`
  - `PATCH /api/asambleas/{id_asamblea}`
- **Request Body (`POST .../asambleas`):**
  ```json
  {
    "id_tipo_asamblea": 41,
    "id_contexto_asamblea": 44,
    "estatus": "programada",
    "observaciones": "Asamblea de anuencia previa"
  }
  ```

---

### Flujo 15: Convocatorias de Asambleas
- **Pantalla / Vista:** Control de Convocatorias (1ra, 2da convocatoria)
- **Endpoints:**
  - `GET /api/asambleas/{id_asamblea}/convocatorias`
  - `POST /api/asambleas/{id_asamblea}/convocatorias`
  - `PATCH /api/asamblea-convocatorias/{id_asamblea_convocatoria}`
- **Regla de Negocio:** La fecha de celebración de la asamblea y su quórum se derivan de la convocatoria que registre `fecha_realizacion`.
- **Request Body (`POST .../convocatorias`):**
  ```json
  {
    "ordinal": 1,
    "fecha_programada": "2026-09-10",
    "fecha_publicacion": "2026-09-01",
    "fecha_realizacion": "2026-09-10",
    "id_resultado_convocatoria": 10,
    "quorum_porcentaje": "75.50",
    "observaciones": "Quórum legal cubierto en primera convocatoria"
  }
  ```

---

### Flujo 16: Convenios de Ocupación Previa (COP) e Instrumentos Jurídicos
- **Pantalla / Vista:** Módulo de Convenios y Contratos
- **Endpoints:**
  - `GET /api/afectaciones/{id_afectacion}/convenios`
  - `POST /api/afectaciones/{id_afectacion}/convenios`
  - `GET /api/convenios/{id_convenio}`
  - `PATCH /api/convenios/{id_convenio}`
  - `POST /api/convenios/{id_convenio}/afectaciones` (Asociar afectaciones adicionales N:M)
  - `DELETE /api/convenio-afectaciones/{id_convenio_afectacion}`
- **Request Body (`POST .../convenios`):**
  ```json
  {
    "tipo_instrumento": "convenio",
    "tipo_convenio": "cop_original",
    "modalidad_especial": null,
    "consecutivo": 1,
    "id_asamblea_autorizacion": 6,
    "fecha_programada_firma": "2026-09-20",
    "fecha_firma": "2026-09-20",
    "superficie_ha": "5.320000",
    "monto_100": "1850000.00",
    "monto_90": "1665000.00",
    "monto_bdt": "185000.00"
  }
  ```

---

### Flujo 17: Comparecientes en Convenios
- **Pantalla / Vista:** Sujetos Firmantes del Convenio
- **Endpoints:**
  - `GET /api/convenios/{id_convenio}/comparecientes`
  - `POST /api/convenios/{id_convenio}/comparecientes`
  - `PATCH /api/convenio-comparecientes/{id_convenio_compareciente}`
  - `DELETE /api/convenio-comparecientes/{id_convenio_compareciente}`
- **Request Body (`POST .../comparecientes`):**
  ```json
  {
    "id_persona": 105,
    "id_calidad_compareciente": 1,
    "proporcion_participacion": "1.0000",
    "monto_individual": "1850000.00",
    "observaciones": "Firma en su calidad de titular"
  }
  ```

---

### Flujo 18: Trámites RAN (Asamblea, Convenio, ORV)
- **Pantalla / Vista:** Trámites de Registro Agrario Nacional
- **Endpoints:**
  - `GET /api/tramites-ran` (Filtros: `id_proyecto_nucleo`, `id_asamblea`, `id_convenio`, `id_orv`)
  - `POST /api/tramites-ran`
  - `GET /api/tramites-ran/{id_tramite_ran}`
  - `PATCH /api/tramites-ran/{id_tramite_ran}`
- **Request Body (`POST /api/tramites-ran`):**
  ```json
  {
    "id_asamblea": 6,
    "id_convenio": null,
    "id_orv": null,
    "numero_tramite": "RAN-REG-2026-004",
    "fecha_programada_ingreso": "2026-09-25",
    "estatus": "ingresado"
  }
  ```

---

### Flujo 19: Bitácora de Eventos y Oficios RAN
- **Pantalla / Vista:** Historial de Seguimiento / Oficios y Calificaciones RAN
- **Endpoints:**
  - `GET /api/tramites-ran/{id_tramite_ran}/eventos`
  - `POST /api/tramites-ran/{id_tramite_ran}/eventos`
  - `PATCH /api/tramite-ran-eventos/{id_tramite_ran_evento}`
- **Request Body (`POST .../eventos`):**
  ```json
  {
    "ordinal": 1,
    "id_tipo_evento": 55,
    "fecha_evento": "2026-09-25",
    "numero_oficio": "RAN/DEL/2026/102",
    "descripcion": "Ingreso formal de acta de asamblea de anuencia",
    "fecha_acuse": "2026-09-25"
  }
  ```

---

### Flujo 20: Trámites FIFONAFE
- **Pantalla / Vista:** Gestión de Fondos FIFONAFE (Tierras de Uso Común / Particulares)
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe`
  - `GET /api/fifonafe/{id_tramite_fifonafe}`
  - `PATCH /api/fifonafe/{id_tramite_fifonafe}`
- **Request Body (`POST .../fifonafe`):**
  ```json
  {
    "ids_afectacion": [12],
    "estatus": "pendiente",
    "acuse_fifonafe_fecha": "2026-09-15",
    "hay_conflictos": false,
    "resultado_no_conflictos": "Sin conflicto social ni litigio agrario"
  }
  ```

---

### Flujo 21: Bitácora de Eventos y Oficios FIFONAFE
- **Pantalla / Vista:** Flujo de Oficios FIFONAFE / DGAOPR / Representación
- **Endpoints:**
  - `GET /api/fifonafe/{id_tramite_fifonafe}/eventos`
  - `POST /api/fifonafe/{id_tramite_fifonafe}/eventos`
  - `PATCH /api/fifonafe-eventos/{id_tramite_fifonafe_evento}`
- **Request Body (`POST .../eventos`):**
  ```json
  {
    "ordinal": 1,
    "id_tipo_evento": 63,
    "numero_oficio": "FIFONAFE/DEP/2026/088",
    "fecha_oficio": "2026-09-18",
    "asunto": "Notificación de suficiencia de fondos para depósito",
    "fecha_acuse": "2026-09-19"
  }
  ```

---

### Flujo 22: Indemnizaciones
- **Pantalla / Vista:** Expediente Económico / Indemnización por Afectación
- **Endpoints:**
  - `GET /api/afectaciones/{id_afectacion}/indemnizacion`
  - `POST /api/afectaciones/{id_afectacion}/indemnizacion`
  - `PATCH /api/indemnizaciones/{id_indemnizacion}`
- **Request Body (`POST .../indemnizacion`):**
  ```json
  {
    "estatus": "programado",
    "fecha_programada": "2026-10-15",
    "fecha_resolucion": "2026-09-30",
    "fecha_entrega_expediente_pa": "2026-09-28"
  }
  ```

---

### Flujo 23: Pagos y Finiquitos
- **Pantalla / Vista:** Registro de Dispersiones y Pagos Realizados
- **Endpoints:**
  - `GET /api/indemnizaciones/{id_indemnizacion}/pagos`
  - `POST /api/indemnizaciones/{id_indemnizacion}/pagos`
  - `PATCH /api/pagos/{id_pago}`
- **Request Body (`POST .../pagos`):**
  ```json
  {
    "fecha_pago": "2026-10-15",
    "monto": "1850000.00",
    "beneficiario_nombre": "Ejido San José de los Encinos",
    "id_persona_beneficiaria": null,
    "medio_pago": "transferencia",
    "referencia": "SPEI-BBVA-998822"
  }
  ```

---

### Flujo 24: Bóveda Documental
- **Pantalla / Vista:** Gestor de Archivos, Versiones e Inmutabilidad de Documentos
- **Endpoints:**
  - `GET /api/documentos/objetivos/{entidad_tipo}/{entidad_id}`
  - `POST /api/documentos/objetivos/{entidad_tipo}/{entidad_id}`
  - `PATCH /api/documentos/{id_documento}`
  - `POST /api/documentos/{id_documento}/vinculos/{entidad_tipo}/{entidad_id}`
  - `DELETE /api/documentos/{id_documento}/vinculos/{entidad_tipo}/{entidad_id}`
  - `POST /api/documentos/{id_documento}/versiones` (Subir archivo binario `multipart/form-data`)
  - `GET /api/documentos/versiones/{id_version}/descarga` (Descarga directa de archivo)
- **Request Body (`POST .../objetivos/{entidad_tipo}/{entidad_id}`):**
  ```json
  {
    "tipo_documento": "acta_asamblea",
    "estado": "disponible",
    "titulo": "Acta de Asamblea de Anuencia firmada",
    "fecha_documento": "2026-09-10",
    "numero_folio": "ACTA-001/2026",
    "descripcion": "Documento escaneado a color con firmas completas"
  }
  ```

---

### Flujo 25: Checklist de Requisitos Documentales por Expediente
- **Pantalla / Vista:** Control de Requisitos del Expediente Único
- **Endpoints:**
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales`
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales`
  - `PATCH /api/requisitos-documentales/{id_expediente_requisito}`
- **Request Body (`POST .../requisitos-documentales`):**
  ```json
  {
    "id_requisito": 3,
    "id_estado_requisito": 1,
    "cumplido": true,
    "observaciones": "Acta de asamblea debidamente requisitada"
  }
  ```

---

### Flujo 26: Dashboard Ejecutivo y Métricas KPI
- **Pantalla / Vista:** Dashboard Principal de Seguimiento
- **Endpoints:**
  - `GET /api/dashboard/kpi?id_proyecto={id}&anio={anio}`
  - `GET /api/exportaciones/dashboard.csv?id_proyecto={id}`
- **Response Structure (`GET /api/dashboard/kpi`):**
  ```json
  [
    {
      "id_proyecto": 1,
      "anio": 2026,
      "indicador": "SUPERFICIE_LIBERADA_HA",
      "valor": "125.450000",
      "meta": "150.000000",
      "porcentaje_cumplimiento": 83.63
    }
  ]
  ```

---

### Flujo 27: Visor Cartográfico / Mapa Geoespacial
- **Pantalla / Vista:** Mapa Interactivo SIG (Capas de Trazo, Franjas y Parcelas)
- **Endpoints:**
  - `GET /api/proyectos/{id_proyecto}/mapa` (Resumen espacial del proyecto)
  - `GET /api/proyectos/{id_proyecto}/trazos` (Historial de trazos lineales)
  - `POST /api/proyectos/{id_proyecto}/trazos` (Registrar nuevo trazo WKT)
- **Request Body (`POST /api/proyectos/{id_proyecto}/trazos`):**
  ```json
  {
    "version": 1,
    "geometria_wkt": "MULTILINESTRING((-100.0 20.0, -100.1 20.1))",
    "fuente": "Levantamiento Topográfico DGAOPR",
    "fecha_vigencia_inicio": "2026-01-01"
  }
  ```

---

### Flujo 28: Importación Geoespacial y Geoprocesamiento Seguro
- **Pantalla / Vista:** Carga y Validación de Archivos Geoespaciales (GeoJSON)
- **Endpoints:**
  - `GET /api/proyectos/{id_proyecto}/importaciones`
  - `POST /api/proyectos/{id_proyecto}/importaciones` (Subir archivo GeoJSON)
- **Request Body (`POST .../importaciones`):** Formato `multipart/form-data` con campo `file` y parámetro `tipo_capa` (`trazo`, `franja`, `parcelas`).
- **Response Structure:**
  ```json
  {
    "id_importacion": 12,
    "id_proyecto": 1,
    "nombre_archivo": "trazo_km_10_20.geojson",
    "estatus": "procesado",
    "total_features": 1,
    "features_validos": 1,
    "features_con_error": 0,
    "errores": []
  }
  ```

---

### Flujo 29: Catálogos para Formularios y Selectores
- **Pantalla / Vista:** Todos los componentes Select / Combobox / Radio
- **Endpoints:**
  - `GET /api/catalogos/entidades`
  - `GET /api/catalogos/municipios?id_entidad={id}`
  - `GET /api/catalogos/operativos/{tipo_catalogo}`
  - `GET /api/catalogos/requisitos-documentales`
- **Response Structure (`GET /api/catalogos/operativos/tipo_tenencia`):**
  ```json
  [
    {
      "id_catalogo_opcion": 1,
      "tipo_catalogo": "tipo_tenencia",
      "codigo": "ejido",
      "nombre": "Ejido",
      "orden": 1,
      "activo": true
    },
    {
      "id_catalogo_opcion": 2,
      "tipo_catalogo": "tipo_tenencia",
      "codigo": "comunidad",
      "nombre": "Comunidad",
      "orden": 2,
      "activo": true
    }
  ]
  ```

---

## 4. Resumen de Modelos Canónicos y Reglas de Integridad

1. **Jerarquía Territorial y de Proyecto:**
   - Todo trabajo se agrupa en `ProyectoNucleo` (vínculo entre `Proyecto` y `NucleoAgrario`).
   - Los responsables son 1:N sobre `ProyectoNucleoResponsable`.
2. **Unidades Agrarias y Afectaciones:**
   - Las parcelas catastrales y tierras comunales se registran como `UnidadAgraria`.
   - Las afectaciones se asocian a una o más unidades agrarias a través de `AfectacionUnidadAgraria` (N:M).
   - Ya **no existe** el concepto ni la tabla de `bien_afectado` / `BienAfectado`.
3. **Asambleas y Trámites:**
   - La fecha de asamblea celebrada se obtiene de su convocatoria con `fecha_realizacion`.
   - Los trámites RAN y FIFONAFE gestionan sus oficios y estados mediante sus tablas de eventos 1:N (`TramiteRanEvento`, `TramiteFifonafeEvento`).
4. **Validación Estricta de Campos:**
   - Todos los esquemas de entrada usan `extra='forbid'`. Enviar campos no reconocidos producirá un error `422 Unprocessable Entity`.
# Cierre Excel V1

Las marcas `X` de las hojas auditadas son auxiliares de conteo: no son campos de API ni columnas operativas. El dashboard deduplica sensibilización y caminamiento por `id_proyecto_nucleo + id_tipo_cop_operativo`, y RAN por trámite. `ActividadCampo` y `Asamblea` aceptan `id_tipo_cop_operativo` nullable; los códigos reportables son `ORIGEN`, `ADICIONAL`, `2A_ADICIONAL`, `COMPLEMENTARIAS` y `TRANSVERSALES`. Las parcelas conservan exclusivamente `no_parcela`.

`ActividadCampo` conserva cada evento real (`tipo_actividad`, `fecha_programada`, `fecha_realizada`, `responsable`, `resultado`, observaciones) y admite varios eventos de un mismo núcleo/ciclo. El KPI cuenta una sola vez cada combinación núcleo/ciclo que tenga el hito correspondiente. `Asamblea` es una entidad independiente: su arreglo `convocatorias` conserva todas las convocatorias, y el KPI cuenta asambleas, no núcleos ni convocatorias.

Un trámite RAN se crea con exactamente uno de `id_asamblea`, `id_convenio` o `id_orv`, `fecha_programada_ingreso`, `referencia_expediente` y el arreglo `eventos`. Cada evento conserva `id_tipo_evento`, `fecha_evento`, `numero_solicitud`, `resultado`, `calificacion`, `folio_referencia` e `id_documento`. Por tanto, ingreso, prevención, reingreso, calificación e inscripción son eventos distintos; ingreso y reingreso juntos siguen contando un solo trámite ingresado en KPI.

`Indemnizacion.estatus` admite `pendiente`, `programado`, `en_proceso`, `completo`, `pagado`, `cancelado` y `otro`. `pagado` no inventa un pago: los datos monetarios y fecha sólo se capturan como registros reales `Pago`. Los requisitos documentales pueden apuntar, además de los objetivos previos, a `orv`, `padron_historial`, `actividad_campo`, `asamblea` y `asamblea_convocatoria`.

`NO. DE PARCELA` y `NO. DE PARCELA PPT` se normalizan al único campo `parcela.no_parcela`; no hay `no_parcela_ppt`. FIFONAFE conserva eventos: el flujo colectivo completo requiere sus cuatro oficios colectivos, mientras que un trámite individual válido no queda sujeto artificialmente a ese conjunto.
