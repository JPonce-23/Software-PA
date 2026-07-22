# DICCIONARIO DE DATOS - SISTEMA SSALFER
**Base de Datos Actual en Producción (Esquema 001_init_schema.sql)**

Este documento modela la estructura de la base de datos actual del proyecto. Cada tabla incluye sus campos obligatorios (NN = Not Null), llaves primarias (PK) y foráneas (FK), así como las relaciones operativas.

---

## 1. PRINCIPIOS DE DISEÑO Y REGLAS DE NEGOCIO EN EL MOTOR

Antes de detallar las tablas, es crucial entender por qué el sistema SSALFER está diseñado con una fuerte carga lógica a nivel del motor de base de datos (PostgreSQL) en lugar de delegar todo al código del backend o frontend:

1. **Uso Estratégico de PostGIS:**
   La liberación de vía es un problema intrínsecamente territorial. Al utilizar los tipos de datos geométricos de PostGIS (`GEOMETRY`), la base de datos no solo guarda coordenadas, sino que comprende el espacio físico. Esto nos permite usar funciones nativas (como `ST_Intersects`) para validar matemáticamente, al momento de guardar, que una parcela afectada realmente cruce por la ruta del tren, eliminando errores humanos de captura y protegiendo al estado de pagar indemnizaciones en zonas equivocadas.

2. **Seguridad Jurídica y Triggers Ineludibles:**
   En el derecho agrario, un error de captura puede derivar en un conflicto social o una auditoría federal. Al programar las reglas de negocio en *Triggers* (Disparadores) y *Funciones* dentro de la base de datos, garantizamos una protección "ineludible". Si un operador intenta (incluso por error desde un script o una API externa) registrar un convenio colectivo sin que exista una asamblea válida, el propio motor de la base de datos abortará la transacción. La integridad de los datos no depende de la aplicación cliente, sino del núcleo de los datos mismos.

3. **Auditoría Forense Nativa:**
   Dado el manejo de recursos públicos, el sistema emplea una arquitectura donde no existen los borrados físicos (`DELETE` bloqueado). Toda tabla cuenta con campos de baja lógica (`activo`, `fecha_baja`, `motivo_baja`) y un trigger maestro que captura silenciosamente cualquier cambio (INSERT, UPDATE, DELETE lógico) guardando una fotografía exacta en formato JSONB (`OLD` y `NEW`), asegurando una trazabilidad perfecta de qué usuario modificó qué dato y cuándo.

4. **Modelado Fiel del Proceso Agrario:**
   El modelo separa claramente la ruta de "Derechos Colectivos" (Uso Común) de los "Derechos Individuales" (Parcelas). Esto refleja la realidad de la Ley Agraria, donde los convenios de uso común requieren obligatoriamente el quórum y anuencia de una asamblea, mientras que los parcelarios son negociaciones directas con el titular registral.

---

## 2. ESTRUCTURA DE TABLAS (ETAPAS)

### ETAPA 1 - GEOESPACIAL Y ESTRUCTURA BASE

### Tabla 1: `entidad_federativa` - Estados de la República
**Justificación Operativa:** Necesaria para clasificar territorialmente a nivel macro y estandarizar datos con INEGI (INEGI ID) para futuros cruces de información federal.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_entidad | SERIAL | ✔ | | ✔ | Identificador único. |
| clave_inegi | CHAR(2) | | | ✔ | Clave oficial INEGI (UNIQUE). Permite homologar con catálogos de SEDATU y RAN. |
| nombre | VARCHAR(100) | | | ✔ | Nombre oficial del estado. |
| activo | BOOLEAN | | | ✔ | Baja lógica estándar. |

### Tabla 2: `municipio` - Municipios registrales
**Cardinalidad:** Entidad 1 ------ N Municipio
**Justificación Operativa:** El Registro Agrario Nacional (RAN) cataloga a los núcleos agrarios por su municipio. Es indispensable para generar los oficios legales que exige la normativa agraria para la inscripción de convenios.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_municipio | SERIAL | ✔ | | ✔ | Identificador único. |
| id_entidad | INTEGER | | ✔ | ✔ | Entidad a la que pertenece. |
| clave_inegi | CHAR(5) | | | ✔ | Clave INEGI (UNIQUE). Clave geoestadística federal. |
| nombre | VARCHAR(150) | | | ✔ | Nombre del municipio. |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

### Tabla 3: `tramo` - Tramos ferroviarios
**Justificación Operativa:** Representa las grandes divisiones logísticas y presupuestales de la megaobra (ej. Tramo 1, Tramo 2). Es el contenedor principal para agrupar metas de liberación, presupuestos y reportes de alto nivel.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_tramo | SERIAL | ✔ | | ✔ | Identificador único. |
| clave_tramo | VARCHAR(20) | | | ✔ | Clave interna (UNIQUE). Usada para nomenclatura de expedientes físicos. |
| nombre_tramo | VARCHAR(200) | | | ✔ | Nombre descriptivo (ej. "Palenque - Escárcega"). |
| ancho_total_derecho_via_m | NUMERIC(6,2) | | | | Ancho fijo del DDV. *(Nota: Se planea depreciar para usar polígonos reales).* |
| geometria_linea | GEOMETRY | | | | Línea central (SRID 4326). Eje troncal de validación espacial. |
| activo | BOOLEAN | | | ✔ | Baja lógica estándar. |

### Tabla 4: `frente` - Subdivisión operativa de un tramo
**Cardinalidad:** Tramo 1 ------ N Frente
**Justificación Operativa:** Permite subdividir un tramo gigante (cientos de km) en zonas controlables ("Frentes de Obra"). Es crucial para el control de acceso, asignando brigadas de topógrafos y abogados a zonas geográficas específicas.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_frente | SERIAL | ✔ | | ✔ | Identificador único. |
| id_tramo | INTEGER | | ✔ | ✔ | Tramo padre al que pertenece operativamente. |
| clave_frente | VARCHAR(30) | | | ✔ | Clave interna para identificación en oficios y minutas. |
| nombre_frente | VARCHAR(200) | | | ✔ | Nombre operativo asignado por el equipo constructor. |
| geometria_linea | GEOMETRY | | | | Geometría opcional para limitar el área de responsabilidad del frente. |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

### Tabla 5: `nucleo_agrario` - Ejidos y Comunidades
**Cardinalidad:** Municipio 1 ------ N Núcleo
**Justificación Operativa:** Es la entidad jurídica propietaria de la tierra social en México. Representa a la comunidad como persona moral; sin ella, es legalmente imposible generar asambleas, convenios y expedientes registrales ante el RAN.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_nucleo | SERIAL | ✔ | | ✔ | Identificador único. |
| id_municipio | INTEGER | | ✔ | ✔ | Municipio registral donde tributa y se registra el núcleo. |
| nombre_nucleo | VARCHAR(300) | | | ✔ | Nombre registral exacto (debe coincidir con la carpeta básica del RAN). |
| tipo_nucleo | VARCHAR(20) | | | ✔ | 'ejido' o 'comunidad'. Define la naturaleza de sus órganos de representación. |
| comunidad_indigena | BOOLEAN | | | ✔ | Condiciona la necesidad de consultas previas, libres e informadas (requisito OIT). |
| geometria_poligono | GEOMETRY | | | | Polígono territorial. Límite exacto de la propiedad del núcleo (SRID 4326). |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

### Tabla 6: `tramo_nucleo` - Intersección de Tramo y Núcleo (Pivote Operativo)
**Cardinalidad:** Tramo 1 ------ N Tramo_Nucleo | Nucleo 1 ------ N Tramo_Nucleo
**Justificación Operativa:** Es el corazón operativo del sistema. Resuelve la relación Muchos-a-Muchos entre la obra y la tierra. Cada registro aquí representa un "Expediente de Liberación" único, donde convergen las negociaciones y el control de avance.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_tramo_nucleo | SERIAL | ✔ | | ✔ | Identificador único del expediente maestro. |
| id_tramo | INTEGER | | ✔ | ✔ | Tramo que causa la afectación. |
| id_frente | INTEGER | | ✔ | ✔ | Frente responsable de la gestión y negociación en campo. |
| id_nucleo | INTEGER | | ✔ | ✔ | Núcleo agrario afectado que deberá otorgar anuencia. |
| consecutivo | INTEGER | | | ✔ | Número de control interno generado automáticamente para la PA. |
| geometria_segmento | GEOMETRY | | | | El pedazo exacto de la vía férrea que queda "atrapado" dentro de este núcleo. |
| es_expropiacion | BOOLEAN | | | ✔ | Bandera legal. Si es true, omite la vía amigable (COP) por decreto presidencial. |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

---

## ETAPA 2 - DERECHOS Y AFECTACIONES

### Tabla 7: `padron_historial` - Censo de sujetos agrarios colectivos
**Cardinalidad:** Núcleo 1 ------ N Padrón
**Justificación Operativa:** El padrón agrario es dinámico (personas mueren o ceden derechos). El sistema registra la "fotografía" del padrón en una fecha específica para poder calcular legalmente el quórum requerido (50%+1) el día de una asamblea.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_padron | SERIAL | ✔ | | ✔ | Identificador único. |
| id_nucleo | INTEGER | | ✔ | ✔ | Núcleo al que pertenece el censo. |
| fecha_padron | DATE | | | ✔ | Fecha de corte del censo expedido por el RAN. |
| numero_ejidatarios_comuneros | INTEGER | | | ✔ | Cantidad total oficial. Base matemática para el cálculo de quórum de asambleas. |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

### Tabla 8: `parcela` - Derechos individuales
**Cardinalidad:** Núcleo 1 ------ N Parcela
**Justificación Operativa:** Modela la tierra fragmentada y asignada de forma individual (parcelada). Es fundamental cruzar esta entidad con el RAN mediante los números de certificados parcelarios para garantizar que se pague al titular legítimo.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_parcela | SERIAL | ✔ | | ✔ | Identificador único. |
| id_nucleo | INTEGER | | ✔ | ✔ | Núcleo donde físicamente reside la parcela. |
| nombre_titular | VARCHAR(300) | | | | Propietario de los derechos (Sujeto Agrario). |
| no_parcela_ppt | VARCHAR(50) | | | | Número asignado en el Plano Interno (Procede). |
| certificado_parcelario | VARCHAR(100) | | | | Identificador registral que acredita la titularidad ante la ley. |
| folio_derechos | VARCHAR(100) | | | | Identificador del Registro Agrario Nacional (RAN). |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

### Tabla 9: `afectacion` - Polígonos de impacto del proyecto
**Cardinalidad:** Tramo_Nucleo 1 ------ N Afectación
**Justificación Operativa:** Representa la huella física exacta que el tren consumirá. Su registro detona todo el proceso legal y financiero posterior. Puede ser de naturaleza colectiva (Uso Común) o individual (Parcela).

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_afectacion | SERIAL | ✔ | | ✔ | Identificador único. |
| id_nucleo | INTEGER | | ✔ | ✔ | FK de seguridad para evitar cruces de datos entre expedientes de distintos núcleos. |
| id_tramo_nucleo | INTEGER | | ✔ | ✔ | Expediente pivote al que pertenece la afectación. |
| id_parcela | INTEGER | | ✔ | | Si es afectación individual, exige este vínculo. Si es colectivo, debe ser NULL. |
| tipo_afectacion | VARCHAR(20) | | | ✔ | 'colectivo' o 'individual'. Define qué reglas de negocio (triggers) se le aplican. |
| superficie_afectada_ha | NUMERIC(12,4) | | | | Hectáreas calculadas matemáticamente a partir del polígono de afectación. |
| geometria_afectacion | GEOMETRY | | | | Polígono georreferenciado del impacto. |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

---

## ETAPA 3 - GESTIÓN SOCIAL Y JURÍDICA

### Tabla 10: `orv` - Órgano de Representación y Vigilancia
**Cardinalidad:** Núcleo 1 ------ N ORV
**Justificación Operativa:** Almacena a la "Mesa Directiva" del núcleo (Comisariado). La Ley Agraria dicta que su mandato dura 3 años. Si el sistema detecta que la vigencia está caducada, cualquier firma plasmada por ellos carece de validez federal.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_orv | SERIAL | ✔ | | ✔ | Identificador único. |
| id_nucleo | INTEGER | | ✔ | ✔ | Núcleo que representan. |
| inicio_vigencia | DATE | | | ✔ | Fecha de la elección. |
| fin_vigencia | DATE | | | ✔ | Fecha de vencimiento. Crítica para validaciones legales. |
| comisariado_presidente | VARCHAR(300) | | | | Nombre del representante legal principal. |
| activo | BOOLEAN | | | ✔ | Baja lógica. |

### Tabla 11: `asamblea` - Actos de anuencia colectiva
**Cardinalidad:** Tramo_Nucleo 1 ------ N Asamblea
**Justificación Operativa:** Evento legal supremo donde la comunidad (máxima autoridad del núcleo) vota. Sin un registro de asamblea con estatus "Anuencia Otorgada", es un delito federal firmar un convenio de expropiación colectiva.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_asamblea | SERIAL | ✔ | | ✔ | Identificador único. |
| id_tramo_nucleo | INTEGER | | ✔ | ✔ | Expediente sobre el que versa la asamblea. |
| tipo_asamblea | VARCHAR(50) | | | ✔ | Puede ser 'informacion', 'anuencia', etc. |
| fecha_realizada | DATE | | | | Cuándo ocurrió el acto formal en la casa ejidal. |
| resultado_anuencia | VARCHAR(30) | | | ✔ | 'otorgada', 'negada', 'pendiente'. Define el bloqueo/desbloqueo de los convenios. |
| ingreso_ran_fecha | DATE | | | | Fecha de inicio del trámite registral para dar fe pública. |
| acta_inscripcion_fecha_ran | DATE | | | | Fecha en que el RAN validó y formalizó la asamblea legalmente. |

### Tabla 12: `convenio` - Contratos de Ocupación Previa (COP)
**Cardinalidad:** Afectacion 1 ------ N Convenio
**Justificación Operativa:** Es el contrato jurídico y financiero. Vincula legalmente una superficie afectada con una contraprestación (monto a pagar). Constituye el entregable final del proceso operativo de la Procuraduría Agraria.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_convenio | SERIAL | ✔ | | ✔ | Identificador único. |
| id_afectacion | INTEGER | | ✔ | ✔ | Polígono de tierra que se está comprometiendo en este contrato. |
| id_asamblea_autorizacion | INTEGER | | ✔ | | Obligatorio en afectaciones colectivas (respaldo legal). NULL en individuales. |
| tipo_convenio | VARCHAR(50) | | | ✔ | Puede ser 'cop_original', 'modificatorio' (cuando se altera la superficie pagada). |
| fecha_firma | DATE | | | | Formalización del acuerdo entre partes. |
| monto_100 | NUMERIC(18,2) | | | | Indemnización total acordada según tabuladores del INDAABIN. |
| superficie_total_ha | NUMERIC(12,4) | | | | Superficie exacta que se está liquidando en este convenio. |
| convenio_inscrito_fecha_ran | DATE | | | | Cierre del ciclo jurídico: El estado es dueño legal y se procede al pago final. |

---

## ETAPA 4 - SOPORTE Y SEGUIMIENTO

### Tabla 13: `tramite_fifonafe` - Pagos e Indemnizaciones
**Cardinalidad:** Convenio 1 ------ 1 Tramite
**Justificación Operativa:** La Procuraduría Agraria no emite los cheques, sino que gestiona el expediente ante el Fideicomiso (FIFONAFE). Esta tabla rastrea los oficios interinstitucionales para garantizar la liberación de los fondos al ejidatario.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_tramite_fifonafe | SERIAL | ✔ | | ✔ | Identificador único. |
| id_tramo_nucleo | INTEGER | | ✔ | ✔ | Expediente general del núcleo. |
| tipo_tramite | VARCHAR(50) | | | ✔ | Tipo de gestión: 'indemnizacion', 'informe_no_conflictos'. |
| estatus | VARCHAR(30) | | | ✔ | 'pendiente', 'completo'. |
| no_oficio_fifonafe_a_dgaopr | VARCHAR(50) | | | | Número de rastreo de correspondencia oficial interinstitucional. |

### Tabla 14: `documentacion_soporte` - Repositorio de Archivos
**Cardinalidad:** Polimórfica (Entidad 1 --- N Documentos)
**Justificación Operativa:** Todo hito en el sistema (actas de asamblea, convenios firmados, certificados parcelarios) requiere su documento fuente (PDF escaneado) para auditorías de la Función Pública.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_documento | SERIAL | ✔ | | ✔ | Identificador único. |
| entidad_relacionada_id | INTEGER | | | ✔ | ID del registro padre (puede apuntar a un Núcleo, a un COP, o a un ORV). |
| entidad_relacionada_tipo | VARCHAR(50) | | | ✔ | Define a qué tabla apunta el ID anterior (polimorfismo). |
| url_archivo | TEXT | | | | Ruta física o URI de almacenamiento en cloud/local. |
| es_critico | BOOLEAN | | | ✔ | Bandera operativa para marcar documentos indispensables para el pago. |

---

## ETAPA 5 - AUDITORÍA Y SEGURIDAD

### Tabla 15: `usuario`
**Justificación Operativa:** Control de acceso e identidad para aplicar control de acceso basado en roles (RBAC) y limitar permisos de lectura/escritura (ej. Admin vs. Geógrafo).

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_usuario | SERIAL | ✔ | | ✔ | Identificador único. |
| correo | VARCHAR(320) | | | ✔ | Credencial de acceso (UNIQUE). |
| contrasena_hash | VARCHAR(255) | | | ✔ | Hash seguro de la contraseña. |
| rol | VARCHAR(30) | | | ✔ | Perfil de permisos ('admin', 'operador', etc.). |

### Tabla 16: `bitacora` (Auditoría Forense Nativa)
**Justificación Operativa:** Requisito de fiscalización ineludible. Cada evento de inserción, actualización o borrado lógico queda inmortalizado aquí automáticamente por el motor de la base de datos, imposibilitando el borrado de huellas.

| Campo | Tipo | PK | FK | NN | Descripción y Justificación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| id_bitacora | BIGSERIAL | ✔ | | ✔ | Identificador inmutable transaccional. |
| id_usuario | INTEGER | | ✔ | ✔ | ID extraído del contexto transaccional (`app.current_user_id`). Identifica al autor del cambio. |
| entidad_tipo | VARCHAR(100) | | | ✔ | Nombre de la tabla afectada. |
| accion | VARCHAR(30) | | | ✔ | Operación ejecutada: 'insert', 'update', 'delete_attempt'. |
| valor_anterior | JSONB | | | | Fotografía completa (JSON) de la fila antes del cambio. |
| valor_nuevo | JSONB | | | | Fotografía completa (JSON) de la fila después del cambio. Permite revertir errores. |

---

## ETAPA 6 - LÓGICA DE NEGOCIO (TRIGGERS Y FUNCIONES)

### Funciones Principales

Las funciones almacenadas concentran lógicas de cálculo complejas o comportamientos repetitivos y seguros.

| Función | Tipo | Descripción y Justificación Legal |
| :---- | :---- | :---- |
| `fn_audit_log()` | TRIGGER FUNCTION | Es el corazón de la seguridad. Captura los pseudo-registros transaccionales `OLD` y `NEW`, los serializa a formato JSONB, extrae el ID del usuario de las variables de entorno de la transacción (`current_setting`) e inserta la evidencia en la `bitacora`. |
| `fn_prevent_physical_delete()` | TRIGGER FUNCTION | Dada la naturaleza auditable del proyecto (recursos federales), esta función lanza una excepción tipo "RAISE EXCEPTION" abortando en seco cualquier comando `DELETE` SQL sobre las tablas operativas. Obliga al sistema a usar la actualización del campo `activo = FALSE`. |
| `fn_validar_baja_logica()` | TRIGGER FUNCTION | Complementa la anterior. Si se detecta un `UPDATE` donde `activo` cambia a falso, la función verifica estrictamente que los campos obligatorios de baja (`fecha_baja`, `motivo_baja`, `id_usuario_baja`) no vengan vacíos. Previene "bajas fantasmas" inexplicables. |
| `fn_calcular_superficie_liberada_afectacion()` | SCALAR FUNCTION | Función utilitaria llamada por los dashboards. Totaliza automáticamente las superficies de los convenios vigentes (sin contar los cancelados) que pertenecen a una afectación, brindando el porcentaje real de avance de liberación. |

### Triggers de Integridad Operativa

Los triggers aseguran que, sin importar si el frontend, un script de backend o un técnico ejecutando SQL crudo intenta modificar datos, la ley agraria no se viole.

| Trigger | Tabla | Evento | Descripción y Justificación Legal |
| :---- | :---- | :---- | :---- |
| `trg_validar_afectacion_uso_comun` | `afectacion` | BEFORE INS/UPD | **Protección de Diseño:** Impide registrar un polígono de tipo "colectivo" si el sistema marca que el tramo está exonerado de afectar usos comunes. |
| `trg_validar_convenio_expropiacion` | `convenio` | BEFORE INS/UPD | **Protección Jurídica:** Bloquea la formalización de un Contrato de Ocupación Previa (vía amigable de pago) si el expediente entero fue declarado bajo un proceso de "Expropiación Directa" hostil. |
| `trg_validar_superficie_liberada_convenio` | `convenio` | AFTER INS/UPD | **Protección Financiera:** Calcula sumas en tiempo real para garantizar matemáticamente que la Procuraduría Agraria no prometa pagar a través de varios convenios una superficie mayor a la que físicamente se expropió. Evita peculado y pagos inflados. |
| `trg_validar_superficie_afectada_reducida` | `afectacion` | BEFORE UPDATE | **Protección Documental:** Si un topógrafo intenta corregir y hacer más pequeño el polígono de una afectación, el trigger lo bloquea si el sistema detecta que el gobierno ya pagó convenios por un área superior a la nueva corrección propuesta. |
| `trg_validar_parcela_individual` | `afectacion` | BEFORE INS/UPD | **Protección Registral:** Valida que, si la afectación se tipifica como "individual", los campos que vinculan la parcela al Registro Agrario Nacional (`nombre_titular`, identificador parcelario) vengan obligatoriamente llenos. |
| `trg_validar_modificatorio_colectivo` | `convenio` | BEFORE INS/UPD | **Protección Agraria:** Si se intenta generar un convenio que modifica el monto a pagar de un núcleo, el trigger exige que haya un registro de una Asamblea con "Anuencia Otorgada" vinculada; de lo contrario, el aumento es ilegal sin consentimiento ejidal. |
| `trg_validar_coherencia_espacial` | `afectacion` | BEFORE INS/UPD | **Validación PostGIS:** Cruza en milisegundos tres factores geográficos: Verifica que el polígono de afectación dibujado choque físicamente (`ST_Intersects`) tanto con los límites del núcleo agrario como con la franja de derecho de vía del proyecto. Si está fuera, aborta la operación. |
| `trg_validar_regresion_estado_convenio` | `convenio` | BEFORE UPDATE | **Seguridad del Proceso:** Evita manipulaciones maliciosas de estados. Por ejemplo, impide que un convenio que ya alcanzó la etapa máxima de "Inscrito en el RAN" sea retornado manualmente al estatus "Borrador" borrando sus fechas oficiales. |
