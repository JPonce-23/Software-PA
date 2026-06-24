Quiero desarrollar un sistema web de seguimiento integral para un proyecto ferroviario operado por la Procuraduría Agraria, encargado de gestionar y monitorear la liberación de derechos de vía en zonas de propiedad social.

Históricamente, estos datos eran recopilados manualmente y centralizados en Excel. El objetivo de este sistema es digitalizar y modernizar este proceso mediante dos componentes principales: un **Dashboard/Reporteador** estadístico y un **Visor Geoespacial (Mapa Interactivo)**.

A través del sistema, nos interesa mostrar en tiempo real:
* Cuántos convenios individuales y de uso común (COP, modificatorios, obras complementarias, etc.) se han formalizado.
* El total de ejidos y comunidades afectadas (Núcleos Agrarios).
* Las superficies liberadas (en metros cuadrados y hectáreas) tanto para derechos individuales como de uso común.

**Visualización del Avance y Componente Geoespacial**
El avance general se reflejará a través de gráficos (principalmente circulares o de pastel) mostrando el porcentaje de superficie liberada frente a la afectada. Además, el sistema contará con un motor geoespacial que permitirá visualizar en un mapa interactivo la unidad geográfica y operativa del proyecto:
* **Tramos:** Los segmentos principales del proyecto ferroviario.
* **Frentes:** Subdivisiones operativas de cada tramo, las cuales mostrarán su progreso mediante códigos de color.
* **Polígonos Agrarios:** El sistema calculará automáticamente las intersecciones espaciales entre el paso del tren y las tierras de las comunidades.
* *(Nota: Las proporciones del trazo correspondientes a propiedad privada o terrenos nacionales se calcularán de manera dinámica por diferencia contra la longitud total del tramo, manteniendo la captura y el enfoque administrativo estrictamente en la propiedad social).*

**Seguimiento del Proceso Legal**
El sistema no solo arrojará métricas, sino que auditará el flujo agrario completo: desde el control de vigencia de las autoridades locales (ORV), las reuniones de sensibilización y asambleas, hasta la inscripción de actas en el Registro Agrario Nacional (RAN) y la cadena de oficios para el pago de indemnizaciones (FIFONAFE).

**Usuarios y Roles**
Para lograr esto, la plataforma soportará múltiples roles de usuario:
* **Operadores:** Encargados del llenado de información administrativa y legal.
* **Geógrafos:** Especialistas enfocados en la captura y validación de las geometrías y coordenadas cartográficas.
* **Visualizadores:** Usuarios finales o directivos que consumirán los tableros de control y el mapa para ver el avance del trabajo.
* **Administradores:** Encargados de la configuración y control de acceso.