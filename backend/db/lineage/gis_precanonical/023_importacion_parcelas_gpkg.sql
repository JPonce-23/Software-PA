-- Habilita staging GPKG estricto de geometrías de parcelas existentes.
SET search_path = public, pg_catalog;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
         WHERE version = '022'
           AND checksum_sha256 = 'a244ed434176feff02ceacbb0e5204bebe0bb16d582dbb4efdea9a13a41ebf0b'
    ) THEN
        RAISE EXCEPTION '023 requiere la migracion 022 exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '023') THEN
        RAISE EXCEPTION '023 ya se encuentra registrada';
    END IF;
END $$;

SELECT pg_advisory_xact_lock(
    hashtextextended('software-pa:023:importacion-parcelas-gpkg', 0)
);

ALTER TABLE importacion_archivo DROP CONSTRAINT chk_importacion_objetivo;
ALTER TABLE importacion_archivo ADD CONSTRAINT chk_importacion_objetivo CHECK (
    tipo_objetivo IN (
        'trazo_proyecto', 'nucleo_agrario', 'parcela',
        'derecho_via_proyecto', 'nucleo_agrario_gpkg', 'parcela_gpkg'
    )
);
ALTER TABLE importacion_archivo ADD CONSTRAINT chk_importacion_parcela_gpkg CHECK (
    tipo_objetivo <> 'parcela_gpkg'
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
           OR (v_objetivo IN ('nucleo_agrario', 'parcela',
                             'derecho_via_proyecto', 'nucleo_agrario_gpkg',
                             'parcela_gpkg') AND v_tipo <> 'MULTIPOLYGON') THEN
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
        ELSIF v_objetivo = 'nucleo_agrario_gpkg' THEN
            SELECT EXISTS (
                SELECT 1 FROM nucleo_agrario n
                JOIN proyecto_nucleo pn ON pn.id_nucleo = n.id_nucleo
                 WHERE n.id_nucleo = NEW.registro_destino_id
                   AND n.activo AND pn.activo AND pn.id_proyecto = v_id_proyecto
                   AND lower(btrim(n.fuente_datos)) = 'ran_phina_catalogo_nucleos'
                   AND btrim(n.id_nucleo_fuente) = NEW.atributos_normalizados->>'cve_unica'
            ) INTO v_destino_existe;
        ELSIF v_objetivo = 'parcela_gpkg' THEN
            SELECT EXISTS (
                SELECT 1 FROM parcela p
                JOIN nucleo_agrario n ON n.id_nucleo = p.id_nucleo
                JOIN proyecto_nucleo pn ON pn.id_nucleo = n.id_nucleo
                 WHERE p.id_parcela = NEW.registro_destino_id
                   AND p.activo AND n.activo AND pn.activo
                   AND pn.id_proyecto = v_id_proyecto
                   AND lower(btrim(n.fuente_datos)) = 'ran_phina_catalogo_nucleos'
                   AND btrim(n.id_nucleo_fuente) =
                       NEW.atributos_normalizados->>'cve_unica_nucleo'
                   AND p.id_nucleo =
                       (NEW.atributos_normalizados->>'id_nucleo')::integer
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
