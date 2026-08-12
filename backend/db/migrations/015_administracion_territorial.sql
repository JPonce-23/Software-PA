BEGIN;

SELECT pg_advisory_xact_lock(hashtext('schema_migration_015'));

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '014') THEN
        RAISE EXCEPTION 'La migracion 014 es requisito para aplicar 015';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '015') THEN
        RAISE EXCEPTION 'La migracion 015 ya fue aplicada';
    END IF;

    IF EXISTS (
        SELECT 1 FROM tramo t
        JOIN proyecto p ON p.id_proyecto = t.id_proyecto
        WHERE t.activo AND NOT p.activo
    ) THEN
        RAISE EXCEPTION 'Existen tramos activos vinculados a proyectos inactivos';
    END IF;
    IF EXISTS (
        SELECT 1 FROM franja_derecho_via f
        JOIN tramo t ON t.id_tramo = f.id_tramo
        WHERE f.activo AND NOT t.activo
    ) THEN
        RAISE EXCEPTION 'Existen franjas activas vinculadas a tramos inactivos';
    END IF;
    IF EXISTS (
        SELECT 1 FROM tramo_nucleo tn
        JOIN tramo t ON t.id_tramo = tn.id_tramo
        JOIN nucleo_agrario n ON n.id_nucleo = tn.id_nucleo
        WHERE tn.activo AND (NOT t.activo OR NOT n.activo)
    ) THEN
        RAISE EXCEPTION 'Existen relaciones tramo-nucleo con padres inactivos';
    END IF;
    IF EXISTS (
        SELECT 1 FROM usuario_tramo ut
        JOIN usuario u ON u.id_usuario = ut.id_usuario
        JOIN tramo t ON t.id_tramo = ut.id_tramo
        WHERE ut.activo AND (NOT u.activo OR NOT t.activo)
    ) THEN
        RAISE EXCEPTION 'Existen asignaciones territoriales con padres inactivos';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM usuario WHERE activo AND rol = 'admin') THEN
        RAISE EXCEPTION 'Debe existir al menos un administrador activo';
    END IF;
    IF EXISTS (
        SELECT lower(btrim(correo)) FROM usuario
        GROUP BY lower(btrim(correo)) HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existen correos duplicados al normalizar mayusculas y espacios';
    END IF;
    IF EXISTS (
        SELECT 1 FROM tramo
        WHERE geometria_linea IS NOT NULL AND (
            ST_IsEmpty(geometria_linea) OR NOT ST_IsValid(geometria_linea)
            OR ST_SRID(geometria_linea) <> 4326
            OR GeometryType(geometria_linea) <> 'MULTILINESTRING'
        )
    ) THEN
        RAISE EXCEPTION 'Existen tramos con geometria incompatible';
    END IF;
    IF EXISTS (
        SELECT 1 FROM tramo_nucleo tn
        JOIN tramo t ON t.id_tramo = tn.id_tramo
        JOIN nucleo_agrario n ON n.id_nucleo = tn.id_nucleo
        WHERE tn.geometria_segmento IS NOT NULL AND (
            ST_IsEmpty(tn.geometria_segmento)
            OR NOT ST_IsValid(tn.geometria_segmento)
            OR ST_SRID(tn.geometria_segmento) <> 4326
            OR GeometryType(tn.geometria_segmento) <> 'MULTILINESTRING'
            OR (t.geometria_linea IS NOT NULL
                AND NOT ST_Intersects(tn.geometria_segmento, t.geometria_linea))
            OR (n.geometria_poligono IS NOT NULL
                AND NOT ST_Intersects(tn.geometria_segmento, n.geometria_poligono))
        )
    ) THEN
        RAISE EXCEPTION 'Existen relaciones tramo-nucleo con geometria incompatible';
    END IF;
END;
$$;

CREATE UNIQUE INDEX uq_015_usuario_correo_normalizado
    ON usuario (lower(btrim(correo)));

ALTER TABLE tramo
    ADD CONSTRAINT chk_015_tramo_geometria_valida CHECK (
        geometria_linea IS NULL OR (
            NOT ST_IsEmpty(geometria_linea)
            AND ST_IsValid(geometria_linea)
            AND ST_SRID(geometria_linea) = 4326
            AND GeometryType(geometria_linea) = 'MULTILINESTRING'
        )
    );

ALTER TABLE tramo_nucleo
    ADD CONSTRAINT chk_015_tramo_nucleo_geometria_valida CHECK (
        geometria_segmento IS NULL OR (
            NOT ST_IsEmpty(geometria_segmento)
            AND ST_IsValid(geometria_segmento)
            AND ST_SRID(geometria_segmento) = 4326
            AND GeometryType(geometria_segmento) = 'MULTILINESTRING'
        )
    );

CREATE OR REPLACE FUNCTION fn_015_validar_hijo_activo() RETURNS TRIGGER AS $$
DECLARE
    v_padre_activo BOOLEAN;
    v_otro_padre_activo BOOLEAN;
    v_tramo_geom GEOMETRY;
    v_nucleo_geom GEOMETRY;
BEGIN
    IF NEW.activo IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME = 'tramo' THEN
        SELECT activo INTO v_padre_activo FROM proyecto
         WHERE id_proyecto = NEW.id_proyecto FOR KEY SHARE;
    ELSIF TG_TABLE_NAME = 'franja_derecho_via' THEN
        SELECT activo INTO v_padre_activo FROM tramo
         WHERE id_tramo = NEW.id_tramo FOR KEY SHARE;
    ELSIF TG_TABLE_NAME = 'usuario_tramo' THEN
        SELECT activo INTO v_padre_activo FROM usuario
         WHERE id_usuario = NEW.id_usuario FOR KEY SHARE;
        SELECT activo INTO v_otro_padre_activo FROM tramo
         WHERE id_tramo = NEW.id_tramo FOR KEY SHARE;
    ELSIF TG_TABLE_NAME = 'tramo_nucleo' THEN
        SELECT activo, geometria_linea
          INTO v_padre_activo, v_tramo_geom
          FROM tramo WHERE id_tramo = NEW.id_tramo FOR KEY SHARE;
        SELECT activo, geometria_poligono
          INTO v_otro_padre_activo, v_nucleo_geom
          FROM nucleo_agrario WHERE id_nucleo = NEW.id_nucleo FOR KEY SHARE;
        IF NEW.geometria_segmento IS NOT NULL AND (
            (v_tramo_geom IS NOT NULL
             AND NOT ST_Intersects(NEW.geometria_segmento, v_tramo_geom))
            OR (v_nucleo_geom IS NOT NULL
                AND NOT ST_Intersects(NEW.geometria_segmento, v_nucleo_geom))
        ) THEN
            RAISE EXCEPTION 'ADM_GEOMETRIA_TRAMO_NUCLEO_INCOHERENTE';
        END IF;
    END IF;

    IF v_padre_activo IS NOT TRUE
       OR (TG_TABLE_NAME IN ('usuario_tramo', 'tramo_nucleo')
           AND v_otro_padre_activo IS NOT TRUE) THEN
        RAISE EXCEPTION 'ADM_PADRE_INACTIVO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_015_validar_baja_padre() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.activo IS TRUE AND NEW.activo IS FALSE THEN
        IF TG_TABLE_NAME = 'proyecto' THEN
            IF EXISTS (
                SELECT 1 FROM tramo
                 WHERE id_proyecto = (to_jsonb(OLD)->>'id_proyecto')::INTEGER
                   AND activo
            ) THEN
                RAISE EXCEPTION 'ADM_PROYECTO_CON_TRAMOS_ACTIVOS';
            END IF;
        ELSIF TG_TABLE_NAME = 'tramo' THEN
            IF EXISTS (SELECT 1 FROM franja_derecho_via WHERE id_tramo = (to_jsonb(OLD)->>'id_tramo')::INTEGER AND activo)
               OR EXISTS (SELECT 1 FROM tramo_nucleo WHERE id_tramo = (to_jsonb(OLD)->>'id_tramo')::INTEGER AND activo)
               OR EXISTS (SELECT 1 FROM usuario_tramo WHERE id_tramo = (to_jsonb(OLD)->>'id_tramo')::INTEGER AND activo) THEN
                RAISE EXCEPTION 'ADM_TRAMO_CON_DEPENDENCIAS_ACTIVAS';
            END IF;
        ELSIF TG_TABLE_NAME = 'nucleo_agrario' THEN
            IF EXISTS (
                SELECT 1 FROM tramo_nucleo
                 WHERE id_nucleo = (to_jsonb(OLD)->>'id_nucleo')::INTEGER
                   AND activo
            ) THEN
                RAISE EXCEPTION 'ADM_NUCLEO_CON_RELACIONES_ACTIVAS';
            END IF;
        ELSIF TG_TABLE_NAME = 'usuario' THEN
            IF EXISTS (
                SELECT 1 FROM usuario_tramo
                 WHERE id_usuario = (to_jsonb(OLD)->>'id_usuario')::INTEGER
                   AND activo
            ) THEN
                RAISE EXCEPTION 'ADM_USUARIO_CON_ASIGNACIONES_ACTIVAS';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_015_validar_administrador_activo() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.activo AND OLD.rol = 'admin'
       AND (NEW.activo IS FALSE OR NEW.rol <> 'admin') THEN
        PERFORM pg_advisory_xact_lock(hashtext('software_pa_active_admin'));
        IF NOT EXISTS (
            SELECT 1 FROM usuario
             WHERE activo AND rol = 'admin' AND id_usuario <> OLD.id_usuario
        ) THEN
            RAISE EXCEPTION 'ADM_ULTIMO_ADMIN_ACTIVO';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_015_validar_geometria_padre() RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'tramo' THEN
        IF NEW.geometria_linea IS DISTINCT FROM OLD.geometria_linea
           AND EXISTS (
               SELECT 1 FROM tramo_nucleo tn
                WHERE tn.id_tramo = (to_jsonb(NEW)->>'id_tramo')::INTEGER
                  AND tn.activo
                  AND tn.geometria_segmento IS NOT NULL
                  AND NEW.geometria_linea IS NOT NULL
                  AND NOT ST_Intersects(tn.geometria_segmento, NEW.geometria_linea)
           ) THEN
            RAISE EXCEPTION 'ADM_GEOMETRIA_TRAMO_ROMPE_RELACIONES';
        END IF;
    ELSIF TG_TABLE_NAME = 'nucleo_agrario' THEN
        IF NEW.geometria_poligono IS DISTINCT FROM OLD.geometria_poligono
           AND EXISTS (
               SELECT 1 FROM tramo_nucleo tn
                WHERE tn.id_nucleo = (to_jsonb(NEW)->>'id_nucleo')::INTEGER
                  AND tn.activo
                  AND tn.geometria_segmento IS NOT NULL
                  AND NEW.geometria_poligono IS NOT NULL
                  AND NOT ST_Intersects(tn.geometria_segmento, NEW.geometria_poligono)
           ) THEN
            RAISE EXCEPTION 'ADM_GEOMETRIA_NUCLEO_ROMPE_RELACIONES';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_015_tramo_padre_activo
    BEFORE INSERT OR UPDATE OF activo, id_proyecto ON tramo
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_hijo_activo();
CREATE TRIGGER trg_015_franja_padre_activo
    BEFORE INSERT OR UPDATE OF activo, id_tramo ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_hijo_activo();
CREATE TRIGGER trg_015_tramo_nucleo_padres_activos
    BEFORE INSERT OR UPDATE OF activo, id_tramo, id_nucleo, geometria_segmento ON tramo_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_hijo_activo();
CREATE TRIGGER trg_015_usuario_tramo_padres_activos
    BEFORE INSERT OR UPDATE OF activo, id_usuario, id_tramo ON usuario_tramo
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_hijo_activo();

CREATE TRIGGER trg_015_proyecto_sin_hijos_activos
    BEFORE UPDATE OF activo ON proyecto
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_baja_padre();
CREATE TRIGGER trg_015_tramo_sin_hijos_activos
    BEFORE UPDATE OF activo ON tramo
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_baja_padre();
CREATE TRIGGER trg_015_nucleo_sin_hijos_activos
    BEFORE UPDATE OF activo ON nucleo_agrario
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_baja_padre();
CREATE TRIGGER trg_015_usuario_sin_asignaciones
    BEFORE UPDATE OF activo ON usuario
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_baja_padre();
CREATE TRIGGER trg_015_ultimo_admin
    BEFORE UPDATE OF activo, rol ON usuario
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_administrador_activo();
CREATE TRIGGER trg_015_tramo_geometria_relaciones
    BEFORE UPDATE OF geometria_linea ON tramo
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_geometria_padre();
CREATE TRIGGER trg_015_nucleo_geometria_relaciones
    BEFORE UPDATE OF geometria_poligono ON nucleo_agrario
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_geometria_padre();

INSERT INTO schema_migrations (version, descripcion)
VALUES ('015', 'Administracion territorial, jerarquia activa y concurrencia');

COMMIT;
