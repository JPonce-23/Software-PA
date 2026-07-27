A continuación, se detalla rigurosamente paso a paso cómo interviene la Procuraduría Agraria (PA) y en qué momento exacto se captura cada uno de los datos en el sistema integral:

Fase 1: Identificación Administrativa, Diagnóstico Legal y Estructura Base
Todo comienza cuando se recibe el trazo del proyecto y las instituciones deben identificar administrativamente la tierra y verificar el estatus legal de sus representantes en el Registro Agrario Nacional (RAN).

1. Datos Generales (Multi-Proyecto) y de Identificación del Tramo: Se abre un expediente y la PA registra la base territorial de manera escalable:
* Proyecto: Identificador del proyecto (ej. "Tren Maya", "Tren Interoceánico") para permitir la escalabilidad del sistema.
* Clave del Tramo y Frente de Obra (¿necesario?): Subdivisión logística para asignar brigadas y metas.
* Consecutivo: Número de control interno asignado al registro.
* Entidad y Municipio: Ubicación registral del núcleo agrario.
* Residencia: La oficina regional de la PA encargada del seguimiento.
* Núcleo Agrario: El nombre oficial de la población.
* E/C (Ejido/Comunidad): Régimen legal al que pertenece.

2. Catálogo Centralizado de Sujetos Agrarios (Personas): Antes de registrar padrones u órganos, se captura a los individuos en una base de datos centralizada para evitar redundancias:
* Persona (Sujeto Agrario): Se registra CURP, RFC, Nombre, Apellidos y datos de contacto de cada ejidatario, comunero o titular.

3. Control de Órganos de Representación y Vigilancia (ORV) y Padrón: La PA investiga en el RAN quién tiene la autoridad legal para firmar y cuántas personas conforman la comunidad. En una matriz dedicada exclusivamente a los ORV, vinculando a los sujetos del catálogo de personas:
* Comisariado (Presidente, Secretario, Tesorero) y Consejo de Vigilancia: Vinculados directamente al catálogo de 'Persona'.
* Inicio Vigencia y Fin Vigencia: Cuándo empezaron y cuándo terminan su periodo.
* ORV Vigentes (Sí/No) y Acta de Elección inscrita en el RAN.
* Fecha de Padrón y Padrón (Número de Ejidatarios/Comuneros): Para saber cuántos votos conforman el quórum.

4. Soporte Documental Robusto y Excepciones: 
* Documentación Disponible / Faltante.
* Control Criptográfico: Al subir un PDF (ej. un acta), el sistema genera y guarda una huella digital (hash) y versionado del documento, garantizando ante la ley que los archivos no sean alterados posteriormente.
* Categoría Sin Nombre: Manejo de excepciones como Comunidad Indígena o Expropiación Directa.

Fase 2: Acercamiento en Campo (Gestión Social, Sensibilización y Caminamiento)
La PA y la SEDATU acuden al territorio. Aquí se levanta una bitácora detallada de las actividades de campo, controlando acuerdos y participantes.

1. Registro de Actividades y Minutas:
* Actividad de Sensibilización / Caminamiento: Se captura fecha programada, fecha realizada, hora y lugar.
* Lista de Asistencia (Participantes): Se vincula a las Personas que asistieron a la reunión.
* Acuerdos y Compromisos: Se registran los compromisos pactados con la comunidad y el responsable de la PA asignado a darles seguimiento.
* Seguimiento (Kanban): A través de un tablero, los mandos pueden ver el porcentaje de avance de estos compromisos, observaciones y alertas tempranas (ej. inconformidades).

A partir del caminamiento topográfico, el proceso se bifurca en dos grandes matrices:

Fase 3A: Matriz de Seguimiento a Derechos Colectivos (Uso Común)
Como las tierras de uso común son de todos, la PA debe recabar información técnica específica. Todo debe ser autorizado por la Asamblea.

1. Convenio de Ocupación Previa (Original):
* Asamblea: Se gestionan convocatorias (1ra, 2da) y la Asamblea Realizada, capturando el quórum exacto.
* RAN (Acta): Ingreso de solicitud, calificación y Acta Inscrita en el RAN (Fecha).
* Firma y Montos: Convenio Firmado (Fecha), Superficie Total Real Afectada (Ha) validada geométricamente por PostGIS, y montos de tabulador.
* RAN (Convenio): Ingreso, calificación e inscripción del convenio.

2. Variantes de Convenios Colectivos:
* Convenio Modificatorio, Convenio Superficie Adicional, Convenio Obras Complementarias: Se registran las alteraciones detonando, según la ley, nuevas asambleas y verificaciones topográficas.

Fase 3B: Matriz de Seguimiento a Derechos Individuales (Parcelas)
Como las parcelas tienen un dueño asignado, no interviene la asamblea. La PA crea un expediente privado vinculado al catálogo central de Personas.

1. Datos Generales de la Parcela: 
* Titular de la Parcela: Se vincula al 'Sujeto Agrario / Persona' (CURP, Nombre).
* No. de Parcela PPT, Certificado Parcelario, Folio de Derechos y Constancia de Vigencia.

2. Convenio de Ocupación Previa Individual (y sus variantes): 
* COP Original, Modificatorio, Ampliación y Remanente: Captura de firmas, superficies exactas, montos y trámite de inscripción ante el RAN.

Fase 4: Matriz de FIFONAFE, Trazabilidad Financiera y Cierres
Antes de que la indemnización sea pagada, el FIFONAFE exige a la PA garantizar la paz social. Se incorpora un control financiero granular.

1. Informe de No Conflictos (Cruces de oficios): 
* Se rastrea toda la cadena de comunicación de oficios entre FIFONAFE, SEDATU (DGAOPR) y la PA para dar luz verde al pago.

2. Control Financiero (Avalúos, Pagos y Transferencias): Una vez autorizado, se rastrea el flujo del dinero:
* Avalúo: Registro del folio del INDAABIN y el monto total dictaminado.
* Indemnización y Pagos Parciales: En lugar de un estatus simple (Completo/Pendiente), se registra cada pago emitido.
* Transferencia Bancaria: Se captura la fecha de transferencia, banco y referencia bancaria o folio de cheque entregado a la persona o fondo común.
* Para Derechos Colectivos, el proceso culmina con el registro de la Asamblea Retiro de Fondos para decidir el reparto del depósito general.

De esta forma, cada dato cumple una función cronológica, auditable, financieramente trazable y geográficamente validada dentro del gran engranaje de liberación de tierras.

