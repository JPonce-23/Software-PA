# Análisis de Inconsistencias - Sistema de Seguimiento de Liberación de Derechos

**Fecha de Análisis**: 2026-06-16  
**Documento Fuente de Verdad**: `Descripción proceso.md`  
**Documentos Analizados**: `requirements.md`, `design-mod.md`

---

## Resumen Ejecutivo

Se identificaron **6 inconsistencias críticas** entre el proceso descrito en `Descripción proceso.md` (fuente de verdad) y las especificaciones técnicas (`requirements.md` y `design-mod.md`). Estas inconsistencias bloquearían una implementación correcta y deben corregirse antes de proceder con el desarrollo.

---

## 🔴 PRIORIDAD ALTA - Bloquea Implementación

### 1. Falta Validación de Tipo de Convenio por Tipo de Afectación

**Ubicación**: `design-mod.md` - Tabla `convenio`  
**Estado Actual**: El CHECK constraint `chk_tipo_convenio_por_afectacion` existe PERO usa valores inconsistentes  
**Problema Detectado**:

La tabla `convenio` tiene esta restricción:
```sql
CONSTRAINT chk_tipo_convenio_por_afectacion CHECK (
    (tipo_afectacion = 'colectivo' AND tipo_convenio IN ('COP', 'modificatorio', 'superficie_adicional', 'obras_complementarias'))
    OR
    (tipo_afectacion = 'individual' AND tipo_convenio IN ('COP', 'modificatorio', 'ampliacion', 'ampliacion_remanente'))
)
```

**Problemas**:
1. Usa `'COP'` (mayúsculas) pero en CHECK de tipo_convenio está definido como `'cop_original'`
2. Mezcla nomenclatura: 'COP' vs 'modificatorio' (minúsculas)

**Lo que Dice el Proceso** (`Descripción proceso.md`, líneas 35-39):
> "Los tipos de convenio varían según el tipo de derecho afectado: para derechos colectivos incluye COP, Modificatorio, Superficie Adicional y Obras Complementarias; para derechos individuales incluye COP, Modificatorio, Ampliación y Ampliación Remanente."

**Corrección Requerida**:
```sql
-- Actualizar el CHECK de tipo_convenio
tipo_convenio VARCHAR(50) NOT NULL CHECK (tipo_convenio IN (
    'cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias',
    'ampliacion', 'ampliacion_remanente'
))

-- Actualizar el CHECK de validación compuesta
CONSTRAINT chk_tipo_convenio_por_afectacion CHECK (
    (tipo_afectacion = 'colectivo' AND tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'))
    OR
    (tipo_afectacion = 'individual' AND tipo_convenio IN ('cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'))
)
```

**Impacto**: CRÍTICO - Sin esta corrección, la validación fallaría siempre porque 'COP' no existe como valor válido en el enum.

---

### 2. Regla BDT para Obras Complementarias NO Implementada

**Ubicación**: `design-mod.md` - Tabla `convenio`, campo `monto_bdt`  
**Estado Actual**: Campo `monto_bdt` permite valores para TODOS los tipos de convenio  
**Problema Detectado**: El proceso establece que Obras Complementarias NO captura monto BDT

**Lo que Dice el Proceso** (`Descripción proceso.md`, línea 48):
> "Se captura el Convenio Firmado (Fecha), montos (90%, 100%) y la Superficie Total Real Afectada (Ha). **(Nota: En esta variante no se captura Monto BDT)**."

**Corrección Requerida**:

**Opción 1 - Validación en Base de Datos (RECOMENDADO)**:
```sql
-- Agregar CHECK constraint que valida que obras_complementarias NO tenga monto_bdt
CONSTRAINT chk_bdt_no_obras_complementarias CHECK (
    (tipo_convenio = 'obras_complementarias' AND monto_bdt IS NULL)
    OR
    (tipo_convenio != 'obras_complementarias')
)
```

**Opción 2 - Validación en Capa de Aplicación**:
```typescript
// En el servicio de creación de convenios
if (convenio.tipo_convenio === 'obras_complementarias' && convenio.monto_bdt !== null) {
  throw new ValidationError('Obras Complementarias no puede tener monto BDT')
}
```

**Corrección en requirements.md**:
- Requirement 8, Criterio de Aceptación 3 ya menciona esta regla ✅
- Pero falta que el diseño técnico la implemente

**Impacto**: ALTO - Permitiría capturar datos incorrectos que no reflejan el proceso real.

---

### 3. Modificatorio Individual - Restricción de Campos NO Implementada

**Ubicación**: `design-mod.md` - Tabla `convenio`  
**Estado Actual**: Todos los campos de superficie son opcionales para todos los tipos  
**Problema Detectado**: Modificatorio Individual solo debe requerir 3 campos, pero el schema no lo valida

**Lo que Dice el Proceso** (`Descripción proceso.md`, línea 59):
> "**Convenio Modificatorio**: A diferencia de otros, el modificatorio individual solo requiere tres datos: Convenio Modificatorio (Fecha), Convenio Monto 90% y Convenio Monto 100%."

**Análisis**:
- Modificatorio Individual NO debe capturar: `superficie_*`, `monto_bdt`
- Modificatorio Colectivo SÍ captura superficie y BDT

**Corrección Requerida**:

**En Base de Datos**:
```sql
-- Agregar CHECK constraint para modificatorio individual
CONSTRAINT chk_modificatorio_individual_sin_superficie CHECK (
    NOT (tipo_convenio = 'modificatorio' 
         AND tipo_afectacion = 'individual' 
         AND (superficie_total_ha IS NOT NULL 
              OR superficie_real_afectada_ha IS NOT NULL 
              OR superficie_adicional_ha IS NOT NULL
              OR monto_bdt IS NOT NULL))
)
```

**En requirements.md**:
- Requirement 8, Criterio de Aceptación 4 ya menciona esta regla ✅
- Necesita implementarse en design-mod.md

**Impacto**: ALTO - Permitiría capturar datos que no tienen sentido en el proceso de modificatorio individual.

---

## 🟢 RESUELTO - Campos RAN Duplicados para Obras Complementarias

**Ubicación**: `design-mod.md` - Tabla `convenio`  
**Estado Actual**: ✅ IMPLEMENTADO - Campos duplicados con sufijo "_2"  
**Decisión Final del Stakeholder**: Los campos RAN "2" son campos adicionales en la MISMA fila

**Respuesta del Stakeholder (Procuraduría Agraria)**:
> "Al ser una nueva ocupación en tierras de uso común, la ley exige detonar de nuevo todo el ciclo: se requiere una nueva asamblea de anuencia, nuevas firmas y su propia inscripción al Registro Agrario Nacional (RAN). Como todos estos datos conviven dentro de la misma gran pestaña de 'Derechos Colectivos', el sistema utiliza los campos Ingresado al RAN (Fecha) 2 y Número de Solicitud de Ingreso 2 como una nomenclatura diferenciada para evitar duplicidades en el sistema."

**Solución Implementada**:
```sql
-- Campos agregados a tabla convenio
ingreso_ran_fecha_2 DATE,
numero_solicitud_ingreso_2 VARCHAR(100),
calificacion_registral_2 TEXT,
acta_inscrita_fecha_ran_2 DATE,

-- Constraint que valida uso exclusivo para obras_complementarias
CONSTRAINT chk_campos_ran_2_solo_obras_complementarias CHECK (
    (tipo_convenio = 'obras_complementarias')
    OR
    (tipo_convenio != 'obras_complementarias' 
     AND ingreso_ran_fecha_2 IS NULL 
     AND numero_solicitud_ingreso_2 IS NULL 
     AND calificacion_registral_2 IS NULL 
     AND acta_inscrita_fecha_ran_2 IS NULL)
)
```

**Justificación**:
- Mantiene la lógica operativa actual (mismo expediente, misma fila)
- Facilita migración desde Excel existente
- El "2" es simplemente un sufijo técnico para evitar colisiones
- Permite ver el ciclo completo de Obras Complementarias en una consulta

**Impacto**: RESUELTO - El diseño ahora refleja fielmente la práctica operativa

---

## 🟢 RESUELTO - Diferencia entre superficie_total_ha y superficie_real_afectada_ha

**Ubicación**: `requirements.md` - Glosario  
**Estado Actual**: ✅ DOCUMENTADO - Diferencia jurídica clara  

**Respuesta del Stakeholder**:
> "La distinción principal es jurídica. Superficie Total Real Afectada (Ha) mide el impacto sobre las tierras inalienables que son de uso comunal y requieren asambleas, mientras que Superficie Total (Ha.) se captura en expedientes privados para medir la afectación de una parcela particular con un dueño específico."

**Solución Implementada**:

**Definiciones en Glosario**:
- **`superficie_total_ha`**: Para afectaciones INDIVIDUALES (parcelas con dueño específico)
- **`superficie_real_afectada_ha`**: Para afectaciones COLECTIVAS (tierras de uso común inalienables)

**Constraint de Validación**:
```sql
CONSTRAINT chk_superficie_segun_tipo_afectacion CHECK (
    (tipo_afectacion = 'individual' AND superficie_real_afectada_ha IS NULL)
    OR
    (tipo_afectacion = 'colectivo' AND superficie_total_ha IS NULL)
    OR
    (tipo_afectacion = 'individual' AND tipo_convenio = 'modificatorio')
)
```

**Justificación**:
- Refleja la diferencia legal entre propiedad individual y colectiva
- Las tierras de uso común son inalienables (no se pueden vender)
- Las parcelas individuales tienen titular y pueden enajenarse
- Previene usar el campo incorrecto según el tipo de derecho

**Impacto**: RESUELTO - Clara distinción jurídica implementada y documentada

---

**Ubicación**: `design-mod.md` - Múltiples tablas  
**Estado Actual**: Mezcla de mayúsculas/minúsculas y formatos  
**Problema Detectado**: 'COP' (mayúsculas) vs 'modificatorio' (minúsculas), falta consistencia

**Ejemplos Encontrados**:
- CHECK constraint usa `'COP'` 
- Otros tipos usan minúsculas: `'modificatorio'`, `'superficie_adicional'`
- El proceso usa títulos capitalizados: "COP Original", "Modificatorio"

**Corrección Requerida**:
**Estandarizar a snake_case en minúsculas** (convención SQL/PostgreSQL):
```sql
tipo_convenio IN (
    'cop_original',           -- Antes: 'COP'
    'modificatorio',          -- OK
    'superficie_adicional',   -- OK
    'obras_complementarias',  -- OK
    'ampliacion',             -- OK
    'ampliacion_remanente'    -- OK
)
```

**Actualizar en**:
- Tabla `convenio` - CHECK constraint de `tipo_convenio`
- Tabla `convenio` - CHECK constraint `chk_tipo_convenio_por_afectacion`
- Interfaces TypeScript en sección "Components and Interfaces"
- Glosario en `requirements.md` (usar snake_case como valor técnico, mantener título legible en descripción)

**Impacto**: MEDIO - Mejora mantenibilidad y previene errores de tipeo.

---

### 6. Falta Campo de Estado/Estatus en Tabla `convenio`

**Ubicación**: `design-mod.md` - Tabla `convenio`  
**Estado Actual**: No existe campo `estatus` o `estado_convenio`  
**Problema Detectado**: No hay forma de trackear el estado del flujo de trabajo del convenio

**Análisis**:
El proceso describe un flujo claro:
1. **Borrador**: Convenio en negociación, sin firma
2. **Firmado**: Convenio firmado (`fecha_firma` poblada)
3. **Ingresado al RAN**: Enviado al RAN (`ingreso_ran_fecha` poblada)
4. **Inscrito en RAN**: Registrado oficialmente (`convenio_inscrito_fecha_ran` poblada)

**Corrección Requerida**:

**Opción A - Campo Calculado (Vista)** (RECOMENDADO):
```sql
-- Crear vista que calcula el estado basado en fechas existentes
CREATE OR REPLACE VIEW vw_convenio_estado AS
SELECT 
    c.*,
    CASE 
        WHEN c.convenio_inscrito_fecha_ran IS NOT NULL THEN 'inscrito_ran'
        WHEN c.ingreso_ran_fecha IS NOT NULL THEN 'ingresado_ran'
        WHEN c.fecha_firma IS NOT NULL THEN 'firmado'
        ELSE 'borrador'
    END AS estado_calculado
FROM convenio c;
```

**Opción B - Campo Explícito**:
```sql
-- Agregar campo de estado con CHECK
ALTER TABLE convenio ADD COLUMN estatus VARCHAR(30) 
    DEFAULT 'borrador' 
    CHECK (estatus IN ('borrador', 'firmado', 'ingresado_ran', 'inscrito_ran'));

-- Trigger para mantener sincronización
CREATE OR REPLACE FUNCTION sync_convenio_estatus()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.convenio_inscrito_fecha_ran IS NOT NULL THEN
        NEW.estatus := 'inscrito_ran';
    ELSIF NEW.ingreso_ran_fecha IS NOT NULL THEN
        NEW.estatus := 'ingresado_ran';
    ELSIF NEW.fecha_firma IS NOT NULL THEN
        NEW.estatus := 'firmado';
    ELSE
        NEW.estatus := 'borrador';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_convenio_estatus 
    BEFORE INSERT OR UPDATE ON convenio
    FOR EACH ROW EXECUTE FUNCTION sync_convenio_estatus();
```

**Recomendación**: Opción A (campo calculado) para evitar redundancia y mantener las fechas como fuente de verdad.

**Impacto**: MEDIO - Facilitaría reportes y validaciones de flujo, pero puede derivarse de campos existentes.

---

## 🟢 PRIORIDAD BAJA - Mejoras Futuras

### 7. Clarificación del Glosario: `superficie_total_ha` vs `superficie_real_afectada_ha`

**Ubicación**: `requirements.md` - Glosario  
**Estado Actual**: No está claro cuál es la diferencia entre ambos campos  
**Problema Detectado**: Ambos campos existen en tabla `convenio` pero sin explicación clara

**Pregunta para Stakeholder**:
> ¿Cuál es la diferencia conceptual entre `superficie_total_ha` y `superficie_real_afectada_ha`?

**Hipótesis**:
- `superficie_total_ha`: Superficie documentada en documentos iniciales o estimada
- `superficie_real_afectada_ha`: Superficie medida en campo después del caminamiento

**Corrección Sugerida**: Agregar definiciones claras en Glosario de requirements.md

---

## 📋 Resumen de Acciones Requeridas

### Correcciones Inmediatas (Antes de Implementación)

| # | Acción | Archivo | Prioridad |
|---|--------|---------|-----------|
| 1 | Corregir CHECK constraint `tipo_convenio` de 'COP' a 'cop_original' | `design-mod.md` | 🔴 ALTA |
| 2 | Agregar CHECK constraint para BDT en obras_complementarias | `design-mod.md` | 🔴 ALTA |
| 3 | Agregar CHECK constraint para modificatorio individual sin superficie | `design-mod.md` | 🔴 ALTA |
| 4 | Decidir estrategia para campos RAN duplicados (consultar stakeholder) | `design-mod.md` | 🟡 MEDIA |
| 5 | Estandarizar nomenclatura a snake_case | `design-mod.md`, interfaces | 🟡 MEDIA |
| 6 | Implementar vista `vw_convenio_estado` para tracking de estado | `design-mod.md` | 🟡 MEDIA |
| 7 | Clarificar diferencia superficie_total vs superficie_real en glosario | `requirements.md` | 🟢 BAJA |

### Documentación Adicional Necesaria

1. **TramoNucleo**: El proceso menciona que este es el "eje central" pero no hay documentación explícita de su rol
   - Sugerencia: Agregar sección en requirements.md explicando que TramoNucleo es la intersección geográfica que genera todo el seguimiento

2. **Flujo de Workflow Detallado**: Documentar el estado esperado en cada fase del proceso
   - Identificación → Sensibilización → Caminamiento → Asamblea → Convenio → RAN → FIFONAFE

---

## 🎯 Próximos Pasos

1. **Revisión con Stakeholder** (Procuraduría Agraria):
   - Confirmar interpretación de campos RAN duplicados para Obras Complementarias
   - Validar diferencia entre superficie_total_ha y superficie_real_afectada_ha
   
2. **Actualizar design-mod.md**:
   - Aplicar correcciones de PRIORIDAD ALTA (1, 2, 3)
   - Implementar mejoras de PRIORIDAD MEDIA (5, 6)

3. **Actualizar requirements.md**:
   - Verificar que Requirements 8 refleje todas las reglas de negocio
   - Agregar clarificaciones al Glosario

4. **Validación Final**:
   - Ejecutar script SQL actualizado para verificar que constraints funcionan
   - Crear casos de prueba para cada regla de validación

---

## Apéndice: Referencias al Documento Fuente

**Archivo**: `Descripción proceso.md`

| Línea(s) | Concepto | Relevancia |
|----------|----------|------------|
| 35-39 | Tipos de convenio por afectación | Define regla de validación crítica |
| 48 | BDT no aplica a Obras Complementarias | Regla de negocio específica |
| 47 | Campos RAN "2" para Obras Complementarias | Potencial necesidad de duplicar campos |
| 59 | Modificatorio Individual simplificado | Restricción de campos específica |
| 28-62 | Matriz Colectivos vs Individuales | Bifurcación del proceso |

---

**Analista**: Kiro (AI Assistant)  
**Revisión Pendiente**: Stakeholder de Procuraduría Agraria  
**Estado**: Borrador para Revisión
