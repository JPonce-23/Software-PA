# Requirements Document

## Introduction

Este documento especifica los requerimientos para un sistema web multiusuario de seguimiento del proceso de liberación de derechos de vía de un proyecto ferroviario que afecta propiedad social (ejidos y comunidades) en México. El sistema reemplazará el seguimiento actual basado en Excel, proporcionando gestión centralizada de datos, tableros de control y capacidades de reporteo para múltiples actores.

## Glossary

- **Sistema**: La aplicación web de seguimiento que se está desarrollando
- **operador**: Usuario de captura de datos que registra información en el sistema
- **visualizador**: Usuario final/stakeholder que visualiza reportes de progreso y tableros
- **Geógrafo**: Usuario especializado con permisos para capturar y editar información geográfica/técnica de geometrías de Tramos, Frentes, Núcleos Agrarios y coordenadas geoespaciales
- **Núcleo_Agrario**: Es la entidad central del sistema que representa a cada ejido o comunidad agraria. Cuentan con personalidad jurídica y patrimonio propio.
- **Tramo**: cada una de las secciones principales que integran el proyecto ferroviario. Constituye la unidad geográfica y operativa de mayor nivel dentro del sistema, y su función principal es facilitar el seguimiento del derecho de vía.
- **Frente**: porción o subdivisión en la que se divide un tramo.
- **Afectación**: Superficie afectada - Registro que documenta la superficie, tipo de tenencia y las personas o parcelas afectadas por el paso del proyecto.
- **Convenio**: Acuerdo que facilita la ocupación de terreno para el inicio de los trabajos operativos, ya que sin él, las obras no pueden comenzar sino hasta el final de todo el proceso legal de expropiación. Los tipos de convenio varían según el tipo de derecho afectado: para derechos colectivos incluye COP, Modificatorio, Superficie Adicional y Obras Complementarias; para derechos individuales incluye COP, Modificatorio, Ampliación y Ampliación Remanente.
- **COP**: Convenio de Ocupación Previa - Es un acuerdo formal donde un núcleo agrario o titular parcelario da permiso para ocupar temporalmente sus tierras mientras se tramita el proceso de expropiación.
- **RAN**: Registro Agrario Nacional - Entidad que controla la tenencia de la tierra, resguarda la seguridad documental
 y es donde se inscriben las actas de asamblea y los Convenios de Ocupación Previa.
- **ORV**: Órganos de Representación y Vigilancia - entidades encargadas de representar, ejecutar y supervisar las decisiones y acciones de un núcleo agrario.
- **Asamblea**: Órgano supremo de decisión del núcleo agrario (ejido o comunidad), donde se reúnen para autorizar proyectos, otorgar anuencias y aprobar convenios.
- **Sensibilización**: Reuniones informativas realizadas con el núcleo agrario para explicar el proyecto y generar entendimiento y disposición.
- **Caminamiento**: Recorrido técnico en campo realizado para verificar la topografía, delimitar afectaciones y levantar observaciones con los posibles afectados.
- **Padrón**: Registro que contabiliza el número de miembros (ejidatarios o comuneros) que conforman a un núcleo agrario y cuenta con una fecha de expedición o actualización
- **FIFONAFE**: Fideicomiso Fondo Nacional de Fomento Ejidal - Institución encargada de administrar los fondos comunes de los núcleos agrarios y realizar el pago de las indemnizaciones.
- **Derechos_Colectivos**: tierras de uso común, las cuales representan el sustento inalienable y económico de toda la comunidad o ejido
- **Derechos_Individuales**: área parcelada, es decir, tierras que tienen un titular específico o dueño particular (como un ejidatario)
- **Indemnización**: pago o compensación económica que el Estado otorga a los sujetos o núcleos agrarios a cambio de adquirir sus bienes o tierras por causas de utilidad pública, concretamente a través del proceso legal de expropiación
- **Monto BDT**: corresponde a la indemnización de Bienes Distintos a la Tierra
- **superficie_total_ha**: Campo usado en convenios de afectación INDIVIDUAL. Mide la superficie de la parcela particular afectada con un dueño específico. Se captura en expedientes privados.
- **superficie_ampliacion_ha**: Campo usado en convenios de afectación INDIVIDUAL (Ampliación o Ampliación Remanente). Mide la nueva superficie afectada que se adiciona a la original.
- **superficie_real_afectada_ha**: Campo usado en convenios de afectación COLECTIVA. Mide el impacto sobre las tierras inalienables de uso común que requieren asambleas. La distinción es jurídica: estas tierras pertenecen al núcleo agrario completo, no a individuos.
- **Expropiación**: Es la forma legal en la que el Estado adquiere bienes por causas de utilidad pública a cambio de una indemnización
- **Comisariado Ejidal / de Bienes Comunales**: Órgano encargado de ejecutar los acuerdos de la asamblea y representar legalmente al núcleo agrario. Está conformado por un Presidente, Secretario y Tesorero.
- **Consejo de Vigilancia**: Órgano cuya función principal es supervisar las acciones del Comisariado.
- **Sujetos Agrarios**: Las personas con derechos sobre la tierra. Se clasifican en ejidatarios (titulares en ejidos), comuneros (titulares en comunidades), avecindados (más de un año de residencia) y posesionarios (poseen terrenos sin ser ejidatarios o avecindados).
- **WGS84**: Sistema de Coordenadas Mundial 1984 (World Geodetic System 1984) - Sistema de referencia de coordenadas geográficas utilizado globalmente, especificado como EPSG:4326
- **UTM**: Universal Transverse Mercator - Sistema de coordenadas proyectadas que divide el mundo en zonas, utilizado en documentos jurídicos de liberación en México
- **Geometría**: Representación espacial de entidades geográficas. Puede ser punto, línea (LineString), polígono (Polygon) o sus versiones múltiples (MultiPoint, MultiLineString, MultiPolygon)
- **Intersección_Geométrica**: Operación espacial que calcula la superposición entre dos geometrías, utilizada para determinar qué Núcleos Agrarios son afectados por un Frente
- **Sistema_de_Referencia_de_Coordenadas**: (SRC o CRS) Marco que define cómo las coordenadas se relacionan con ubicaciones en la superficie terrestre

## Requirements

### Requirement 1: Gestión de Usuarios y Control de Acceso

**User Story:** Como administrador del sistema, quiero gestionar cuentas de usuario con control de acceso basado en roles, para que los usuarios de captura puedan ingresar información, los usuarios visualizadores solo puedan ver reportes y los geógrafos puedan capturar información geográfica.

#### Acceptance Criteria

1. EL Sistema DEBERÁ soportar la creación de cuentas de usuario con roles asignados: Administrador, operador, visualizador y Geógrafo
2. CUANDO un operador inicie sesión, EL Sistema DEBERÁ otorgar permisos de lectura y escritura sobre datos administrativos y de seguimiento
3. CUANDO un visualizador inicie sesión, EL Sistema DEBERÁ otorgar permisos de solo lectura
4. CUANDO un Geógrafo inicie sesión, EL Sistema DEBERÁ otorgar permisos de lectura y escritura sobre geometrías y datos geoespaciales
5. EL Sistema DEBERÁ autenticar usuarios antes de otorgar acceso
6. EL Sistema DEBERÁ mantener un registro de auditoría de acciones de usuario
7. EL Sistema DEBERÁ permitir la asignación de uno o varios Frentes a cada usuario para organizar y delimitar su responsabilidad territorial


### Requirement 2: Gestión de Estructura del Proyecto Ferroviario

**User Story:** Como operador, quiero definir y organizar segmentos ferroviarios (Tramos) y sus subdivisiones (Frentes), para poder estructurar el proyecto geográficamente, el proyecto puede tener más de un tramo.

#### Acceptance Criteria

1. EL Sistema DEBERÁ permitir la creación de registros de Tramo con identificadores únicos
2. EL Sistema DEBERÁ permitir la creación de registros de Frente asociados a un Tramo
3. CUANDO se crea un Tramo, EL Sistema DEBERÁ requerir un nombre único y clave. El número de tramo se captura en el registro de la intersección con el Núcleo Agrario.
4. EL Sistema DEBERÁ soportar múltiples Frentes por Tramo
5. EL Sistema DEBERÁ mostrar la relación jerárquica entre Tramos y Frentes
6. EL Sistema DEBERÁ almacenar la geometría del tramo estrictamente como un trazo lineal (MultiLineString). Los polígonos de derecho de vía se calcularán de manera dinámica (on-the-fly) mediante un buffer perimetral (parametrizado en metros por el `ancho_total_derecho_via_m` de cada tramo) sobre el trazo central, usando un casting a "geography" para validaciones exactas sin depender de proyecciones planas.

### Requirement 3: Registro de Núcleos Agrarios

**User Story:** Como operador, quiero registrar Núcleos Agrarios (ejidos y comunidades) afectados por el proyecto ferroviario, para poder dar seguimiento a todas las entidades de propiedad social afectadas.

#### Acceptance Criteria

1. EL Sistema DEBERÁ permitir la creación de registros de Núcleo_Agrario
2. CUANDO se crea un Núcleo_Agrario, EL Sistema DEBERÁ capturar: nombre, tipo (Ejido/Comunidad), estado, municipio y residencia. El consecutivo se captura en el registro de la intersección con el Tramo.
3. EL Sistema DEBERÁ almacenar información de datos generales específicos para Derechos Colectivos o individuales acorde al tipo de afectación
4. EL Sistema DEBERÁ almacenar información de ORV incluyendo integrantes y fechas de vigencia
5. EL Sistema DEBERÁ dar seguimiento a información del Padrón incluyendo fecha y número de integrantes
6. EL Sistema DEBERÁ asociar cada Núcleo_Agrario con uno o más Tramos
7. El Sistema DEBERÁ permitir que el núcleo agrario sea atravesado por una o más veces por el frente ferroviario.

### Requirement 4: Registro de Afectaciones

**Historia de Usuario:** Como operador, quiero registrar superficies afectadas por el proyecto ferroviario, para poder dar seguimiento tanto a impactos de derechos colectivos como individuales.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir la creación de registros de Afectación vinculados a un Núcleo_Agrario
2. CUANDO se crea una Afectación, EL Sistema DEBERÁ capturar superficie afectada en hectáreas o metros cuadrados, tipo de tenencia, subtipo de tenencia y personas considerando si la afectación es sobre derechos colectivos, derechos individuales o tierras de uso común o parcelas afectadas
3. EL Sistema DEBERÁ clasificar la Afectación como Derecho_Colectivo o Derecho_Individual
4. DONDE una Afectación se clasifica como Derecho_Individual, EL Sistema DEBERÁ capturar número de parcela, información del titular y documentación de la propiedad
5. DONDE una Afectación se clasifica como Derecho_Colectivo, EL Sistema DEBERÁ capturar destino de la superficie, número de parcela/solar (si aplica a un área comunal específica), y relacionar el padrón y estatus de ORV vigentes en asambleas.
6. EL Sistema DEBERÁ permitir múltiples Afectaciones por Núcleo_Agrario
7. EL Sistema DEBERÁ hacer obligatoria la captura del polígono de afectación para altas desde interfaz, garantizando intersección espacial con su Núcleo y su Tramo asociado (`origen_registro IN ('migracion_excel', 'captura_sistema')`). Para importación masiva desde Excel, se permitirá geometrías nulas marcando el expediente como "Pendiente de Digitalización Espacial".

### Requirement 5: Seguimiento de Proceso de Sensibilización

**Historia de Usuario:** Como operador, quiero dar seguimiento a reuniones de sensibilización con comunidades afectadas, para poder documentar esfuerzos de acercamiento.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir el registro de eventos de Sensibilización vinculados a un Núcleo_Agrario
2. CUANDO se registra una Sensibilización, EL Sistema DEBERÁ capturar fecha programada y fecha realizada
3. EL Sistema DEBERÁ permitir múltiples eventos de Sensibilización por Núcleo_Agrario
4. EL Sistema DEBERÁ mostrar estatus de completitud basado en si la fecha realizada está poblada


### Requirement 6: Seguimiento de Caminamientos

**Historia de Usuario:** Como operador, quiero dar seguimiento a inspecciones de campo (Caminamientos), para poder documentar actividades de verificación técnica.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir el registro de eventos de Caminamiento vinculados a un Núcleo_Agrario
2. CUANDO se registra un Caminamiento, EL Sistema DEBERÁ capturar fecha programada y fecha realizada
3. EL Sistema DEBERÁ permitir múltiples Caminamientos por Núcleo_Agrario
4. EL Sistema DEBERÁ mostrar estatus de completitud basado en si la fecha realizada está poblada

### Requirement 7: Registro de Asambleas

**Historia de Usuario:** Como operador, quiero dar seguimiento a asambleas incluyendo convocatorias y realizaciones, para poder monitorear el proceso formal de aprobación.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir la creación de registros de Asamblea vinculados a un Núcleo_Agrario
2. CUANDO se crea una Asamblea, EL Sistema DEBERÁ capturar: fecha de primera convocatoria, fecha de segunda convocatoria y fecha de realización
3. EL Sistema DEBERÁ dar seguimiento a fecha de ingreso al RAN, número de solicitud, calificación registral y fecha de inscripción
4. EL Sistema DEBERÁ asociar cada Asamblea con un propósito (por ejemplo, aprobación de COP, aprobación de superficie adicional o por obras complementarias)
5. EL Sistema DEBERÁ mostrar specíficamente para la afectación de derechos colectivos que involucra al FIFONAFE, se documenta el estatus de la asamblea requerida para retirar los recursos, indicando si el trámite está "Completo", "Pendiente" o "Programado"

### Requirement 8: Gestión de Convenios

**Historia de Usuario:** Como operador, quiero registrar y dar seguimiento a convenios de diferentes tipos, para poder monitorear el proceso completo de contratación.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ soportar la creación de registros de Convenio con los siguientes tipos diferenciados por tipo de derecho afectado:
   - **Para Derechos Colectivos**: COP (Original), Modificatorio, Superficie Adicional y Obras Complementarias
   - **Para Derechos Individuales**: COP (Original), Modificatorio, Ampliación y Ampliación Remanente
2. CUANDO se crea un Convenio, EL Sistema DEBERÁ capturar: fecha de firma, monto 90%, monto 100% y opcionalmente monto BDT
3. CUANDO se crea un Convenio de tipo Obras Complementarias, EL Sistema NO DEBERÁ capturar el campo monto BDT (esta variante no incluye Bienes Distintos a la Tierra)
4. CUANDO se crea un Convenio Modificatorio para Derecho Individual, EL Sistema SOLO DEBERÁ requerir: fecha de firma, monto 90% y monto 100% (sin superficie ni BDT)
5. EL Sistema DEBERÁ dar seguimiento a fecha de ingreso al RAN, número de solicitud, calificación registral y fecha de inscripción
6. EL Sistema DEBERÁ vincular cada Convenio a una Afectación (colectiva o individual)
7. DONDE un Convenio es de tipo Superficie Adicional, EL Sistema DEBERÁ capturar superficie adicional en hectáreas
8. DONDE un Convenio es de tipo Ampliación o Ampliación Remanente, EL Sistema DEBERÁ capturar superficie de ampliación en hectáreas
9. EL Sistema DEBERÁ permitir múltiples Convenios por Afectación para representar modificaciones y enmiendas
10. EL Sistema DEBERÁ validar que el tipo de convenio sea consistente con el tipo de afectación:
    - Superficie Adicional y Obras Complementarias SOLO aplican a Derechos Colectivos
    - Ampliación y Ampliación Remanente SOLO aplican a Derechos Individuales
11. CUANDO se crea un Convenio variante (Modificatorio, Superficie Adicional, Obras Complementarias, Ampliación), EL Sistema DEBERÁ permitir vincularlo con su Convenio COP padre mediante referencia. En el caso del Modificatorio Colectivo, este puede apuntar y modificar a un `cop_original`, una `superficie_adicional` o unas `obras_complementarias`, siempre que dicho padre cuente con una Asamblea autorizadora válida.

### Requirement 9: Seguimiento de Indemnizaciones y FIFONAFE

**Historia de Usuario:** Como operador, quiero dar seguimiento a pagos de indemnización y procesamiento de FIFONAFE, para poder monitorear estatus de pagos.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir el registro de estatus de Indemnización para cada Afectación (individual o colectiva)
2. EL Sistema DEBERÁ soportar valores de estatus: Completo, Pendiente, Programado
3. EL Sistema DEBERÁ dar seguimiento a correspondencia de oficios de FIFONAFE, rastreando obligatoriamente los siguientes cuatro oficios con sus respectivos números y fechas:
    a. Oficio de FIFONAFE a DGAOPR/Representación
    b. Oficio de DGAOPR a Representación
    c. Respuesta de Representación a DGAOPR
    d. Respuesta de DGAOPR/Representación a FIFONAFE
4. EL Sistema DEBERÁ dar seguimiento a informes de no conflictos a través de la cadena de oficios antes mencionada
5. EL Sistema DEBERÁ mostrar estatus de completitud de pago por Afectación


### Requirement 10: Tablero de Convenios Formalizados

**Historia de Usuario:** Como visualizador, quiero visualizar un tablero mostrando conteos de convenios formalizados, para poder entender el progreso general.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ mostrar conteo total de convenios individuales formalizados (Convenios para Derecho_Individual con fecha de inscripción)
2. EL Sistema DEBERÁ mostrar conteo total de convenios colectivos formalizados (Convenios para Derecho_Colectivo con fecha de inscripción)
3. EL Sistema DEBERÁ mostrar conteo total de Núcleos Agrarios afectados
4. CUANDO se muestran datos del tablero, EL Sistema DEBERÁ actualizarse automáticamente cuando los datos subyacentes cambien
5. EL Sistema DEBERÁ permitir filtrado por Tramo

### Requirement 11: Tablero de Superficies Liberadas

**Historia de Usuario:** Como visualizador, quiero visualizar superficies liberadas con ubicaciones y mediciones, para poder dar seguimiento al progreso espacial.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ mostrar superficies liberadas para Derechos_Individuales con ubicación y metros cuadrados
2. EL Sistema DEBERÁ mostrar superficies liberadas para Derechos_Colectivos (uso común) con ubicación y metros cuadrados
3. CUANDO una Afectación tiene un Convenio asociado con fecha de inscripción, EL Sistema DEBERÁ clasificar esa superficie como liberada
4. EL Sistema DEBERÁ calcular área total liberada por Núcleo_Agrario
5. EL Sistema DEBERÁ permitir filtrado por Tramo y Frente

### Requirement 12: Visualización de Progreso por Tramo

**Historia de Usuario:** Como visualizador, quiero visualizar gráficas tipo dona mostrando porcentaje liberado por segmento ferroviario, para poder evaluar completitud a nivel de segmento.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ mostrar una gráfica tipo dona para cada Tramo mostrando porcentaje de superficie liberada
2. CUANDO se calcula porcentaje liberado, EL Sistema DEBERÁ dividir metros cuadrados liberados totales entre metros cuadrados afectados totales por Tramo
3. EL Sistema DEBERÁ mostrar tanto superficies liberadas como pendientes en metros cuadrados
4. EL Sistema DEBERÁ codificar con colores las barras de progreso (por ejemplo, verde para >75%, amarillo para 25-75%, rojo para <25%)
5. EL Sistema DEBERÁ permitir navegación detallada desde nivel Tramo hasta nivel Frente

### Requirement 13: Generación de Reportes

**Historia de Usuario:** Como visualizador, quiero generar y exportar reportes, para poder compartir información de progreso con actores interesados.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ generar reportes resumidos incluyendo: total de Núcleos Agrarios, total de Convenios, superficie total liberada y tramos
2. EL Sistema DEBERÁ generar reportes detallados listando todas las Afectaciones con estatus por Tramo
3. EL Sistema DEBERÁ exportar reportes en formatos CSV, PDF y Excel
4. CUANDO se genera un reporte, EL Sistema DEBERÁ incluir marca de tiempo de generación e información del usuario
5. EL Sistema DEBERÁ permitir filtrado de reportes por rango de fechas, Tramo y estatus


### Requirement 14: Migración de Datos desde Excel

**Historia de Usuario:** Como administrador del sistema, quiero importar datos existentes desde hojas de cálculo Excel, para que la información histórica de seguimiento se preserve en el nuevo sistema.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ proporcionar una función de importación de datos que acepte archivos Excel (.xlsx, .xls)
2. CUANDO se importan datos, EL Sistema DEBERÁ validar campos requeridos antes de la inserción
3. SI la validación de importación falla, ENTONCES EL Sistema DEBERÁ generar un reporte de errores identificando filas inválidas
4. CUANDO la importación es exitosa, EL Sistema DEBERÁ generar un reporte resumido de registros importados
5. EL Sistema DEBERÁ soportar plantillas de importación para: Núcleos Agrarios, Afectaciones, Convenios, Asambleas e Indemnizaciones

### Requirement 15: Gestión de Documentación Soporte

**Historia de Usuario:** Como operador, quiero dar seguimiento al estatus de documentación soporte, para poder identificar documentos faltantes.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir el registro de estatus de documentación para cada Núcleo_Agrario
2. EL Sistema DEBERÁ dar seguimiento a categorías: Documentación Disponible y Documentación Faltante
3. CUANDO se documenta estatus, EL Sistema DEBERÁ permitir especificación de tipos de documento (por ejemplo, acta de ORV, Padrón, certificados)
4. EL Sistema DEBERÁ generar alertas para documentos críticos faltantes
5. EL Sistema DEBERÁ mostrar porcentaje de completitud de documentación por Núcleo_Agrario

### Requirement 16: Seguimiento de Inscripciones en RAN

**Historia de Usuario:** Como operador, quiero dar seguimiento al proceso de inscripción de documentos en el RAN, para poder monitorear la formalización registral.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ registrar fecha de ingreso al RAN para Asambleas y Convenios
2. EL Sistema DEBERÁ capturar número de solicitud de ingreso al RAN
3. EL Sistema DEBERÁ registrar calificación registral emitida por el RAN
4. EL Sistema DEBERÁ capturar fecha de inscripción definitiva en el RAN
5. EL Sistema DEBERÁ calcular días transcurridos entre ingreso y inscripción en el RAN

### Requirement 17: Gestión de ORV (Órganos de Representación y Vigilancia)

**Historia de Usuario:** Como operador, quiero registrar integrantes de los órganos de representación de núcleos agrarios, para poder mantener información actualizada de representantes legales.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ registrar integrantes del Comisariado: Presidente, Secretario y Tesorero
2. EL Sistema DEBERÁ registrar integrantes del Consejo de Vigilancia: Presidente y Secretarios
3. EL Sistema DEBERÁ capturar fechas de inicio y fin de vigencia del ORV
4. EL Sistema DEBERÁ calcular si el ORV está vigente basado en la fecha de fin de vigencia
5. EL Sistema DEBERÁ registrar si el acta de elección del ORV está inscrita en el RAN


### Requirement 18: Registro de Padrón de Ejidatarios/Comuneros

**Historia de Usuario:** Como operador, quiero registrar información del padrón de ejidatarios o comuneros, para poder documentar la composición del núcleo agrario.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ capturar fecha del padrón
2. EL Sistema DEBERÁ registrar número total de ejidatarios o comuneros en el padrón
3. EL Sistema DEBERÁ mantener historial de cambios en el padrón
4. EL Sistema DEBERÁ vincular obligatoriamente cada acta de asamblea registrada con la versión histórica del padrón vigente en su momento, garantizando la inmutabilidad de la auditoría de quórum legal.
5. EL Sistema DEBERÁ asociar el padrón con el Núcleo_Agrario correspondiente

### Requirement 19: Indicadores de Excepciones Operativas

**Historia de Usuario:** Como operador, quiero marcar núcleos agrarios y tramos sujetos a excepciones operativas (expropiación directa, comunidad indígena, no afecta tierras de uso común), para poder distinguir estos procedimientos especiales.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir marcar un Núcleo_Agrario como sujeto a expropiación directa
2. EL Sistema DEBERÁ permitir marcar un Núcleo_Agrario como Comunidad Indígena
3. EL Sistema DEBERÁ permitir indicar si El Proyecto Ferroviario No Afecta Tierras de Uso Común para un tramo-núcleo específico
4. CUANDO se active alguna de estas excepciones, EL Sistema DEBERÁ mostrar un indicador visual distintivo
5. EL Sistema DEBERÁ filtrar reportes y tableros por tipo de procedimiento (convenio vs expropiación)
6. EL Sistema DEBERÁ registrar razón o motivo de la expropiación directa
7. EL Sistema DEBERÁ generar estadísticas separadas para núcleos bajo expropiación directa

### Requirement 20: Seguimiento de Obras Complementarias

**Historia de Usuario:** Como operador, quiero dar seguimiento específico a convenios de obras complementarias, para poder monitorear este tipo especial de afectación.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ soportar creación de Convenios tipo Obras Complementarias
2. CUANDO se crea un Convenio de Obras Complementarias, EL Sistema DEBERÁ capturar superficie total real afectada
3. EL Sistema DEBERÁ detonar un nuevo ciclo relacional completo creando registros independientes de Asamblea y Convenio para las Obras Complementarias, preservando intacto el COP original y abandonando la captura en campos paralelos duplicados.
4. EL Sistema DEBERÁ calcular montos específicos (90%, 100%) para Obras Complementarias
5. EL Sistema DEBERÁ mostrar en reportes separación entre convenios COP estándar y Obras Complementarias

### Requirement 21: Gestión de Superficies Adicionales

**Historia de Usuario:** Como operador, quiero registrar superficies adicionales descubiertas durante la ejecución del proyecto, para poder documentar expansiones de afectación.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ soportar creación de Convenios tipo Superficie Adicional
2. CUANDO se registra Superficie Adicional, EL Sistema DEBERÁ capturar hectáreas adicionales afectadas
3. EL Sistema DEBERÁ vincular la Superficie Adicional con el Convenio COP original
4. EL Sistema DEBERÁ actualizar superficie total liberada al inscribirse Convenio de Superficie Adicional
5. EL Sistema DEBERÁ mostrar histórico de expansiones de superficie por Núcleo_Agrario


### Requirement 22: Alertas y Notificaciones de Vencimientos

**Historia de Usuario:** Como operador, quiero recibir alertas sobre vencimientos próximos de ORV y eventos programados, para poder actuar oportunamente.

#### Criterios de Aceptación

1. CUANDO la fecha de vencimiento de un ORV esté a menos de 30 días, EL Sistema DEBERÁ generar una alerta
2. CUANDO un evento programado (Sensibilización, Caminamiento, Asamblea) esté próximo, EL Sistema DEBERÁ notificar al usuario responsable
3. EL Sistema DEBERÁ mostrar un tablero de alertas en la página principal
4. EL Sistema DEBERÁ permitir configurar anticipación de alertas por tipo de evento
5. CUANDO se cumpla una fecha programada sin registrar realización, EL Sistema DEBERÁ marcar como evento vencido

### Requirement 23: Cálculo de Montos de Indemnización

**Historia de Usuario:** Como operador, quiero registrar diferentes montos asociados a convenios (90%, 100%, BDT), para poder dar seguimiento completo a obligaciones económicas.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ capturar monto 90% para cada Convenio cuando aplique
2. EL Sistema DEBERÁ capturar monto 100% para cada Convenio
3. EL Sistema DEBERÁ capturar monto BDT (Bienes Distintos a la Tierra) cuando aplique
4. EL Sistema DEBERÁ calcular monto total por Convenio sumando componentes aplicables
5. EL Sistema DEBERÁ generar reporte de montos totales comprometidos por Tramo

### Requirement 24: Búsqueda y Filtrado Avanzado

**Historia de Usuario:** Como visualizador, quiero buscar y filtrar información por múltiples criterios, para poder localizar rápidamente datos específicos.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ proporcionar búsqueda por nombre de Núcleo_Agrario
2. EL Sistema DEBERÁ permitir filtrado por estado, municipio y residencia
3. EL Sistema DEBERÁ permitir filtrado por estatus de convenio (firmado, inscrito, pendiente)
4. EL Sistema DEBERÁ permitir filtrado por rango de fechas
5. EL Sistema DEBERÁ combinar múltiples filtros simultáneamente

### Requirement 25: Auditoría y Trazabilidad

**Historia de Usuario:** Como administrador del sistema, quiero mantener un registro de auditoría de todas las modificaciones, para poder garantizar trazabilidad y rendición de cuentas.

#### Criterios de Aceptación

1. CUANDO se crea un registro, EL Sistema DEBERÁ almacenar usuario, fecha y hora de creación
2. CUANDO se modifica un registro, EL Sistema DEBERÁ almacenar usuario, fecha, hora y valores modificados
3. EL Sistema DEBERÁ permitir consultar historial de cambios por registro
4. EL Sistema DEBERÁ generar reportes de auditoría por usuario y rango de fechas
5. EL Sistema DEBERÁ preservar historial de auditoría de forma permanente
6. EL Sistema DEBERÁ aplicar el registro de auditoría estricto (vía base de datos) a absolutamente todas las tablas operativas, incluyendo accesos de usuario, alertas y documentación soporte.

### Requirement 26: Captura y Edición de Geometrías de Tramos

**Historia de Usuario:** Como Geógrafo, quiero capturar y editar el trazo de Tramos ferroviarios en el mapa, para poder representar espacialmente el proyecto.

#### Criterios de Aceptación

1. CUANDO el Geógrafo dibuja un trazo, EL Sistema DEBERÁ almacenar la geometría como línea (LineString o MultiLineString)
2. EL Sistema DEBERÁ permitir al Geógrafo editar geometrías existentes de Tramos
3. CUANDO se captura una geometría, EL Sistema DEBERÁ validar que el sistema de coordenadas sea WGS84 (EPSG:4326) o UTM zona correspondiente
4. EL Sistema DEBERÁ permitir importar geometrías de Tramos desde archivos Shapefile, KML o GeoJSON
5. CUANDO se importa una geometría, EL Sistema DEBERÁ transformar coordenadas al sistema de referencia estándar del sistema si es necesario
6. EL Sistema DEBERÁ mostrar advertencias cuando se detecten inconsistencias en el sistema de coordenadas

### Requirement 27: Captura y Edición de Geometrías de Frentes

**Historia de Usuario:** Como Geógrafo, quiero dividir el trazo de Tramos en Frentes, para poder segmentar el proyecto en subdivisiones operativas.

#### Criterios de Aceptación

1. CUANDO el Geógrafo crea un Frente, EL Sistema DEBERÁ almacenar la geometría como segmento de línea del Tramo padre
2. EL Sistema DEBERÁ validar que la geometría del Frente esté contenida dentro del Tramo correspondiente
3. CUANDO el Geógrafo modifica un Frente, EL Sistema DEBERÁ permitir edición de su geometría lineal
4. EL Sistema DEBERÁ calcular la longitud del Frente automáticamente al capturar o modificar su geometría
5. EL Sistema DEBERÁ permitir al Geógrafo dividir un Tramo en múltiples Frentes de forma interactiva en el mapa

### Requirement 28: Captura y Edición de Geometrías de Núcleos Agrarios

**Historia de Usuario:** Como Geógrafo, quiero capturar y editar polígonos de Núcleos Agrarios, para poder representar espacialmente los ejidos y comunidades afectados.

#### Criterios de Aceptación

1. CUANDO el Geógrafo dibuja un Núcleo_Agrario, EL Sistema DEBERÁ almacenar la geometría como polígono o multipolígono
2. EL Sistema DEBERÁ permitir al Geógrafo editar geometrías existentes de Núcleos Agrarios
3. CUANDO se captura una geometría de Núcleo_Agrario, EL Sistema DEBERÁ validar que el sistema de coordenadas sea WGS84 (EPSG:4326) o UTM zona correspondiente
4. EL Sistema DEBERÁ permitir importar geometrías de Núcleos Agrarios desde archivos Shapefile, KML o GeoJSON
5. EL Sistema DEBERÁ calcular automáticamente la superficie del polígono en hectáreas y metros cuadrados
6. EL Sistema DEBERÁ detectar automáticamente intersecciones entre Núcleos Agrarios y Frentes

### Requirement 29: Validación de Sistemas de Coordenadas

**Historia de Usuario:** Como Geógrafo, quiero que el sistema valide los sistemas de coordenadas de las geometrías, para evitar errores de ubicación espacial.

#### Criterios de Aceptación

1. CUANDO se importa o captura una geometría, EL Sistema DEBERÁ detectar el sistema de coordenadas declarado
2. SI el sistema de coordenadas no es WGS84 ni UTM, ENTONCES EL Sistema DEBERÁ mostrar advertencia al Geógrafo
3. EL Sistema DEBERÁ verificar que las coordenadas UTM correspondan a la zona correcta según la ubicación geográfica del proyecto
4. CUANDO se detecten coordenadas fuera del rango válido, EL Sistema DEBERÁ rechazar la geometría con mensaje descriptivo
5. EL Sistema DEBERÁ permitir al Geógrafo especificar explícitamente el sistema de coordenadas de entrada durante la importación

### Requirement 30: Mapa Interactivo Principal

**Historia de Usuario:** Como visualizador, quiero visualizar un mapa interactivo del proyecto ferroviario, para poder explorar espacialmente el trazo, frentes y núcleos agrarios.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ mostrar un mapa base interactivo con capacidades de zoom y paneo
2. EL Sistema DEBERÁ renderizar el trazo completo del proyecto ferroviario como líneas sobre el mapa
3. EL Sistema DEBERÁ mostrar los Tramos como líneas diferenciadas por color o estilo
4. EL Sistema DEBERÁ mostrar los Frentes como segmentos del trazo con colores codificados según su porcentaje de avance
5. EL Sistema DEBERÁ mostrar los Núcleos Agrarios como polígonos sobre el mapa
6. EL Sistema DEBERÁ proporcionar controles de capas para activar/desactivar la visualización de Tramos, Frentes y Núcleos Agrarios

### Requirement 31: Visualización de Núcleos Agrarios en Mapa

**Historia de Usuario:** Como visualizador, quiero ver Núcleos Agrarios representados en el mapa con información al interactuar, para poder identificar rápidamente su estatus.

#### Criterios de Aceptación

1. CUANDO se muestra un Núcleo_Agrario en el mapa, EL Sistema DEBERÁ aplicar color codificado según su estatus de liberación
2. EL Sistema DEBERÁ usar escala de colores distintiva: rojo para "sin anuencia", amarillo para "en proceso", verde para "liberado"
3. CUANDO el usuario pase el mouse sobre un Núcleo_Agrario, EL Sistema DEBERÁ mostrar tooltip con: nombre, tipo (Ejido/Comunidad), superficie total y estatus
4. CUANDO el usuario haga clic en un Núcleo_Agrario, EL Sistema DEBERÁ abrir panel lateral con información detallada completa
5. EL Sistema DEBERÁ permitir filtrar visibilidad de Núcleos Agrarios por estatus, tipo y municipio

### Requirement 32: Navegación Jerárquica desde Proyecto hasta Núcleos Agrarios

**Historia de Usuario:** Como visualizador, quiero navegar jerárquicamente desde el Proyecto hasta los Núcleos Agrarios en el mapa, para poder explorar el progreso en diferentes niveles de detalle.

#### Criterios de Aceptación

1. CUANDO el usuario selecciona un Proyecto, EL Sistema DEBERÁ mostrar todos sus Tramos en el mapa
2. CUANDO el usuario hace clic en un Tramo, EL Sistema DEBERÁ destacar ese Tramo y mostrar sus Frentes con colores según avance
3. EL Sistema DEBERÁ mostrar el porcentaje de avance general del Tramo seleccionado en panel informativo
4. CUANDO el usuario hace clic en un Frente, EL Sistema DEBERÁ mostrar en panel lateral: porcentaje de avance total, porcentaje de superficie de uso común liberada, porcentaje de superficie de uso individual liberada
5. CUANDO se selecciona un Frente, EL Sistema DEBERÁ listar los Núcleos Agrarios que intersectan ese Frente
6. CUANDO el usuario hace clic en un Núcleo_Agrario desde la lista, EL Sistema DEBERÁ centrar el mapa en ese núcleo y abrir su ficha completa

### Requirement 33: Panel de Información Detallada de Frente

**Historia de Usuario:** Como visualizador, quiero ver información detallada de un Frente al seleccionarlo, para poder entender su progreso de liberación.

#### Criterios de Aceptación

1. CUANDO se selecciona un Frente, EL Sistema DEBERÁ mostrar de forma segregada y no excluyente: el Avance Legal y el Avance Geoespacial.
2. EL Sistema DEBERÁ calcular el porcentaje de Avance Legal como: (superficie liberada inscrita formalmente / superficie total afectada) × 100
3. EL Sistema DEBERÁ calcular el porcentaje de Avance Geoespacial como: (superficie afectada con geometría validada / superficie total afectada) × 100
4. EL Sistema DEBERÁ mostrar desglose de superficie de uso común liberada y superficie de uso individual liberada
5. EL Sistema DEBERÁ listar todos los Núcleos Agrarios que intersectan el Frente con: nombre, superficie afectada y estatus legal/espacial actual.

### Requirement 34: Cálculo Automático de Superficies por Frente

**Historia de Usuario:** Como visualizador, quiero que el sistema calcule automáticamente las superficies afectadas y liberadas por Frente, para obtener métricas de avance precisas.

#### Criterios de Aceptación

1. CUANDO existen geometrías de Frente y Núcleos Agrarios, EL Sistema DEBERÁ calcular automáticamente las intersecciones geométricas
2. EL Sistema DEBERÁ calcular superficie total afectada por Frente como suma de todas las intersecciones con Núcleos Agrarios
3. CUANDO un Convenio es inscrito en el RAN, EL Sistema DEBERÁ contabilizar la superficie correspondiente como liberada
4. EL Sistema DEBERÁ calcular superficie liberada por Frente distinguiendo entre uso común y uso individual
5. EL Sistema DEBERÁ recalcular automáticamente los porcentajes de avance cuando se actualicen geometrías o se inscriban convenios
6. EL Sistema DEBERÁ validar que la suma de superficies liberadas no exceda la superficie total afectada del Frente

### Requirement 35: Codificación de Colores por Avance de Frente

**Historia de Usuario:** Como visualizador, quiero ver los Frentes codificados con colores según su porcentaje de avance, para identificar rápidamente el progreso en el mapa.

#### Criterios de Aceptación

1. CUANDO se muestra un Frente en el mapa, EL Sistema DEBERÁ aplicar color según su porcentaje de avance
2. EL Sistema DEBERÁ usar escala de colores: rojo para avance <25%, amarillo para avance entre 25% y 75%, verde para avance >75%
3. CUANDO el usuario pase el mouse sobre un Frente, EL Sistema DEBERÁ mostrar tooltip con: nombre del Frente, porcentaje de avance y superficie liberada
4. EL Sistema DEBERÁ actualizar automáticamente los colores cuando cambien los porcentajes de avance
5. EL Sistema DEBERÁ proporcionar leyenda visible explicando la escala de colores

### Requirement 36: Importación de Archivos Geoespaciales

**Historia de Usuario:** Como Geógrafo, quiero importar geometrías desde archivos geoespaciales estándar, para poder integrar información proveniente de otras fuentes.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ soportar importación de archivos Shapefile (.shp con sus archivos asociados .shx, .dbf, .prj)
2. EL Sistema DEBERÁ soportar importación de archivos KML y KMZ
3. EL Sistema DEBERÁ soportar importación de archivos GeoJSON
4. CUANDO se importa un archivo, EL Sistema DEBERÁ leer el sistema de coordenadas desde los metadatos del archivo (.prj en Shapefile)
5. SI el sistema de coordenadas no se puede detectar, ENTONCES EL Sistema DEBERÁ solicitar al Geógrafo que lo especifique manualmente
6. CUANDO se completa la importación, EL Sistema DEBERÁ mostrar resumen de geometrías importadas: número de elementos, tipo de geometría y sistema de coordenadas
7. EL Sistema DEBERÁ validar que las geometrías importadas sean del tipo correcto (líneas para Tramos/Frentes, polígonos para Núcleos Agrarios)


---

## Non-Functional Requirements

### Rendimiento

**RNF-1:** CUANDO se ejecuta una consulta de tablero, EL Sistema DEBERÁ retornar resultados dentro de 3 segundos para conjuntos de datos que contengan hasta 1,000 Núcleos Agrarios.

**RNF-2:** CUANDO múltiples usuarios concurrentes accedan al sistema, EL Sistema DEBERÁ soportar al menos 50 usuarios simultáneos sin degradación de rendimiento.

### Integridad de Datos

**RNF-3:** EL Sistema DEBERÁ garantizar integridad referencial entre entidades relacionadas (por ejemplo, Convenio debe referenciar Afectación válida).

**RNF-4:** CUANDO se modifican datos, EL Sistema DEBERÁ mantener una pista de auditoría incluyendo usuario, marca de tiempo y valores modificados.

### Usabilidad

**RNF-5:** EL Sistema DEBERÁ proporcionar una interfaz de usuario en idioma español.

**RNF-6:** EL Sistema DEBERÁ mostrar mensajes de error de validación en lenguaje claro y accionable.

**RNF-7:** EL Sistema DEBERÁ proporcionar ayuda contextual y tooltips en formularios de captura de datos.

### Seguridad

**RNF-8:** EL Sistema DEBERÁ cifrar contraseñas de usuario utilizando algoritmos de hashing estándar de la industria.

**RNF-9:** CUANDO una sesión de usuario esté inactiva por 30 minutos, EL Sistema DEBERÁ cerrar sesión automáticamente.

**RNF-10:** EL Sistema DEBERÁ registrar intentos de acceso fallidos y bloquear cuentas después de 5 intentos consecutivos fallidos.

### Compatibilidad

**RNF-11:** EL Sistema DEBERÁ ser accesible mediante navegadores web modernos (Chrome, Firefox, Edge, Safari) sin requerir plugins.

**RNF-12:** EL Sistema DEBERÁ ser responsivo y funcional en pantallas de escritorio con resolución mínima de 1280x720 píxeles.

### Disponibilidad

**RNF-13:** EL Sistema DEBERÁ estar disponible el 99% del tiempo durante horario laboral (8:00 AM - 8:00 PM hora local).

**RNF-14:** EL Sistema DEBERÁ realizar respaldos automáticos diarios de la base de datos.

### Mantenibilidad

**RNF-15:** EL Sistema DEBERÁ utilizar arquitectura modular que permita actualizaciones sin tiempo de inactividad prolongado.

**RNF-16:** EL Sistema DEBERÁ mantener logs de errores y excepciones para facilitar diagnóstico de problemas.

### Rendimiento Geoespacial

**RNF-17:** CUANDO se renderiza un mapa con hasta 100 Núcleos Agrarios, EL Sistema DEBERÁ mostrar las geometrías dentro de 2 segundos.

**RNF-18:** CUANDO se calculan intersecciones geométricas, EL Sistema DEBERÁ completar el cálculo para un Frente con hasta 50 Núcleos Agrarios en menos de 5 segundos.

**RNF-19:** EL Sistema DEBERÁ soportar visualización de geometrías con hasta 10,000 vértices sin degradación perceptible de rendimiento.

### Precisión Geoespacial

**RNF-20:** CUANDO se transforman coordenadas entre sistemas de referencia, EL Sistema DEBERÁ mantener precisión de al menos 1 metro.

**RNF-21:** CUANDO se calculan superficies de polígonos, EL Sistema DEBERÁ proporcionar resultados con precisión de al menos 0.01 hectáreas.

**RNF-22:** EL Sistema DEBERÁ almacenar coordenadas con precisión de al menos 6 decimales para coordenadas geográficas (aproximadamente 0.11 metros).

---

## Consideraciones Técnicas Adicionales

### Migración de Datos

La migración desde Excel requiere mapeo cuidadoso de:
- Datos Generales de Núcleos Agrarios
- Seguimiento de Afectación a Derechos Colectivos
- Seguimiento de Afectación a Derechos Individuales
- Datos de FIFONAFE
- Información de ORV
- Documentación soporte

### Estructura Geográfica

El sistema debe reflejar la jerarquía:
**Proyecto → Tramos → Frentes → Núcleos Agrarios → Afectaciones**

Cada nivel debe permitir agregación de métricas hacia niveles superiores.

### Consideraciones Geoespaciales

El sistema debe manejar:
- **Sistemas de Coordenadas**: Soporte dual para WGS84 (visualización web) y UTM (documentos legales)
- **Transformación de Coordenadas**: Capacidad de transformar entre sistemas sin pérdida de precisión
- **Cálculos Geométricos**: Intersecciones, cálculo de superficies, longitudes y distancias
- **Validación Espacial**: Verificación de consistencia topológica (polígonos sin auto-intersecciones, geometrías válidas)
- **Optimización de Renderizado**: Simplificación de geometrías complejas para visualización en diferentes niveles de zoom
- **Capas Base**: Integración con servicios de mapas base (OpenStreetMap, imágenes satelitales)

### Cálculos Automáticos de Superficie

El sistema debe calcular automáticamente:
- Superficie afectada por Frente mediante intersección geométrica con Núcleos Agrarios
- Superficie liberada por Frente basada en Convenios inscritos en RAN
- Porcentajes de avance distinguiendo entre uso común e individual
- Validación de consistencia entre superficies calculadas geométricamente y superficies registradas administrativamente

