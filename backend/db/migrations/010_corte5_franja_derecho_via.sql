BEGIN;

CREATE TABLE franja_derecho_via (
    id_franja SERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL,
    version INTEGER NOT NULL,
    ancho_izquierdo_m NUMERIC,
    ancho_derecho_m NUMERIC,
    geometria_poligono geometry(MULTIPOLYGON, 4326) NOT NULL,
    fuente VARCHAR(200) NOT NULL,
    fecha_vigencia_inicio DATE NOT NULL,
    fecha_vigencia_fin DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    -- Campos de auditoría (AuditableMixin)
    fecha_baja TIMESTAMP WITH TIME ZONE,
    id_usuario_baja INTEGER,
    motivo_baja VARCHAR,
    fecha_reactivacion TIMESTAMP WITH TIME ZONE,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion VARCHAR,
    observaciones VARCHAR,

    CONSTRAINT fk_franja_tramo FOREIGN KEY (id_tramo) REFERENCES tramo (id_tramo),
    CONSTRAINT chk_franja_anchos_positivos CHECK (
        (ancho_izquierdo_m IS NULL OR ancho_izquierdo_m > 0) AND
        (ancho_derecho_m IS NULL OR ancho_derecho_m > 0)
    ),
    CONSTRAINT chk_franja_vigencia CHECK (
        fecha_vigencia_fin IS NULL OR fecha_vigencia_inicio <= fecha_vigencia_fin
    )
);

-- Solo una franja activa por tramo a la vez
CREATE UNIQUE INDEX uq_tramo_franja_activa ON franja_derecho_via (id_tramo) WHERE activo = true;

-- Fase 1 de Migración/Compatibilidad: Crear versión 1 para cada tramo activo
-- usando el búfer implícito heredado.
INSERT INTO franja_derecho_via (
    id_tramo,
    version,
    ancho_izquierdo_m,
    ancho_derecho_m,
    geometria_poligono,
    fuente,
    fecha_vigencia_inicio,
    activo
)
SELECT 
    id_tramo,
    1 AS version,
    ancho_total_derecho_via_m / 2 AS ancho_izquierdo_m,
    ancho_total_derecho_via_m / 2 AS ancho_derecho_m,
    -- ST_Buffer con endcap=flat o round (geography genera round por defecto). 
    -- Convertimos a geografía para hacer el buffer en metros y volvemos a geometría, 
    -- y luego forzamos a MULTIPOLYGON.
    ST_Multi(ST_Buffer(geometria_linea::geography, ancho_total_derecho_via_m / 2)::geometry) AS geometria_poligono,
    'Migración automática desde búfer implícito' AS fuente,
    fecha_registro AS fecha_vigencia_inicio,
    TRUE AS activo
FROM tramo
WHERE activo = true AND geometria_linea IS NOT NULL;

-- Registrar migración en historial
INSERT INTO schema_migrations (version, descripcion) VALUES ('010', 'Corte 5 - Franja Derecho Via');

COMMIT;
