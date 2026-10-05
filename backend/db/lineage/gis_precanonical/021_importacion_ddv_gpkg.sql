-- Amplia el staging existente exclusivamente para importaciones DDV GeoPackage.
SET search_path = public, pg_catalog;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
         WHERE version = '020'
           AND checksum_sha256 = '3662cc9ce0ed2e63095b7a873616356aa965e94b1b34e9f651ffd5396452dc09'
    ) THEN
        RAISE EXCEPTION '021 requiere la migracion 020 exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '021') THEN
        RAISE EXCEPTION '021 ya se encuentra registrada';
    END IF;
END $$;

SELECT pg_advisory_xact_lock(
    hashtextextended('software-pa:021:importacion-ddv-gpkg', 0)
);

ALTER TABLE importacion_archivo DROP CONSTRAINT chk_importacion_objetivo;
ALTER TABLE importacion_archivo ADD CONSTRAINT chk_importacion_objetivo CHECK (
    tipo_objetivo IN (
        'trazo_proyecto', 'nucleo_agrario', 'parcela', 'derecho_via_proyecto'
    )
);
ALTER TABLE importacion_archivo ADD CONSTRAINT chk_importacion_ddv_gpkg CHECK (
    tipo_objetivo <> 'derecho_via_proyecto'
    OR (
        formato_detectado = 'gpkg'
        AND mapeo = '{}'::jsonb
        AND opciones_mapeo = '{}'::jsonb
        AND id_perfil IS NULL
        AND crs_destino = 'EPSG:4326'
    )
);

CREATE OR REPLACE FUNCTION fn_validar_importacion_feature_objetivo()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_objetivo varchar(30);
    v_id_proyecto integer;
    v_tipo text;
    v_destino_existe boolean;
BEGIN
    SELECT tipo_objetivo, id_proyecto INTO v_objetivo, v_id_proyecto
      FROM importacion_archivo
     WHERE id_importacion = NEW.id_importacion AND activo;
    IF v_objetivo IS NULL THEN
        RAISE EXCEPTION 'La importación padre no existe o está inactiva';
    END IF;

    IF NEW.geometria_normalizada IS NOT NULL THEN
        v_tipo := GeometryType(NEW.geometria_normalizada);
        IF (v_objetivo = 'trazo_proyecto' AND v_tipo <> 'MULTILINESTRING')
           OR (v_objetivo IN ('nucleo_agrario', 'parcela', 'derecho_via_proyecto')
               AND v_tipo <> 'MULTIPOLYGON') THEN
            RAISE EXCEPTION 'Tipo geométrico % inválido para objetivo %',
                v_tipo, v_objetivo;
        END IF;
    END IF;

    IF NEW.registro_destino_id IS NOT NULL THEN
        IF v_objetivo = 'trazo_proyecto' THEN
            SELECT EXISTS (
                SELECT 1 FROM trazo_proyecto
                 WHERE id_trazo = NEW.registro_destino_id
            ) INTO v_destino_existe;
        ELSIF v_objetivo = 'nucleo_agrario' THEN
            SELECT EXISTS (
                SELECT 1 FROM nucleo_agrario
                 WHERE id_nucleo = NEW.registro_destino_id
            ) INTO v_destino_existe;
        ELSIF v_objetivo = 'parcela' THEN
            SELECT EXISTS (
                SELECT 1 FROM parcela
                 WHERE id_parcela = NEW.registro_destino_id
            ) INTO v_destino_existe;
        ELSE
            SELECT EXISTS (
                SELECT 1 FROM derecho_via_proyecto
                 WHERE id_derecho_via = NEW.registro_destino_id
                   AND id_proyecto = v_id_proyecto
            ) INTO v_destino_existe;
        END IF;
        IF NOT v_destino_existe THEN
            RAISE EXCEPTION
                'El registro destino confirmado no existe para el objetivo %',
                v_objetivo;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
