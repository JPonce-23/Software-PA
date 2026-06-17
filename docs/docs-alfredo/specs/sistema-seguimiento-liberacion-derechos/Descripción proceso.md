A continuación, te detallo rigurosamente paso a paso cómo interviene la Procuraduría Agraria (PA) y en qué momento exacto se captura cada uno de los datos listados en el documento Estructura [Datos.md]:

Fase 1: Identificación Administrativa y Diagnóstico Legal  
Todo comienza cuando se recibe el trazo del proyecto y las instituciones deben identificar administrativamente la tierra y verificar el estatus legal de sus representantes en el Registro Agrario Nacional (RAN).

1\. Datos Generales y de Identificación del Tramo: Tanto para la ruta de colectivos como de individuales, se abre un expediente y la PA registra la base territorial:

* Consecutivo: Número de control interno asignado al registro.  
* Entidad y Municipio: Ubicación registral del núcleo agrario.  
* Residencia: La oficina regional de la PA encargada del seguimiento.  
* Núcleo Agrario: El nombre oficial de la población.  
* E/C (Ejido/Comunidad): Régimen legal al que pertenece.  
* Clave del Tramo y Número de Tramo: Se capturan para saber qué porción exacta del proyecto ferroviario pasa por ahí.

2\. Control de Órganos de Representación y Vigilancia (ORV) y Padrón: La PA investiga en el RAN quién tiene la autoridad legal para firmar y cuántas personas conforman la comunidad. En una matriz dedicada exclusivamente a los ORV, se capturan:

* Num: Identificador numérico de esta pestaña.  
* Comisariado\_Presidente, Comisariado\_Secretario, Comisariado\_Tesorero: Nombres exactos de quienes ejecutan los acuerdos.  
* Consejo\_Vigilancia\_Presidente, Consejo\_Vigilancia\_Secretario1, Consejo\_Vigilancia\_Secretario2: Nombres de quienes supervisan al Comisariado.  
* Inicio Vigencia y Fin Vigencia: Cuándo empezaron y cuándo terminan su periodo.  
* ORV Vigentes (Sí/No) Estatus, Fecha de Vencimiento de ORV y Acta de Elección de ORV Inscrita en el RAN (Sí/No): Para garantizar que sus firmas tendrán validez legal.  
* Fecha de Padrón y Padrón: Número de Ejidatarios/Comuneros: Para saber cuántos votos conforman el quórum de una asamblea.

3\. Soporte Documental y Excepciones: A lo largo de todo el proceso, las tres matrices (Colectivos, Individuales y ORV) llevan un control físico del expediente:

* Documentación Disponible y Documentación Faltante: Para llevar un checklist de los papeles.  
* Observaciones: Un campo de texto libre contemplado en el formato.  
* Categoría Sin Nombre: Un bloque especial que usa la PA para catalogar excepciones operativas: Comunidad Indígena (si requieren protocolos especiales), El Proyecto Ferroviario No Afecta Tierras de Uso Común (si el tren solo toca parcelas privadas) o Expropiación Directa (cuando fracasa el acuerdo y se debe forzar el juicio expropiatorio desde cero).

Fase 2: Acercamiento en Campo (Sensibilización y Caminamiento)  
La PA y la SEDATU acuden al territorio para marcar la tierra y convencer a la gente de autorizar el Convenio de Ocupación Previa (COP). Se captura sistemáticamente:

* Reunión Programada (Fecha) y Reunión Realizada (Fecha): Para registrar los eventos de "Sensibilización".  
* Programado (Fecha) / Caminamiento Programado (Fecha) y Realizado (Fecha) / Caminamiento Realizado (Fecha): Para registrar el marcaje topográfico en campo.

A partir de este recorrido, el proceso se bifurca en dos grandes matrices:

Fase 3A: Matriz de Seguimiento a Derechos Colectivos (Uso Común)  
Como las tierras de uso común son de todos, la PA debe recabar información técnica específica de esa área común: Destino de la Superficie y, si aplica para un área comunal específica, el No. de Parcela/Solar. Todo debe ser autorizado por la Asamblea.  
1\. Convenio de Ocupación Previa (Original):

* Asamblea: La PA documenta el esfuerzo para lograr el quórum capturando Asamblea Programada 1ra (Fecha), Asamblea Programada 2da (Fecha) y la Asamblea Realizada (Fecha) donde se otorga la anuencia.  
* RAN (Acta): El acta de esa asamblea se ingresa al registro capturando: Ingresado al RAN (Fecha), Número de Solicitud de Ingreso, Calificación Registral y Acta Inscrita en el RAN (Fecha).  
* Firma y Montos: Se captura el Convenio Firmado (Fecha), la Superficie Total Real Afectada (Ha), y los montos del avalúo: Convenio Monto 90%, Convenio Monto 100% y Monto BDT (Bienes Distintos a la Tierra).  
* RAN (Convenio): El convenio también se inscribe en el RAN rastreando los mismos 4 campos: Ingresado al RAN (Fecha), Número de Solicitud de Ingreso, Calificación Registral y Convenio Inscrito en el RAN (Fecha).

2\. Variantes de Convenios Colectivos (Nuevos ciclos): Si el proyecto sufre alteraciones, la matriz detalla sub-procesos específicos. Cada uno (excepto el modificatorio) requiere detonar de nuevo los campos de Sensibilización, Caminamiento, Asamblea, Firmas e Inscripción al RAN:

* Convenio Modificatorio: Solo se capturan los ajustes al acuerdo inicial: Convenio Modificatorio Firmado (Fecha), los montos (90%, 100%, Monto BDT) y la Superficie Total Real Afectada (Ha), junto con sus respectivos campos de ingreso e inscripción al RAN.  
* Convenio Superficie Adicional: Se reinicia el ciclo de asamblea y RAN. Se captura el Convenio Sup. Adicional Firmado (Fecha), los montos (90%, 100%, BDT) y la Superficie Adicional (Ha).  
* Convenio Obras Complementarias: Repite el ciclo pero usando campos con nomenclatura diferenciada para evitar duplicidades en el sistema: Asamblea 1ra Convocatoria (Fecha), Asamblea 2da Convocatoria (Fecha), Ingresado al RAN (Fecha) 2, Número de Solicitud de Ingreso 2\. Se captura el Convenio Firmado (Fecha), montos (90%, 100%) y la Superficie Total Real Afectada (Ha). (Nota: En esta variante no se captura Monto BDT).

Fase 3B: Matriz de Seguimiento a Derechos Individuales (Parcelas)  
Como las parcelas tienen un dueño asignado, no interviene la asamblea. Tras el caminamiento, la PA crea un expediente privado.

1\. Datos Generales de la Parcela: Para validar que el trato es con la persona correcta, la PA captura: Tipo de Parcela (Individual), No. de Parcela PPT, Nombre de la Persona Titular de la Parcela, Constancia de Vigencia de Derechos (Fecha), el Certificado Parcelario y el Folio de Derechos.

2\. Convenio de Ocupación Previa Individual (y sus variantes): Tras negociar en privado, se recaban los datos del acuerdo, los cuales tienen ligeras variaciones a lo colectivo:

* COP Original: Se captura Convenio Firmado (Fecha), montos (Convenio Monto 90%, Convenio Monto 100%, Monto BDT) y la Superficie Total (Ha.). Se inscribe rastreando: Convenio Ingresado al RAN (Fecha), No. de Solicitud de Ingreso, Calificación Registral y Convenio Inscrito en el RAN (Fecha).  
* Convenio Modificatorio: A diferencia de otros, el modificatorio individual solo requiere tres datos: Convenio Modificatorio (Fecha), Convenio Monto 90% y Convenio Monto 100%.  
* Convenio Ampliación y Convenio Ampliación \- Remanente: Se utilizan cuando hay cambios en la afectación de la parcela. En ambos se captura el Convenio Ampliación (Fecha), los tres montos (90%, 100%, Monto BDT), la Superficie de Ampliación, y los cuatro campos del trámite de inscripción ante el RAN.

Fase 4: Matriz de FIFONAFE, Informes de No Conflictos y Cierres  
Antes de que la indemnización sea pagada, el FIFONAFE (que administra los recursos) exige a la PA garantizar la paz social. Esto detona una matriz exclusiva de control de pagos y oficios.

1\. Informe de No Conflictos (Cruces de oficios para ambas vías): Se rastrea toda la cadena de comunicación interinstitucional rellenando rigurosamente:

* No. de Oficio FIFONAFE a DGAOPR/Representación y Fecha: El FIFONAFE pregunta si se puede pagar.  
* No. de Oficio DGAOPR a Representación y Fecha: La SEDATU solicita a la PA que revise la zona.  
* Respuesta Representación a DGAOPR No. de Oficio y Fecha: La PA valida que no hay conflictos sociales o legales.  
* Respuesta DGAOPR/Representación a FIFONAFE No. de Oficio y Fecha: Se le da luz verde definitiva al fideicomiso.

2\. El Cierre y Dispersión de Fondos: Una vez que los oficios fluyen, el dinero se mueve:

* Para Derechos Individuales, el FIFONAFE paga directamente a la persona. El proceso culmina actualizando el campo Indemnización: Estatus (Completo, Pendiente, Programado).  
* Para Derechos Colectivos, como el dinero va a un fondo común, el campo Indemnización: Estatus (Completo, Pendiente, Programado) marca el depósito general, pero la comunidad aún no puede usarlo. La PA debe organizar una reunión final para decidir el reparto, llenando el campo Asamblea Retiro de Fondos: Estatus (Completo, Pendiente, Programado).

De esta forma, cada uno de los datos del archivo Estructura Datos.md cumple una función específica, cronológica y auditable dentro del gran engranaje de liberación de tierras.

**Introducción agraria básica.**  
Artículo 27 Constitucional: Establece que la Nación es dueña originaria de las tierras y regula la propiedad ejidal y comunal, prohibiendo los latifundios y facultando al Estado para expropiar tierras por utilidad pública.  
Las reformas de 1992 finalizaron el reparto agrario, permitieron la conversión de ejidos en propiedad privada para el mercado y crearon instituciones como la Procuraduría Agraria (PA) y los Tribunales Agrarios.

Instancias del Sector Agrario: El sector está conformado por la SEDATU (encargada del desarrollo territorial), la Procuraduría Agraria (defiende los derechos de los sujetos agrarios), el Registro Agrario Nacional o RAN (controla la tenencia de la tierra y la seguridad documental) y el FIFONAFE (administra los fondos comunes de los núcleos agrarios).

Los Núcleos Agrarios: Engloban a los ejidos y comunidades; cuentan con personalidad jurídica y patrimonio propio, y son los propietarios de las tierras que se les dotaron.

Los Órganos del Núcleo Agrario: La Asamblea es el órgano supremo de decisión (puede ser de formalidades simples o especiales).  
El Comisariado Ejidal / de Bienes Comunales ejecuta los acuerdos de la asamblea y representa al núcleo; mientras que el Consejo de Vigilancia se encarga de supervisar las acciones del Comisariado.  
Estos órganos de representación duran 3 años.

Los Sujetos Agrarios: Se clasifican en Ejidatarios (titulares de derechos en ejidos), Comuneros (titulares en comunidades agrarias), Avecindados (personas reconocidas con más de un año de residencia) y Posesionarios (poseen terrenos sin ser forzosamente ejidatarios o avecindados).

Tipos de tierras: También conocidas como "Grandes Áreas", se dividen en: Tierras de uso común (sustento inalienable y económico de la comunidad), Área parcelada (tierras destinadas al cultivo de manera individual) y Área de Asentamientos Humanos (necesarias para la vida comunitaria y la urbanización).

Acciones agrarias: Son procesos que alteran la geografía o tenencia del núcleo. Pueden sumar superficie (dotación, ITRE, ampliación), restar superficie (dominio pleno, división de ejido, expropiación, titulación de asentamientos) o no afectar la superficie (certificaciones como PROCEDE o reversiones).

De la Expropiación de Bienes Ejidales y Comunales: Trámite ante la SEDATU fundamentado en el artículo 93 por causas de utilidad pública (ej. vías de transporte). Debe realizarse mediante un decreto presidencial publicado en el Diario Oficial, y a cambio se otorga una indemnización.

REGLAMENTO DE LA LEY AGRARIA EN MATERIA DE ORDENAMIENTO DE LA PROPIEDAD RURAL: Estipula que durante o antes del procedimiento expropiatorio, se pueden celebrar convenios de ocupación previa para usar las tierras.  
Además, define los requisitos formales (Art. 57 y Art. 61\) para suscribir el convenio y solicitar la expropiación mediante escrito libre.

**CONVENIOS DE OCUPACIÓN PREVIA Y EL PROCEDIMIENTO DE EXPROPIACIÓN**  
Introducción: La expropiación es la forma en que el Estado adquiere bienes por utilidad pública con indemnización. Los convenios de ocupación previa permiten al Estado ocupar dichas tierras agrarias antes de que concluya ese proceso legal de expropiación.

Marco Jurídico: Sustentado en el Art. 27 Constitucional, los artículos 93 al 96 de la Ley Agraria (que hablan de causas de utilidad pública y avalúos) y el Título Tercero del Reglamento de la Ley Agraria en Materia de Ordenamiento de la Propiedad Rural.

Convenio de Ocupación Previa: Es un acuerdo formal donde el núcleo agrario (o el titular parcelario) da permiso a un promovente para ocupar temporalmente las tierras mientras se tramita o en su defecto se cancela el proceso expropiatorio.

Contenido de un Convenio de Ocupación Previa: Legalmente debe incluir la superficie y ubicación geográfica, si es gratuito u oneroso (con monto y garantía de pago), vigencia, compromiso de iniciar la expropiación y el proceso para pago de daños en caso de cancelación.

Estructura de un Convenio de Ocupación Previa: Se compone de un Proemio (partes y tipo de convenio), Declaraciones (datos de la parcela y organización promovente), Cláusulas (que definen forma de pago, uso para utilidad pública, obligaciones, plazo máximo de 3 años ante SEDATU, daños a la naturaleza, etc.) y la firma de los involucrados.

Convenio de Ocupación Previa (Derechos colectivos): Cuando se afectan tierras de uso común, se requiere realizar asambleas de información y de anuencia para autorizar al Comisariado a firmar. El monto pactado se deposita en el FIFONAFE, requiriendo otra asamblea para el retiro de los fondos.

Convenio de Ocupación Previa (Derechos individuales): Para la afectación de parcelas, se sensibiliza al titular, se redacta el convenio y la firma se realiza directamente con la persona afectada, tras lo cual se inscribe en el RAN.

Proceso de Expropiación con un Convenio de Ocupación Previa: Facilita el inicio de los trabajos operativos. El flujo es: Formalización del convenio de ocupación \-\> Desarrollo de las obras \-\> Inicio del proceso de expropiación \-\> Ejecución de la expropiación.

Proceso de Expropiación sin un Convenio de Ocupación Previa: Las obras no pueden iniciar sino hasta el final del proceso legal. El flujo es: Inicio del proceso de expropiación \-\> Ejecución de la expropiación \-\> Desarrollo de las obras.

Procedimiento de Expropiación: Consta de varios pasos formales: Solicitud, verificación de utilidad pública, notificación, instauración, trabajos técnicos, avalúo oficial, publicación del decreto, notificación, pago individual o colectivo (a través de FIFONAFE) y, por último, la ejecución del decreto.

**Conceptos**  
tramo: Representa cada uno de los tramos principales que conforman el proyecto ferroviario. Constituye la unidad geográfica y operativa de mayor nivel dentro del sistema, para el seguimiento del derecho de vía.  
núcleo agrario: Es la entidad central del sistema. Representa cada ejido o comunidad agraria que es atravesado o afectado por el proyecto ferroviario,. Alrededor del cual se articula Todo el seguimiento de derechos colectivos, e individuales, convenios, asambleas, afectaciones  y documentación relacionada con el derecho de vía.  
entidad\_federativa: Estado de la República al que se encuentra adscrito registralmente el núcleo agrario para fines de identificación y seguimiento dentro del sistema. Puede diferir de la localización geográfica.  
municipio: Municipio al que se encuentra adscrito registralmente el núcleo agrario para fines de identificación y seguimiento dentro del sistema. Puede diferir de la localización geográfica.  
residencia: Oficina o Unidad administrativa regional de la Procuraduría Agraria encargada de la atención y seguimiento al núcleo agrario dentro del proyecto.  
nombre\_nucleo: Nombre oficial del ejido o comunidad conforme a sus asientos registrales. Verificable en el PHINA  
anuencia: Indica si el núcleo agrario ha otorgado su anuencia para el desarrollo del proyecto (sí/no).  
es\_expropiacion: Indica si el procedimiento correspondiente se lleva a cabo mediante  expropiación directa,  derivado de la falta de celebración de un convenio.  
geometria\_poligono: Es muy importante definir el sistema de coordenadas de entrada, para garantizar la entrada de información conforme a los distintos productos cartográficos. Considerar que la mayoría de usuarios y mapas base trabajan con coordenadas geográficas basadas en  WGS84; en tanto los documentos jurídicos utilizados en la liberación utilizan coordenadas UTM. En su caso, debe vigilarse la correcta zonificación y características específicas del SRC  
afectación: Registra la superficie, tipo de tenencia propiedad y personas o/parcelas afectadas por el paso del tramo ferroviario dentro de un núcleo agrario, considerando derechos colectivos, individuales y tierras de uso común sujetas al régimen de propiedad social.  
tipo\_tenencia: Indica la modalidad de tenencia de la superficie afectada dentro del núcleo agrario, como tierra parcelada individual, parcelada colectiva o de uso común.  
subtipo\_tenencia: Clasificación específica: individual, copropiedad, infraestructura, parcela no asignada, parcela con destino específico, tierra no registrada, etc.  
sensibilización: Registra las reuniones de sensibilización realizadas con el núcleo agrario, en las que se informa sobre el derecho de vía y el proyecto ferroviario, con el objetivo de generar entendimiento y disposición respecto al mismo.  
fecha\_reunion\_programada: Fecha programada para la realización de la reunión.  
fecha\_reunion\_realizada: Fecha de realización de la reunión.  
caminamiento: Registro de recorridos técnicos en campo  para la verificación topográfica del trazo ferroviario y la delimitación de posibles afectaciones en el territorio del núcleo agrario  
asamblea: Registra las asambleas ejidales o comunales del núcleo agrario en el marco del proceso de autorización del proyecto y obtención de la anuencia. incluyendo primera convocatoria, segunda convocatoria y asamblea realizada.  
Fecha\_exp\_1a: Fecha de expedición de la primera convocatoria para la realización de la asamblea, conforme al art. 26 de la Ley Agraria.  
Fecha\_prog\_1a: Fecha en que se espera desahogar la asamblea por primera convocatoria, conforme al art. 26 de la Ley Agraria.  
Fecha\_exp\_2a: Fecha de expedición de la segunda convocatoria para la realización de la asamblea, conforme al art. 26 de la Ley Agraria.  
Fecha\_prog\_2a: Fecha en que se espera desahogar la asamblea por segunda convocatoria, conforme al art. 26 de la Ley Agraria.  
Tipo de convenio: COP (Convenio de Ocupación Previa): Original, modificatorio, superficie adicional u obras complementarias.  
convenio\_monto\_90: Monto pactado equivalente al 90% del valor del convenio. En ocasiones no aplica, depende del acuerdo con el núcleo agrario.  
convenio\_monto\_100: Monto pactado equivalente al 100% del valor del convenio.  
monto\_bdt: Monto correspondiente a la indemnización de Bienes Distintos a la Tierra.  
