# PROMPT 3C — CORREGIR UNA IMPLEMENTACIÓN RECHAZADA O INCOMPLETA

Usa este prompt cuando la auditoría encuentre defectos.

Actúa como arquitecto y desarrollador full-stack senior.

La auditoría independiente detectó defectos en la implementación.

## Tarea exacta

1. Lee `ESTADO_PROYECTO.md`.
2. Revisa el reporte completo de auditoría.
3. Extrae los hallazgos críticos, altos y medios.
4. Verifica cada hallazgo directamente en el código.
5. Clasifica cada uno como:

   * confirmado;
   * falso positivo;
   * ya corregido;
   * requiere decisión funcional;
   * no verificable.
6. Para cada defecto confirmado:

   * agrega una prueba que lo reproduzca cuando sea viable;
   * aplica la corrección mínima necesaria;
   * ejecuta la prueba específica;
   * revisa el diff.
7. Prioriza:

   * integridad;
   * seguridad;
   * autorización;
   * migraciones;
   * atomicidad;
   * concurrencia;
   * lógica funcional;
   * API;
   * frontend;
   * pruebas;
   * documentación.
8. Ejecuta la suite completa al finalizar.
9. Revisa nuevamente todos los gates.
10. Actualiza `ESTADO_PROYECTO.md` sólo con correcciones verificadas.
11. No hagas commit ni push.

## Restricciones

* No corrijas falsos positivos.
* No amplíes el alcance.
* No desactives pruebas.
* No relajes restricciones para hacer pasar datos.
* No resuelvas decisiones funcionales mediante inferencia.
* No ocultes pruebas fallidas.
* No elimines datos o volúmenes.

## Formato de salida

### Hallazgos procesados

| ID | Severidad | Confirmación | Acción | Estado |

### Cambios aplicados

| Archivo | Cambio | Hallazgo | Prueba |

### Validaciones

| Validación | Comando | Resultado |

### Gates

| Gate | Resultado | Evidencia |

### Riesgos restantes

### Veredicto

* Correcciones incompletas.
* Bloqueado por decisión funcional.
* Bloqueado por entorno.
* Listo para nueva auditoría.

Cuando el resultado sea “Listo para nueva auditoría”, vuelve a ejecutar el Prompt 3.

---
