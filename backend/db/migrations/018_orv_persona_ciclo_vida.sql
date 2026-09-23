-- Separa la vigencia temporal de ORV/OrvIntegrante de su baja administrativa.
-- Agrega causas de finalizacion, evita traslapes y protege la baja de Persona.
SET search_path = public, pg_catalog;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM schema_migrations
         WHERE version = '017'
           AND checksum_sha256 = '7fe91d37c1724291f0bf3fa47ba58d6afff8c062e6c44d527b14ea025fa36282'
    ) THEN
        RAISE EXCEPTION '018 requiere la migracion 017 exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '018') THEN
        RAISE EXCEPTION '018 ya se encuentra registrada';
    END IF;
END $$;

SELECT pg_advisory_xact_lock(
    hashtextextended('software-pa:018:orv-persona-ciclo-vida', 0)
);

LOCK TABLE catalogo_operativo, orv_integrante, persona IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE parcela_titular, unidad_agraria_titular, convenio_compareciente,
           tramite_fifonafe_interviniente, pago IN SHARE ROW EXCLUSIVE MODE;

-- No se puede hacer segura la baja de Persona si el estado vigente ya contiene
-- relaciones activas hacia personas administrativamente inactivas.
DO $$
DECLARE
    v_conflictos text;
BEGIN
    SELECT string_agg(referencia, ', ' ORDER BY referencia)
      INTO v_conflictos
      FROM (
        SELECT 'orv_integrante:' || oi.id_orv_integrante AS referencia
          FROM orv_integrante oi JOIN persona p USING (id_persona)
         WHERE oi.activo AND NOT p.activo
        UNION ALL
        SELECT 'parcela_titular:' || pt.id_parcela_titular
          FROM parcela_titular pt JOIN persona p USING (id_persona)
         WHERE pt.activo AND NOT p.activo
        UNION ALL
        SELECT 'unidad_agraria_titular:' || ut.id_unidad_titular
          FROM unidad_agraria_titular ut JOIN persona p USING (id_persona)
         WHERE ut.activo AND NOT p.activo
        UNION ALL
        SELECT 'convenio_compareciente:' || cc.id_compareciente
          FROM convenio_compareciente cc JOIN persona p USING (id_persona)
         WHERE cc.activo AND NOT p.activo
        UNION ALL
        SELECT 'tramite_fifonafe_interviniente:' || tfi.id_interviniente_fifonafe
          FROM tramite_fifonafe_interviniente tfi JOIN persona p USING (id_persona)
         WHERE tfi.activo AND NOT p.activo
        UNION ALL
        SELECT 'pago:' || pa.id_pago
          FROM pago pa JOIN persona p ON p.id_persona = pa.id_persona_beneficiaria
         WHERE pa.activo AND NOT p.activo
      ) conflictos;

    IF v_conflictos IS NOT NULL THEN
        RAISE EXCEPTION
            '018 abortada: relaciones activas apuntan a personas inactivas: %',
            v_conflictos;
    END IF;
END $$;

-- El rango usa ambos extremos inclusivos porque fecha_fin es el ultimo dia
-- efectivo. daterange canoniza [inicio, fin] como [inicio, fin + 1 dia).
DO $$
DECLARE
    v_conflictos text;
BEGIN
    SELECT string_agg(a.id_orv_integrante || '<->' || b.id_orv_integrante, ', '
                      ORDER BY a.id_orv_integrante, b.id_orv_integrante)
      INTO v_conflictos
      FROM orv_integrante a
      JOIN orv_integrante b
        ON a.id_orv_integrante < b.id_orv_integrante
       AND a.activo AND b.activo
       AND a.id_orv = b.id_orv
       AND a.id_organo = b.id_organo
       AND a.id_cargo = b.id_cargo
       AND a.id_calidad = b.id_calidad
       AND daterange(a.fecha_inicio, a.fecha_fin, '[]')
           && daterange(b.fecha_inicio, b.fecha_fin, '[]');

    IF v_conflictos IS NOT NULL THEN
        RAISE EXCEPTION
            '018 abortada: periodos ORV traslapados en registros %', v_conflictos;
    END IF;
END $$;

ALTER TABLE catalogo_operativo DISABLE TRIGGER trg_audit_catalogo_operativo;
INSERT INTO catalogo_operativo(
    tipo_catalogo, codigo, nombre, descripcion, orden, fuente, activo
)
SELECT 'tipo_fin_orv_integrante', v.codigo, v.nombre, v.descripcion, v.orden,
       'Ciclo de vida ORV', true
  FROM (VALUES
    ('termino_periodo', 'Término de periodo', 'Conclusión del periodo del cargo.', 10),
    ('remocion_asamblea', 'Remoción por asamblea', 'Remoción acordada por la asamblea.', 20),
    ('sustitucion', 'Sustitución', 'Sustitución de la persona integrante.', 30),
    ('fallecimiento', 'Fallecimiento', 'Conclusión del cargo por fallecimiento.', 40),
    ('correccion', 'Corrección', 'Corrección administrativa de la vigencia funcional.', 50),
    ('otro', 'Otro', 'Otra causa documentada; requiere detalle.', 999)
  ) AS v(codigo, nombre, descripcion, orden)
 WHERE NOT EXISTS (
    SELECT 1 FROM catalogo_operativo c
     WHERE c.tipo_catalogo = 'tipo_fin_orv_integrante' AND c.codigo = v.codigo
 );

INSERT INTO catalogo_operativo(
    tipo_catalogo, codigo, nombre, descripcion, orden, fuente, activo
)
SELECT 'tipo_fin_orv_integrante', 'sin_clasificar', 'Sin clasificar',
       'Razón no determinada para una finalización histórica previa a schema 018.',
       1000, 'Migración de datos históricos', true
 WHERE EXISTS (SELECT 1 FROM orv_integrante WHERE fecha_fin IS NOT NULL)
   AND NOT EXISTS (
       SELECT 1 FROM catalogo_operativo
        WHERE tipo_catalogo = 'tipo_fin_orv_integrante'
          AND codigo = 'sin_clasificar'
   );
ALTER TABLE catalogo_operativo ENABLE TRIGGER trg_audit_catalogo_operativo;

DO $$
DECLARE
    v_incompatibles text;
BEGIN
    SELECT string_agg(codigo, ', ' ORDER BY codigo)
      INTO v_incompatibles
      FROM catalogo_operativo
     WHERE tipo_catalogo = 'tipo_fin_orv_integrante'
       AND codigo IN (
           'termino_periodo', 'remocion_asamblea', 'sustitucion',
           'fallecimiento', 'correccion', 'otro'
       )
       AND NOT activo;
    IF v_incompatibles IS NOT NULL THEN
        RAISE EXCEPTION '018: opciones tipo_fin_orv_integrante inactivas: %', v_incompatibles;
    END IF;
    IF (
        SELECT count(*) FROM catalogo_operativo
         WHERE tipo_catalogo = 'tipo_fin_orv_integrante'
           AND codigo IN (
               'termino_periodo', 'remocion_asamblea', 'sustitucion',
               'fallecimiento', 'correccion', 'otro'
           )
           AND activo
    ) <> 6 THEN
        RAISE EXCEPTION '018 requiere seis causas funcionales activas y unicas';
    END IF;
    IF EXISTS (SELECT 1 FROM orv_integrante WHERE fecha_fin IS NOT NULL)
       AND (
           SELECT count(*) FROM catalogo_operativo
            WHERE tipo_catalogo = 'tipo_fin_orv_integrante'
              AND codigo = 'sin_clasificar'
              AND activo
       ) <> 1 THEN
        RAISE EXCEPTION
            '018 requiere sin_clasificar activo y unico para la historia existente';
    END IF;
END $$;

ALTER TABLE orv_integrante
    ADD COLUMN id_tipo_fin bigint,
    ADD COLUMN detalle_fin text;

ALTER TABLE orv_integrante
    ADD CONSTRAINT orv_integrante_id_tipo_fin_fkey
    FOREIGN KEY (id_tipo_fin) REFERENCES catalogo_operativo(id_catalogo_opcion);

-- El runner no representa a una persona usuaria. Se evita fabricar auditoría
-- durante el backfill neutral y se repone inmediatamente el trigger.
ALTER TABLE orv_integrante DISABLE TRIGGER trg_audit_orv_integrante;
UPDATE orv_integrante
   SET id_tipo_fin = (
       SELECT id_catalogo_opcion
        FROM catalogo_operativo
        WHERE tipo_catalogo = 'tipo_fin_orv_integrante'
          AND codigo = 'sin_clasificar'
          AND activo
   )
 WHERE fecha_fin IS NOT NULL;
ALTER TABLE orv_integrante ENABLE TRIGGER trg_audit_orv_integrante;

ALTER TABLE orv_integrante
    ADD CONSTRAINT chk_orv_integrante_finalizacion CHECK (
        (fecha_fin IS NULL AND id_tipo_fin IS NULL
            AND (detalle_fin IS NULL OR btrim(detalle_fin) = ''))
        OR
        (fecha_fin IS NOT NULL AND id_tipo_fin IS NOT NULL)
    );

CREATE FUNCTION fn_validar_orv_integrante_finalizacion() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_codigo text;
BEGIN
    IF NEW.id_tipo_fin IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT codigo INTO v_codigo
      FROM catalogo_operativo
     WHERE id_catalogo_opcion = NEW.id_tipo_fin
       AND tipo_catalogo = 'tipo_fin_orv_integrante'
       AND activo;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Tipo de finalizacion ORV invalido';
    END IF;
    IF v_codigo = 'otro' AND NULLIF(btrim(NEW.detalle_fin), '') IS NULL THEN
        RAISE EXCEPTION 'El tipo de finalizacion otro requiere detalle';
    END IF;
    IF v_codigo = 'sin_clasificar'
       AND (TG_OP = 'INSERT' OR OLD.id_tipo_fin IS DISTINCT FROM NEW.id_tipo_fin) THEN
        RAISE EXCEPTION 'sin_clasificar se reserva para datos historicos migrados';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_orv_integrante_finalizacion
BEFORE INSERT OR UPDATE OF fecha_fin, id_tipo_fin, detalle_fin
ON orv_integrante FOR EACH ROW
EXECUTE FUNCTION fn_validar_orv_integrante_finalizacion();

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;

ALTER TABLE orv_integrante
    ADD CONSTRAINT ex_orv_integrante_slot_periodo
    EXCLUDE USING gist (
        id_orv WITH =,
        id_organo WITH =,
        id_cargo WITH =,
        id_calidad WITH =,
        daterange(fecha_inicio, fecha_fin, '[]') WITH &&
    ) WHERE (activo);

COMMENT ON CONSTRAINT ex_orv_integrante_slot_periodo ON orv_integrante IS
    'Impide periodos activos traslapados por ORV/organo/cargo/calidad; fecha_fin es inclusiva.';

-- Serializa la baja de Persona con la creación/reactivación de cualquiera de
-- sus relaciones activas, de modo que la protección sobreviva a concurrencia.
CREATE FUNCTION fn_persona_tiene_relaciones_activas(p_id_persona integer)
RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT EXISTS (SELECT 1 FROM orv_integrante WHERE id_persona = p_id_persona AND activo)
        OR EXISTS (SELECT 1 FROM parcela_titular WHERE id_persona = p_id_persona AND activo)
        OR EXISTS (SELECT 1 FROM unidad_agraria_titular WHERE id_persona = p_id_persona AND activo)
        OR EXISTS (SELECT 1 FROM convenio_compareciente WHERE id_persona = p_id_persona AND activo)
        OR EXISTS (SELECT 1 FROM tramite_fifonafe_interviniente WHERE id_persona = p_id_persona AND activo)
        OR EXISTS (SELECT 1 FROM pago WHERE id_persona_beneficiaria = p_id_persona AND activo);
$$;

CREATE FUNCTION fn_proteger_baja_persona() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.activo AND NOT NEW.activo THEN
        PERFORM pg_advisory_xact_lock(
            hashtextextended('software-pa:persona-relaciones:' || NEW.id_persona, 0)
        );
        IF fn_persona_tiene_relaciones_activas(NEW.id_persona) THEN
            RAISE EXCEPTION
                'La persona mantiene relaciones activas y no puede darse de baja';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_persona_proteger_baja
BEFORE UPDATE OF activo ON persona FOR EACH ROW
EXECUTE FUNCTION fn_proteger_baja_persona();

CREATE FUNCTION fn_validar_persona_relacion_activa() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_id_persona integer;
BEGIN
    IF NOT NEW.activo THEN
        RETURN NEW;
    END IF;
    v_id_persona := NULLIF(to_jsonb(NEW) ->> TG_ARGV[0], '')::integer;
    IF v_id_persona IS NULL THEN
        RETURN NEW;
    END IF;
    PERFORM pg_advisory_xact_lock(
        hashtextextended('software-pa:persona-relaciones:' || v_id_persona, 0)
    );
    IF NOT EXISTS (
        SELECT 1 FROM persona WHERE id_persona = v_id_persona AND activo
    ) THEN
        RAISE EXCEPTION 'Persona inexistente o inactiva';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_orv_integrante_persona_activa
BEFORE INSERT OR UPDATE OF id_persona, activo ON orv_integrante FOR EACH ROW
EXECUTE FUNCTION fn_validar_persona_relacion_activa('id_persona');
CREATE TRIGGER trg_parcela_titular_persona_activa
BEFORE INSERT OR UPDATE OF id_persona, activo ON parcela_titular FOR EACH ROW
EXECUTE FUNCTION fn_validar_persona_relacion_activa('id_persona');
CREATE TRIGGER trg_unidad_titular_persona_activa
BEFORE INSERT OR UPDATE OF id_persona, activo ON unidad_agraria_titular FOR EACH ROW
EXECUTE FUNCTION fn_validar_persona_relacion_activa('id_persona');
CREATE TRIGGER trg_compareciente_persona_activa
BEFORE INSERT OR UPDATE OF id_persona, activo ON convenio_compareciente FOR EACH ROW
EXECUTE FUNCTION fn_validar_persona_relacion_activa('id_persona');
CREATE TRIGGER trg_fif_interviniente_persona_activa
BEFORE INSERT OR UPDATE OF id_persona, activo ON tramite_fifonafe_interviniente FOR EACH ROW
EXECUTE FUNCTION fn_validar_persona_relacion_activa('id_persona');
CREATE TRIGGER trg_pago_persona_activa
BEFORE INSERT OR UPDATE OF id_persona_beneficiaria, activo ON pago FOR EACH ROW
EXECUTE FUNCTION fn_validar_persona_relacion_activa('id_persona_beneficiaria');

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM orv_integrante
         WHERE (fecha_fin IS NULL) IS DISTINCT FROM (id_tipo_fin IS NULL)
            OR (fecha_fin IS NOT NULL AND fecha_inicio IS NOT NULL AND fecha_fin < fecha_inicio)
    ) THEN
        RAISE EXCEPTION '018 postcondicion: finalizaciones ORV inconsistentes';
    END IF;
    IF EXISTS (
        SELECT 1
          FROM orv_integrante oi
          JOIN catalogo_operativo c ON c.id_catalogo_opcion = oi.id_tipo_fin
         WHERE c.tipo_catalogo <> 'tipo_fin_orv_integrante'
            OR (c.codigo = 'otro' AND NULLIF(btrim(oi.detalle_fin), '') IS NULL)
    ) THEN
        RAISE EXCEPTION '018 postcondicion: tipo o detalle de finalizacion invalido';
    END IF;
END $$;
