# Cambios Aplicados - Corrección de Inconsistencias

**Fecha**: 2026-06-16  
**Archivos Modificados**: `design-mod.md`  
**Documento de Análisis**: `ANALISIS_INCONSISTENCIAS.md`

---

## Resumen de Cambios

Se aplicaron **5 correcciones críticas** al archivo `design-mod.md` para alinear el diseño técnico con el proceso descrito en `Descripción proceso.md` (fuente de verdad).

---

## ✅ Cambios Aplicados

### 1. ✅ Corrección de Nomenclatura: 'COP' → 'cop_original'

**Problema**: El CHECK constraint usaba 'COP' (mayúsculas) que no coincidía con el valor del enum que debía ser 'cop_original'

**Solución Aplicada**:
```sql
-- ANTES
tipo_convenio VARCHAR(50) NOT NULL CHECK (tipo_convenio IN (
    'COP', 'modificatorio', ...
))

-- DESPUÉS  
tipo_convenio VARCHAR(50) NOT NULL CHECK (tipo_convenio IN (
    'cop_original', 'modificatorio', ...
))
```

**Ubicación**: Tabla `convenio`, línea ~767

**Impacto**: CRÍTICO - Sin esta corrección, todas las validaciones de tipo_convenio fallarían porque 'COP' no era un valor válido.

---

### 2. ✅ Constraint: Validación de Tipo de Convenio por Afectación

**Problema**: El constraint `chk_tipo_convenio_por_afectacion` usaba el valor incorrecto 'COP' en lugar de 'cop_original'

**Solución Aplicada**:
```sql
CONSTRAINT chk_tipo_convenio_por_afectacion CHECK (
    (tipo_afectacion = 'colectivo' AND tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'))
    OR
    (tipo_afectacion = 'individual' AND tipo_convenio IN ('cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'))
)
```

**Ubicación**: Tabla `convenio`, después de foreign keys

**Fuente de Verdad**: `Descripción proceso.md`, líneas 35-39

**Impacto**: CRÍTICO - Previene crear convenios inconsistentes (ej. "Ampliación" en afectación colectiva)

---

### 3. ✅ Constraint: Obras Complementarias NO Captura monto_bdt

**Problema**: El diseño permitía capturar `monto_bdt` para convenios de tipo 'obras_complementarias', pero el proceso explícitamente indica que NO se captura

**Solución Aplicada**:
```sql
-- Nueva regla agregada
CONSTRAINT chk_bdt_no_obras_complementarias CHECK (
    (tipo_convenio = 'obras_complementarias' AND monto_bdt IS NULL)
    OR
    (tipo_convenio != 'obras_complementarias')
)
```

**Ubicación**: Tabla `convenio`, después de `chk_tipo_convenio_por_afectacion`

**Fuente de Verdad**: `Descripción proceso.md`, línea 48:
> "(Nota: En esta variante no se captura Monto BDT)."

**Impacto**: ALTO - Previene captura de datos que no deben existir según el proceso real

---

### 4. ✅ Constraint: Modificatorio Individual Sin Superficie ni BDT

**Problema**: El diseño permitía capturar superficie y BDT para modificatorio individual, pero el proceso indica que solo requiere 3 campos: fecha, monto_90, monto_100

**Solución Aplicada**:
```sql
-- Nueva regla agregada
CONSTRAINT chk_modificatorio_individual_sin_superficie CHECK (
    NOT (tipo_convenio = 'modificatorio' 
         AND tipo_afectacion = 'individual' 
         AND (superficie_total_ha IS NOT NULL 
              OR superficie_real_afectada_ha IS NOT NULL 
              OR superficie_adicional_ha IS NOT NULL
              OR monto_bdt IS NOT NULL))
)
```

**Ubicación**: Tabla `convenio`, después de `chk_bdt_no_obras_complementarias`

**Fuente de Verdad**: `Descripción proceso.md`, línea 59:
> "el modificatorio individual solo requiere tres datos: Convenio Modificatorio (Fecha), Convenio Monto 90% y Convenio Monto 100%."

**Impacto**: ALTO - Evita captura de datos innecesarios que no aplican al flujo simplificado de modificatorio individual

**Nota**: Esta regla NO aplica a modificatorios colectivos

---

### 5. ✅ Nueva Vista: vw_convenio_estado

**Problema**: No había forma de trackear el estado del workflow del convenio (borrador, firmado, ingresado RAN, inscrito RAN)

**Solución Aplicada**:
```sql
CREATE OR REPLACE VIEW vw_convenio_estado AS
SELECT 
    c.*,
    CASE 
        WHEN c.convenio_inscrito_fecha_ran IS NOT NULL THEN 'inscrito_ran'
        WHEN c.ingreso_ran_fecha IS NOT NULL THEN 'ingresado_ran'
        WHEN c.fecha_firma IS NOT NULL THEN 'firmado'
        ELSE 'borrador'
    END AS estado_calculado,
    (c.convenio_inscrito_fecha_ran IS NOT NULL) AS esta_inscrito_ran,
    (c.fecha_firma IS NOT NULL) AS esta_firmado
FROM convenio c;
```

**Ubicación**: Sección "Vistas de Base de Datos", antes de `vw_tramo_nucleo_estado`

**Justificación**: Campo calculado en lugar de campo explícito para mantener las fechas como fuente de verdad y evitar inconsistencias por falta de sincronización

**Impacto**: MEDIO - Facilita reportes y validaciones de flujo sin modificar estructura de tabla

---

### 6. ✅ Nueva Sección: Reglas de Negocio Implementadas en Base de Datos

**Problema**: Los constraints existían pero no había documentación clara de su propósito, fuente de verdad y justificación

**Solución Aplicada**: Agregada nueva sección completa que documenta:
- RN-1: Validación de Tipo de Convenio por Tipo de Afectación
- RN-2: Obras Complementarias NO Captura Monto BDT
- RN-3: Modificatorio Individual - Restricción de Campos
- Decisiones de Diseño:
  - Nomenclatura snake_case
  - Estado calculado mediante vista
  - Estrategia para campos RAN duplicados

**Ubicación**: Nueva sección antes de "Correctness Properties"

**Impacto**: MEDIO - Mejora documentación y facilita mantenimiento futuro

---

## 📊 Estadísticas de Cambios

| Métrica | Valor |
|---------|-------|
| Archivos modificados | 1 (`design-mod.md`) |
| Constraints agregados | 2 (chk_bdt_no_obras_complementarias, chk_modificatorio_individual_sin_superficie) |
| Constraints corregidos | 2 (tipo_convenio enum, chk_tipo_convenio_por_afectacion) |
| Vistas agregadas | 1 (vw_convenio_estado) |
| Secciones de documentación agregadas | 1 (Reglas de Negocio) |
| Líneas de código SQL agregadas | ~150 |

---

## 🔍 Validación de Cambios

### Tests de Validación Sugeridos

Una vez implementado el schema actualizado, ejecutar estos tests:

```sql
-- Test 1: Validar que 'COP' ya no es aceptado (debe fallar)
INSERT INTO convenio (id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_convenio, fecha_firma)
VALUES (1, 1, 'colectivo', 'COP', '2026-01-01');
-- Esperado: ERROR violación de CHECK constraint

-- Test 2: Validar que 'cop_original' es aceptado (debe pasar)
INSERT INTO convenio (id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_convenio, fecha_firma)
VALUES (1, 1, 'colectivo', 'cop_original', '2026-01-01');
-- Esperado: SUCCESS

-- Test 3: Validar que obras_complementarias con monto_bdt falla
INSERT INTO convenio (id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_convenio, fecha_firma, monto_bdt)
VALUES (1, 2, 'colectivo', 'obras_complementarias', '2026-01-01', 50000);
-- Esperado: ERROR violación de chk_bdt_no_obras_complementarias

-- Test 4: Validar que obras_complementarias sin monto_bdt pasa
INSERT INTO convenio (id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_convenio, fecha_firma, monto_90, monto_100)
VALUES (1, 2, 'colectivo', 'obras_complementarias', '2026-01-01', 90000, 100000);
-- Esperado: SUCCESS

-- Test 5: Validar que modificatorio individual con superficie falla
INSERT INTO convenio (id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_convenio, fecha_firma, superficie_total_ha)
VALUES (1, 3, 'individual', 'modificatorio', '2026-01-01', 2.5);
-- Esperado: ERROR violación de chk_modificatorio_individual_sin_superficie

-- Test 6: Validar que modificatorio individual solo con montos pasa
INSERT INTO convenio (id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_convenio, fecha_firma, monto_90, monto_100)
VALUES (1, 3, 'individual', 'modificatorio', '2026-01-01', 45000, 50000);
-- Esperado: SUCCESS

-- Test 7: Validar vista vw_convenio_estado calcula correctamente
SELECT id_convenio, tipo_convenio, fecha_firma, ingreso_ran_fecha, convenio_inscrito_fecha_ran, estado_calculado
FROM vw_convenio_estado
ORDER BY id_convenio;
-- Esperado: Columna estado_calculado muestra 'borrador', 'firmado', 'ingresado_ran', o 'inscrito_ran' según fechas

-- Test 8: Validar que ampliacion en afectación colectiva falla
INSERT INTO convenio (id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_convenio, fecha_firma)
VALUES (1, 4, 'colectivo', 'ampliacion', '2026-01-01');
-- Esperado: ERROR violación de chk_tipo_convenio_por_afectacion
```

---

## ⚠️ Temas Validados con Stakeholder - RESUELTOS ✅

### 1. ✅ Campos RAN Duplicados para Obras Complementarias - IMPLEMENTADO

**Decisión del Stakeholder (Procuraduría Agraria)**:
> "Al ser una nueva ocupación en tierras de uso común, la ley exige detonar de nuevo todo el ciclo [...] el sistema utiliza los campos Ingresado al RAN (Fecha) 2 y Número de Solicitud de Ingreso 2 como una nomenclatura diferenciada para evitar duplicidades en el sistema. Es decir, el '2' es solo un sufijo técnico para que las columnas de la base de datos no choquen con las columnas de la asamblea original del COP."

**Solución Implementada**:
- Agregados 4 campos a tabla `convenio`: `ingreso_ran_fecha_2`, `numero_solicitud_ingreso_2`, `calificacion_registral_2`, `acta_inscrita_fecha_ran_2`
- Constraint `chk_campos_ran_2_solo_obras_complementarias` valida que solo se usen para obras_complementarias
- Los campos "_2" se populan en la MISMA fila del convenio (no fila separada)

**Rationale**: Mantiene la práctica operativa actual donde ambos ciclos se documentan en el mismo expediente

---

### 2. ✅ Diferencia superficie_total_ha vs superficie_real_afectada_ha - DOCUMENTADO

**Respuesta del Stakeholder**:
> "La distinción principal es jurídica. Superficie Total Real Afectada (Ha) mide el impacto sobre las tierras inalienables que son de uso comunal y requieren asambleas, mientras que Superficie Total (Ha.) se captura en expedientes privados para medir la afectación de una parcela particular con un dueño específico."

**Solución Implementada**:
- `superficie_total_ha`: Para afectaciones INDIVIDUALES (parcelas con dueño)
- `superficie_real_afectada_ha`: Para afectaciones COLECTIVAS (tierras de uso común)
- Constraint `chk_superficie_segun_tipo_afectacion` valida el uso correcto
- Definiciones agregadas al Glosario en requirements.md

**Rationale**: Refleja la distinción legal entre propiedad individual (enajenable) y colectiva (inalienable)

---

## 📁 Archivos Generados

1. **ANALISIS_INCONSISTENCIAS.md** - Documento de análisis completo con todas las inconsistencias detectadas
2. **CAMBIOS_APLICADOS.md** (este archivo) - Resumen de correcciones implementadas
3. **design-mod.md** (modificado) - Diseño técnico actualizado con constraints y vistas

---

## 🎯 Próximos Pasos

### Inmediatos
1. ✅ Revisar cambios aplicados en `design-mod.md`
2. ⏳ Validar con stakeholder los 2 temas pendientes
3. ⏳ Actualizar `requirements.md` si se requieren aclaraciones adicionales

### Antes de Implementación
1. ⏳ Ejecutar tests de validación SQL
2. ⏳ Crear script de migración si ya existe una BD en desarrollo
3. ⏳ Actualizar interfaces TypeScript en código fuente si difieren del diseño

### Durante Implementación
1. ⏳ Implementar validación adicional en capa de aplicación (defensa en profundidad)
2. ⏳ Crear mensajes de error amigables para usuarios cuando violen constraints
3. ⏳ Agregar tests unitarios que verifiquen reglas de negocio

---

## ✍️ Resumen para el Usuario

Se completó el análisis de consistencia y se aplicaron **5 correcciones críticas** al diseño técnico para alinearlo con el proceso descrito en `Descripción proceso.md`:

1. Corregida nomenclatura de 'COP' a 'cop_original' 
2. Agregado constraint: Obras Complementarias no puede tener monto_bdt
3. Agregado constraint: Modificatorio Individual no puede tener superficie ni bdt
4. Creada vista vw_convenio_estado para tracking de workflow
5. Documentadas todas las reglas de negocio con fuentes y justificaciones

Los cambios previenen captura de datos incorrectos y garantizan que el sistema implemente fielmente el proceso real de la Procuraduría Agraria.

**Archivos para revisar**:
- `ANALISIS_INCONSISTENCIAS.md` - Análisis completo
- `design-mod.md` - Diseño actualizado (buscar "Reglas de Negocio Implementadas")
