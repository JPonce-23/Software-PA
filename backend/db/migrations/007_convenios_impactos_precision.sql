-- CANDIDATO NO EJECUTADO — Bloque 5 Convenios / Cierre Excel V1.
-- Migración forward-only. Requiere una base con 001-006 verificadas.
SET search_path = public, pg_catalog;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
        WHERE version = '006' AND checksum_sha256 =
            'e1a603fd2015615671c0cd072a0a795f50e92e8c21e838f26d88abec25dddee4'
    ) THEN
        RAISE EXCEPTION '007 requiere la migración 006 exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '007') THEN
        RAISE EXCEPTION '007 ya se encuentra registrada';
    END IF;
    IF to_regclass('public.vw_proyecto_nucleo_resumen') IS NULL
       OR to_regclass('public.vw_hito_seguimiento_005') IS NULL
       OR to_regclass('public.vw_hito_seguimiento') IS NULL
       OR to_regclass('public.vw_reporte_avance_periodo') IS NULL
       OR to_regclass('public.vw_dashboard_kpi') IS NULL
       OR to_regclass('public.vw_reporte_snapshot_actual') IS NULL THEN
        RAISE EXCEPTION '007 requiere todas las vistas efectivas de 006';
    END IF;
END $$;

-- ALTER TYPE necesita retirar las vistas dependientes. Se guardan y recrean
-- expresamente; no se usa DROP CASCADE y no se cambia su semántica histórica.
CREATE TEMP TABLE _007_vistas_006 (
    orden integer PRIMARY KEY,
    nombre text NOT NULL UNIQUE,
    definicion text NOT NULL,
    comentario text,
    propietario text NOT NULL
) ON COMMIT DROP;

INSERT INTO _007_vistas_006(orden,nombre,definicion,comentario,propietario) VALUES
    (5,'vw_proyecto_nucleo_resumen',pg_get_viewdef('vw_proyecto_nucleo_resumen'::regclass,true),obj_description('vw_proyecto_nucleo_resumen'::regclass,'pg_class'),pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='vw_proyecto_nucleo_resumen'::regclass))),
    (10,'vw_hito_seguimiento_005',pg_get_viewdef('vw_hito_seguimiento_005'::regclass,true),obj_description('vw_hito_seguimiento_005'::regclass,'pg_class'),pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='vw_hito_seguimiento_005'::regclass))),
    (20,'vw_hito_seguimiento',pg_get_viewdef('vw_hito_seguimiento'::regclass,true),obj_description('vw_hito_seguimiento'::regclass,'pg_class'),pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='vw_hito_seguimiento'::regclass))),
    (30,'vw_reporte_avance_periodo',pg_get_viewdef('vw_reporte_avance_periodo'::regclass,true),obj_description('vw_reporte_avance_periodo'::regclass,'pg_class'),pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='vw_reporte_avance_periodo'::regclass))),
    (40,'vw_dashboard_kpi',pg_get_viewdef('vw_dashboard_kpi'::regclass,true),obj_description('vw_dashboard_kpi'::regclass,'pg_class'),pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='vw_dashboard_kpi'::regclass))),
    (50,'vw_reporte_snapshot_actual',pg_get_viewdef('vw_reporte_snapshot_actual'::regclass,true),obj_description('vw_reporte_snapshot_actual'::regclass,'pg_class'),pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='vw_reporte_snapshot_actual'::regclass)));

CREATE TEMP TABLE _007_permisos_vistas AS
SELECT tp.table_name nombre,tp.grantee,tp.privilege_type,tp.is_grantable
FROM information_schema.table_privileges tp
JOIN _007_vistas_006 v ON v.nombre=tp.table_name
WHERE tp.table_schema='public';

DROP VIEW vw_dashboard_kpi;
DROP VIEW vw_reporte_avance_periodo;
DROP VIEW vw_hito_seguimiento;
DROP VIEW vw_hito_seguimiento_005;
DROP VIEW vw_reporte_snapshot_actual;
DROP VIEW vw_proyecto_nucleo_resumen;

-- Las fuentes auditadas llegan a 0.0000001 ha. Esta ampliación no recupera
-- decimales ya redondeados; toda corrección posterior requiere trazabilidad.
ALTER TABLE afectacion
    ALTER COLUMN superficie_preliminar_ha TYPE numeric(15,7)
        USING superficie_preliminar_ha::numeric(15,7),
    ALTER COLUMN superficie_afectada_ha TYPE numeric(15,7)
        USING superficie_afectada_ha::numeric(15,7);

ALTER TABLE afectacion_unidad_agraria
    ALTER COLUMN superficie_preliminar_ha TYPE numeric(15,7)
        USING superficie_preliminar_ha::numeric(15,7),
    ALTER COLUMN superficie_afectada_ha TYPE numeric(15,7)
        USING superficie_afectada_ha::numeric(15,7);

ALTER TABLE convenio
    ALTER COLUMN superficie_ha TYPE numeric(15,7)
        USING superficie_ha::numeric(15,7),
    ADD COLUMN efecto_monto varchar(20) NOT NULL DEFAULT 'pendiente',
    ADD COLUMN monto_90_impacto numeric(18,2),
    ADD COLUMN monto_100_impacto numeric(18,2),
    ADD COLUMN monto_bdt_impacto numeric(18,2),
    ADD COLUMN estado_antecedente varchar(30);

ALTER TABLE convenio_afectacion
    ADD COLUMN efecto_superficie varchar(20) NOT NULL DEFAULT 'pendiente',
    ADD COLUMN superficie_impacto_ha numeric(15,7);

COMMENT ON COLUMN convenio.superficie_ha IS
    'Superficie total declarada por el instrumento; no representa por sí sola superficie física ni impacto sumable.';
COMMENT ON COLUMN convenio.efecto_monto IS
    'Semántica económica independiente de tipo_convenio: adicion, sustitucion, correccion, sin_cambio o pendiente.';
COMMENT ON COLUMN convenio.monto_90_impacto IS
    'Impacto con signo sobre la obligación al 90%; nunca se suma con 100% o BDT.';
COMMENT ON COLUMN convenio.monto_100_impacto IS
    'Impacto con signo sobre la obligación al 100%; nunca se suma con 90% o BDT.';
COMMENT ON COLUMN convenio.monto_bdt_impacto IS
    'Impacto con signo sobre BDT; nunca se suma con 90% o 100%.';
COMMENT ON COLUMN convenio.estado_antecedente IS
    'no_aplica, vinculado, referido_sin_soporte o pendiente_identificar; evita padres ficticios.';
COMMENT ON COLUMN convenio_afectacion.efecto_superficie IS
    'Efecto del instrumento sobre esta afectación; independiente de tipo_convenio.';
COMMENT ON COLUMN convenio_afectacion.superficie_impacto_ha IS
    'Impacto superficial con signo para esta relación; la superficie física vigente permanece en afectación/unidad.';

ALTER TABLE convenio ADD CONSTRAINT chk_convenio_efecto_monto_007 CHECK (
    efecto_monto IN ('adicion','sustitucion','correccion','sin_cambio','pendiente')
);
ALTER TABLE convenio ADD CONSTRAINT chk_convenio_impacto_monto_007 CHECK (
    (efecto_monto = 'pendiente'
        AND monto_90_impacto IS NULL
        AND monto_100_impacto IS NULL
        AND monto_bdt_impacto IS NULL)
 OR (efecto_monto = 'sin_cambio'
        AND num_nonnulls(monto_90_impacto,monto_100_impacto,monto_bdt_impacto) > 0
        AND coalesce(monto_90_impacto,0) = 0
        AND coalesce(monto_100_impacto,0) = 0
        AND coalesce(monto_bdt_impacto,0) = 0)
 OR (efecto_monto = 'adicion'
        AND num_nonnulls(monto_90_impacto,monto_100_impacto,monto_bdt_impacto) > 0
        AND coalesce(monto_90_impacto,0) >= 0
        AND coalesce(monto_100_impacto,0) >= 0
        AND coalesce(monto_bdt_impacto,0) >= 0
        AND greatest(coalesce(monto_90_impacto,0),coalesce(monto_100_impacto,0),coalesce(monto_bdt_impacto,0)) > 0)
 OR (efecto_monto IN ('sustitucion','correccion')
        AND num_nonnulls(monto_90_impacto,monto_100_impacto,monto_bdt_impacto) > 0)
);
ALTER TABLE convenio ADD CONSTRAINT chk_convenio_impacto_declarado_007 CHECK (
    efecto_monto = 'pendiente'
 OR ((monto_90 IS NULL OR monto_90_impacto IS NOT NULL)
     AND (monto_100 IS NULL OR monto_100_impacto IS NOT NULL)
     AND (monto_bdt IS NULL OR monto_bdt_impacto IS NOT NULL))
);

ALTER TABLE convenio_afectacion ADD CONSTRAINT chk_ca_efecto_superficie_007 CHECK (
    efecto_superficie IN ('adicion','sustitucion','correccion','sin_cambio','pendiente')
);
ALTER TABLE convenio_afectacion ADD CONSTRAINT chk_ca_impacto_superficie_007 CHECK (
    (efecto_superficie = 'pendiente' AND superficie_impacto_ha IS NULL)
 OR (efecto_superficie = 'sin_cambio' AND superficie_impacto_ha = 0)
 OR (efecto_superficie = 'adicion' AND superficie_impacto_ha > 0)
 OR (efecto_superficie IN ('sustitucion','correccion') AND superficie_impacto_ha IS NOT NULL)
);

-- Backfill de linaje: sólo hechos ya estructurados. Los efectos permanecen
-- pendientes y sus impactos NULL; no se infieren desde tipo_convenio.
ALTER TABLE convenio DISABLE TRIGGER trg_audit_convenio;
UPDATE convenio
   SET estado_antecedente = CASE
       WHEN tipo_instrumento = 'convenio'
            AND tipo_convenio IN ('modificatorio','superficie_adicional','obras_complementarias','ampliacion','ampliacion_remanente')
            AND id_convenio_padre IS NOT NULL THEN 'vinculado'
       WHEN tipo_instrumento = 'convenio'
            AND tipo_convenio IN ('modificatorio','superficie_adicional','obras_complementarias','ampliacion','ampliacion_remanente')
            THEN 'pendiente_identificar'
       ELSE 'no_aplica'
   END;

-- El UPDATE dispara dos constraint triggers diferidos de integridad. Se fuerzan
-- por nombre antes del siguiente ALTER TABLE para ejecutar sus validaciones y
-- vaciar únicamente esos eventos pendientes; después se restaura su modo
-- inicialmente diferido. No se deshabilita ningún trigger de integridad.
SET CONSTRAINTS trg_convenio_individual_firmado, trg_linaje_unidad_convenio IMMEDIATE;
ALTER TABLE convenio ENABLE TRIGGER trg_audit_convenio;
SET CONSTRAINTS trg_convenio_individual_firmado, trg_linaje_unidad_convenio DEFERRED;

ALTER TABLE convenio
    ALTER COLUMN estado_antecedente SET NOT NULL,
    ADD CONSTRAINT chk_convenio_estado_antecedente_007 CHECK (
        estado_antecedente IN ('no_aplica','vinculado','referido_sin_soporte','pendiente_identificar')
    );

CREATE OR REPLACE FUNCTION fn_validar_estado_antecedente_007() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    es_derivado boolean := NEW.tipo_instrumento = 'convenio'
        AND NEW.tipo_convenio IN ('modificatorio','superficie_adicional','obras_complementarias','ampliacion','ampliacion_remanente');
BEGIN
    IF NOT NEW.activo THEN RETURN NEW; END IF;
    -- Compatibilidad con el backend 006: omitir el campo no inventa un padre.
    -- Un vínculo real permite derivar "vinculado"; sin vínculo queda pendiente.
    IF NEW.estado_antecedente IS NULL
       OR (TG_OP='UPDATE'
           AND NEW.estado_antecedente IS NOT DISTINCT FROM OLD.estado_antecedente
           AND (NEW.tipo_instrumento IS DISTINCT FROM OLD.tipo_instrumento
                OR NEW.tipo_convenio IS DISTINCT FROM OLD.tipo_convenio
                OR NEW.id_convenio_padre IS DISTINCT FROM OLD.id_convenio_padre)) THEN
        NEW.estado_antecedente := CASE
            WHEN NEW.tipo_instrumento='convenio'
             AND NEW.tipo_convenio IN ('modificatorio','superficie_adicional','obras_complementarias','ampliacion','ampliacion_remanente')
             AND NEW.id_convenio_padre IS NOT NULL THEN 'vinculado'
            WHEN NEW.tipo_instrumento='convenio'
             AND NEW.tipo_convenio IN ('modificatorio','superficie_adicional','obras_complementarias','ampliacion','ampliacion_remanente')
                THEN 'pendiente_identificar'
            ELSE 'no_aplica'
        END;
    END IF;
    IF NEW.tipo_instrumento = 'convenio' AND NEW.tipo_convenio = 'cop_original' THEN
        IF NEW.id_convenio_padre IS NOT NULL OR NEW.estado_antecedente <> 'no_aplica' THEN
            RAISE EXCEPTION '007: COP original no admite padre ni estado de antecedente derivado';
        END IF;
    ELSIF es_derivado THEN
        IF NEW.id_convenio_padre IS NOT NULL AND NEW.estado_antecedente <> 'vinculado' THEN
            RAISE EXCEPTION '007: instrumento con padre debe declarar antecedente vinculado';
        END IF;
        IF NEW.id_convenio_padre IS NULL
           AND NEW.estado_antecedente NOT IN ('referido_sin_soporte','pendiente_identificar') THEN
            RAISE EXCEPTION '007: instrumento sin padre requiere antecedente referido o pendiente de identificar';
        END IF;
    ELSIF NEW.id_convenio_padre IS NOT NULL OR NEW.estado_antecedente <> 'no_aplica' THEN
        RAISE EXCEPTION '007: el instrumento no derivado no admite antecedente';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_estado_antecedente_007 ON convenio;
CREATE TRIGGER trg_estado_antecedente_007
BEFORE INSERT OR UPDATE OF tipo_instrumento,tipo_convenio,id_convenio_padre,estado_antecedente,activo
ON convenio FOR EACH ROW EXECUTE FUNCTION fn_validar_estado_antecedente_007();

-- El bloque 039 conserva todas sus validaciones de ámbito, PN y ciclos; sólo
-- deja de exigir un padre ficticio cuando 007 documenta el estado antecedente.
CREATE OR REPLACE FUNCTION fn_validar_linaje_convenio_individual() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE v_padre convenio%ROWTYPE; v_cycle boolean := false;
BEGIN
    IF NOT NEW.activo OR NEW.ambito IS DISTINCT FROM 'individual' THEN RETURN NEW; END IF;
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        RAISE EXCEPTION '039: convenio individual no debe usar Asamblea como autorizacion';
    END IF;
    IF NEW.tipo_instrumento = 'convenio' THEN
        IF NEW.tipo_convenio NOT IN ('cop_original','modificatorio','ampliacion','ampliacion_remanente') THEN
            RAISE EXCEPTION '039: tipo de convenio % no corresponde al flujo individual', NEW.tipo_convenio;
        END IF;
        IF NEW.tipo_convenio = 'cop_original' AND NEW.id_convenio_padre IS NOT NULL THEN
            RAISE EXCEPTION '039: cop_original individual no debe tener convenio padre';
        END IF;
        IF NEW.id_convenio_padre IS NOT NULL THEN
            IF NEW.id_convenio IS NOT NULL AND NEW.id_convenio_padre = NEW.id_convenio THEN
                RAISE EXCEPTION '039: un convenio no puede ser su propio padre';
            END IF;
            SELECT * INTO v_padre FROM convenio
             WHERE id_convenio=NEW.id_convenio_padre AND activo;
            IF NOT FOUND THEN RAISE EXCEPTION '039: convenio padre inexistente o inactivo'; END IF;
            IF v_padre.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo
               OR v_padre.ambito IS DISTINCT FROM 'individual'
               OR v_padre.tipo_instrumento IS DISTINCT FROM 'convenio' THEN
                RAISE EXCEPTION '039: convenio padre debe compartir ProyectoNucleo, ambito individual y ser un convenio';
            END IF;
            IF NEW.id_convenio IS NOT NULL THEN
                WITH RECURSIVE ancestros AS (
                    SELECT c.id_convenio,c.id_convenio_padre FROM convenio c WHERE c.id_convenio=NEW.id_convenio_padre
                    UNION ALL
                    SELECT p.id_convenio,p.id_convenio_padre FROM convenio p
                    JOIN ancestros a ON p.id_convenio=a.id_convenio_padre
                    WHERE p.id_convenio_padre IS NOT NULL
                ) SELECT EXISTS(SELECT 1 FROM ancestros WHERE id_convenio=NEW.id_convenio) INTO v_cycle;
                IF v_cycle THEN RAISE EXCEPTION '039: el linaje de convenio no puede contener ciclos'; END IF;
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER trg_linaje_convenio_individual ON convenio;
CREATE TRIGGER trg_linaje_convenio_individual
BEFORE INSERT OR UPDATE OF id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,id_convenio_padre,id_asamblea_autorizacion,estado_antecedente,activo
ON convenio FOR EACH ROW EXECUTE FUNCTION fn_validar_linaje_convenio_individual();

-- Conserva Asamblea/PN/ámbito y compatibilidad de tipos de 001; añade las
-- omisiones demostradas para cualquier ámbito: padre-instrumento y autopadre.
CREATE OR REPLACE FUNCTION fn_validar_convenio_relaciones() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE v_padre convenio%ROWTYPE; v_asamblea asamblea%ROWTYPE; v_contexto text;
BEGIN
    IF NEW.id_convenio_padre IS NOT NULL THEN
        IF NEW.id_convenio IS NOT NULL AND NEW.id_convenio_padre=NEW.id_convenio THEN
            RAISE EXCEPTION '007: un convenio no puede ser su propio padre';
        END IF;
        SELECT * INTO v_padre FROM convenio
         WHERE id_convenio=NEW.id_convenio_padre AND activo;
        IF NOT FOUND
           OR v_padre.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo
           OR v_padre.ambito IS DISTINCT FROM NEW.ambito
           OR v_padre.tipo_instrumento IS DISTINCT FROM 'convenio' THEN
            RAISE EXCEPTION '007: el padre debe ser convenio activo del mismo ProyectoNucleo y ámbito';
        END IF;
        IF NEW.tipo_convenio='cop_original'
           OR (NEW.tipo_convenio='superficie_adicional' AND v_padre.tipo_convenio NOT IN ('cop_original','superficie_adicional'))
           OR (NEW.tipo_convenio='obras_complementarias' AND v_padre.tipo_convenio NOT IN ('cop_original','obras_complementarias'))
           OR (NEW.tipo_convenio IN ('ampliacion','ampliacion_remanente') AND v_padre.tipo_convenio NOT IN ('cop_original','ampliacion')) THEN
            RAISE EXCEPTION '007: relación padre/hijo no permitida para los tipos de convenio';
        END IF;
        IF NEW.id_convenio IS NOT NULL AND EXISTS (
            WITH RECURSIVE ancestro AS (
                SELECT c.id_convenio,c.id_convenio_padre FROM convenio c
                 WHERE c.id_convenio=NEW.id_convenio_padre
                UNION
                SELECT c.id_convenio,c.id_convenio_padre FROM convenio c
                JOIN ancestro a ON c.id_convenio=a.id_convenio_padre
                WHERE a.id_convenio_padre IS NOT NULL
            ) SELECT 1 FROM ancestro WHERE id_convenio=NEW.id_convenio
        ) THEN RAISE EXCEPTION '007: la relación de convenios produciría un ciclo'; END IF;
    END IF;
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        SELECT * INTO v_asamblea FROM asamblea
         WHERE id_asamblea=NEW.id_asamblea_autorizacion AND activo;
        IF NEW.ambito IS DISTINCT FROM 'colectivo' OR v_asamblea.id_asamblea IS NULL
           OR v_asamblea.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo THEN
            RAISE EXCEPTION '007: la Asamblea sólo autoriza convenios colectivos del mismo ProyectoNucleo';
        END IF;
        SELECT c.codigo INTO v_contexto FROM catalogo_operativo c
         WHERE c.id_catalogo_opcion=v_asamblea.id_contexto_asamblea;
        IF v_contexto IS NOT NULL AND v_contexto<>'otro'
           AND v_contexto IS DISTINCT FROM NEW.tipo_convenio THEN
            RAISE EXCEPTION '007: el contexto de la Asamblea no corresponde al tipo de convenio';
        END IF;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER trg_convenio_relaciones ON convenio;
CREATE TRIGGER trg_convenio_relaciones
BEFORE INSERT OR UPDATE OF id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,id_convenio_padre,id_asamblea_autorizacion,estado_antecedente,activo
ON convenio FOR EACH ROW EXECUTE FUNCTION fn_validar_convenio_relaciones();

-- Acreditaciones colectivas: se mantiene el catálogo individual existente y
-- el trigger elige el universo según el ámbito del convenio.
ALTER TABLE catalogo_operativo DISABLE TRIGGER trg_audit_catalogo_operativo;
INSERT INTO catalogo_operativo(tipo_catalogo,codigo,nombre,descripcion,orden,fuente,activo)
VALUES
 ('tipo_acreditacion_compareciente_colectivo','nombramiento_orv','Nombramiento en ORV','Representación histórica acreditada mediante ORV del núcleo.',10,'Bloque 5 Convenios / PA / RAN',true),
 ('tipo_acreditacion_compareciente_colectivo','poder_representacion','Poder o mandato','Representación externa o mandato documentado.',20,'Bloque 5 Convenios',true),
 ('tipo_acreditacion_compareciente_colectivo','oficio_comision','Oficio de comisión','Intervención institucional acreditada mediante oficio.',30,'Bloque 5 Convenios',true),
 ('tipo_acreditacion_compareciente_colectivo','credencial_institucional','Credencial institucional','Calidad institucional documentada.',40,'Bloque 5 Convenios',true),
 ('tipo_acreditacion_compareciente_colectivo','otra','Otra acreditación colectiva','Acreditación colectiva descrita y trazable.',90,'Bloque 5 Convenios',true)
ON CONFLICT (tipo_catalogo,codigo) DO NOTHING;
ALTER TABLE catalogo_operativo ENABLE TRIGGER trg_audit_catalogo_operativo;

ALTER TABLE requisito_documental DISABLE TRIGGER trg_audit_requisito_documental;
INSERT INTO requisito_documental(codigo,nombre,descripcion,contexto,obligatorio,orden,fuente,activo)
VALUES ('col_convenio_firmado','Convenio colectivo firmado',
 'Instrumento colectivo con firmas completas y acreditadas; disponibilidad del archivo no equivale por sí sola a firma completa.',
 'colectivo_convenio',true,20,'RLA-MOPR arts. 56-58 / Bloque 5',true)
ON CONFLICT (codigo) DO NOTHING;
ALTER TABLE requisito_documental ENABLE TRIGGER trg_audit_requisito_documental;

-- Una fecha histórica sólo crea una tarea pendiente de validación; nunca una
-- firma acreditada. Se preservan requisitos existentes más fuertes.
ALTER TABLE expediente_requisito DISABLE TRIGGER trg_audit_expediente_requisito;
INSERT INTO expediente_requisito(
    id_proyecto_nucleo,id_requisito,id_estado,id_documento,detalle,activo,
    entidad_tipo,entidad_id
)
SELECT c.id_proyecto_nucleo,r.id_requisito,e.id_catalogo_opcion,NULL,
       'Backfill 007: fecha histórica presente; firma y soporte pendientes de validación.',
       true,'convenio',c.id_convenio
FROM convenio c
JOIN requisito_documental r ON r.codigo = CASE
    WHEN c.ambito='individual' THEN 'ind_convenio_firmado'
    ELSE 'col_convenio_firmado' END AND r.activo
JOIN catalogo_operativo e ON e.tipo_catalogo='estado_requisito_documental'
    AND e.codigo='pendiente_validacion' AND e.activo
WHERE c.activo AND c.fecha_firma IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM expediente_requisito er
      WHERE er.activo AND er.entidad_tipo='convenio' AND er.entidad_id=c.id_convenio
        AND er.id_requisito=r.id_requisito
  );
ALTER TABLE expediente_requisito ENABLE TRIGGER trg_audit_expediente_requisito;

CREATE OR REPLACE FUNCTION fn_validar_compareciente() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_ambito varchar(20); v_pn integer; v_nucleo integer; v_persona_titular integer;
    v_nucleo_parcela integer; v_titular_inicio date; v_titular_fin date;
    v_fecha_firma date; v_orv_vigente boolean := false;
    v_acreditacion_historica boolean := false; v_documento_acreditacion boolean := false;
BEGIN
    IF NOT NEW.activo THEN RETURN NEW; END IF;
    SELECT c.ambito,c.id_proyecto_nucleo,pn.id_nucleo,c.fecha_firma
      INTO v_ambito,v_pn,v_nucleo,v_fecha_firma
      FROM convenio c JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
     WHERE c.id_convenio=NEW.id_convenio AND c.activo AND pn.activo;
    IF v_pn IS NULL THEN RAISE EXCEPTION '007: convenio del compareciente inexistente o inactivo'; END IF;
    IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_calidad,'calidad_compareciente_convenio') THEN
        RAISE EXCEPTION '007: calidad de compareciente invalida';
    END IF;

    IF v_ambito='individual' THEN
        IF NEW.id_tipo_acreditacion IS NOT NULL
           AND NOT fn_opcion_catalogo_valida(NEW.id_tipo_acreditacion,'tipo_acreditacion_derecho_individual') THEN
            RAISE EXCEPTION '039: tipo de acreditacion individual invalido';
        END IF;
        IF NEW.id_parcela_titular IS NOT NULL THEN
            SELECT pt.id_persona,p.id_nucleo,pt.fecha_inicio,pt.fecha_fin
              INTO v_persona_titular,v_nucleo_parcela,v_titular_inicio,v_titular_fin
              FROM parcela_titular pt JOIN parcela p ON p.id_parcela=pt.id_parcela
             WHERE pt.id_parcela_titular=NEW.id_parcela_titular AND pt.activo AND p.activo;
            IF v_persona_titular IS NULL THEN RAISE EXCEPTION '039: ParcelaTitular del compareciente inexistente o inactivo'; END IF;
            IF v_persona_titular IS DISTINCT FROM NEW.id_persona THEN RAISE EXCEPTION '039: ParcelaTitular no pertenece a la persona compareciente'; END IF;
            IF v_nucleo_parcela IS DISTINCT FROM v_nucleo THEN RAISE EXCEPTION '039: la parcela del compareciente no pertenece al NucleoAgrario del ProyectoNucleo'; END IF;
            IF v_fecha_firma IS NOT NULL AND v_titular_inicio IS NOT NULL AND v_fecha_firma<v_titular_inicio THEN RAISE EXCEPTION '039: la titularidad inicia despues de la fecha de firma del convenio'; END IF;
            IF v_fecha_firma IS NOT NULL AND v_titular_fin IS NOT NULL AND v_fecha_firma>v_titular_fin THEN RAISE EXCEPTION '039: la titularidad termino antes de la fecha de firma del convenio'; END IF;
        END IF;
        IF NEW.es_firmante AND NEW.id_parcela_titular IS NULL AND NEW.id_tipo_acreditacion IS NULL THEN
            RAISE EXCEPTION '039: firmante individual requiere ParcelaTitular o acreditacion alternativa';
        END IF;
    ELSIF v_ambito='colectivo' THEN
        IF NEW.id_parcela_titular IS NOT NULL THEN
            RAISE EXCEPTION '007: compareciente colectivo no usa ParcelaTitular';
        END IF;
        IF NEW.id_tipo_acreditacion IS NOT NULL
           AND NOT fn_opcion_catalogo_valida(NEW.id_tipo_acreditacion,'tipo_acreditacion_compareciente_colectivo') THEN
            RAISE EXCEPTION '007: tipo de acreditacion colectiva invalido';
        END IF;
        IF v_fecha_firma IS NOT NULL THEN
            SELECT EXISTS (
                SELECT 1 FROM orv_integrante oi JOIN orv o ON o.id_orv=oi.id_orv
                WHERE oi.id_persona=NEW.id_persona AND oi.activo AND o.activo
                  AND o.id_nucleo=v_nucleo
                  AND (oi.fecha_inicio IS NULL OR oi.fecha_inicio<=v_fecha_firma)
                  AND (oi.fecha_fin IS NULL OR oi.fecha_fin>=v_fecha_firma)
                  AND (o.inicio_vigencia IS NULL OR o.inicio_vigencia<=v_fecha_firma)
                  AND (o.fin_vigencia IS NULL OR o.fin_vigencia>=v_fecha_firma)
            ) INTO v_orv_vigente;
        END IF;
        v_acreditacion_historica := NEW.id_tipo_acreditacion IS NOT NULL
            AND NULLIF(btrim(NEW.referencia_acreditacion),'') IS NOT NULL
            AND NEW.fecha_acreditacion IS NOT NULL
            AND v_fecha_firma IS NOT NULL
            AND NEW.fecha_acreditacion<=v_fecha_firma;
        SELECT EXISTS (
            SELECT 1 FROM documento_vinculo dv
            JOIN documento d ON d.id_documento=dv.id_documento
            WHERE dv.activo AND d.activo AND d.estado='disponible'
              AND dv.entidad_tipo='convenio_compareciente'
              AND dv.entidad_id=NEW.id_compareciente
        ) INTO v_documento_acreditacion;
        IF NEW.es_firmante AND NOT v_orv_vigente
           AND NOT (v_acreditacion_historica AND v_documento_acreditacion)
           AND NOT NEW.requiere_revision THEN
            RAISE EXCEPTION '007: firmante colectivo requiere ORV vigente al acto, acreditacion externa documentada o revision explicita';
        END IF;
    ELSE
        RAISE EXCEPTION '007: ambito de convenio invalido';
    END IF;

    IF NEW.es_firmante AND NEW.id_parcela_titular IS NULL
       AND NEW.id_tipo_acreditacion IS NOT NULL
       AND NULLIF(btrim(NEW.referencia_acreditacion),'') IS NULL
       AND NOT NEW.requiere_revision THEN
        RAISE EXCEPTION '007: acreditacion sin referencia debe quedar explicitamente en revision';
    END IF;
    RETURN NEW;
END $$;

-- Evaluación vigente para reporting. No convierte fecha/referencia en firma:
-- exige requisito y documento disponibles, firmantes sin revisión y, para cada
-- firmante colectivo, ORV histórica o acreditación externa documentada.
CREATE OR REPLACE FUNCTION fn_convenio_firma_acreditada_007(p_id_convenio integer)
RETURNS boolean LANGUAGE sql STABLE
SET search_path = public, pg_catalog AS $$
SELECT EXISTS (
    SELECT 1 FROM convenio c
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
    WHERE c.id_convenio=p_id_convenio AND c.activo AND pn.activo
      AND c.fecha_firma IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM expediente_requisito er
        JOIN requisito_documental r ON r.id_requisito=er.id_requisito AND r.activo
        JOIN catalogo_operativo ec ON ec.id_catalogo_opcion=er.id_estado
        JOIN documento d ON d.id_documento=er.id_documento
        WHERE er.activo AND er.entidad_tipo='convenio' AND er.entidad_id=c.id_convenio
          AND ((c.ambito='individual' AND r.codigo='ind_convenio_firmado')
            OR (c.ambito='colectivo' AND r.codigo='col_convenio_firmado'))
          AND ec.tipo_catalogo='estado_requisito_documental'
          AND ec.codigo='disponible' AND ec.activo
          AND d.activo AND d.estado='disponible'
      )
      AND EXISTS (
        SELECT 1 FROM convenio_compareciente cc
        WHERE cc.id_convenio=c.id_convenio AND cc.activo AND cc.es_firmante
      )
      AND NOT EXISTS (
        SELECT 1 FROM convenio_compareciente cc
        WHERE cc.id_convenio=c.id_convenio AND cc.activo AND cc.es_firmante
          AND (cc.requiere_revision OR (c.ambito='colectivo' AND NOT (
            EXISTS (
              SELECT 1 FROM orv_integrante oi JOIN orv o ON o.id_orv=oi.id_orv
              WHERE oi.id_persona=cc.id_persona AND oi.activo AND o.activo
                AND o.id_nucleo=pn.id_nucleo
                AND (oi.fecha_inicio IS NULL OR oi.fecha_inicio<=c.fecha_firma)
                AND (oi.fecha_fin IS NULL OR oi.fecha_fin>=c.fecha_firma)
                AND (o.inicio_vigencia IS NULL OR o.inicio_vigencia<=c.fecha_firma)
                AND (o.fin_vigencia IS NULL OR o.fin_vigencia>=c.fecha_firma)
            ) OR (
              cc.id_tipo_acreditacion IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM catalogo_operativo ac
                WHERE ac.id_catalogo_opcion=cc.id_tipo_acreditacion AND ac.activo
                  AND ac.tipo_catalogo='tipo_acreditacion_compareciente_colectivo'
              )
              AND NULLIF(btrim(cc.referencia_acreditacion),'') IS NOT NULL
              AND cc.fecha_acreditacion IS NOT NULL
              AND cc.fecha_acreditacion<=c.fecha_firma
              AND EXISTS (
                SELECT 1 FROM documento_vinculo dv
                JOIN documento d ON d.id_documento=dv.id_documento
                WHERE dv.activo AND d.activo AND d.estado='disponible'
                  AND dv.entidad_tipo='convenio_compareciente'
                  AND dv.entidad_id=cc.id_compareciente
              )
            )
          )))
      )
);
$$;

GRANT EXECUTE ON FUNCTION fn_convenio_firma_acreditada_007(integer)
TO software_pa_app;

-- Se recrean literalmente las vistas 006, en orden de dependencia.
DO $$
DECLARE v record;
BEGIN
    FOR v IN SELECT * FROM _007_vistas_006 ORDER BY orden LOOP
        EXECUTE format('CREATE VIEW %I AS %s',v.nombre,v.definicion);
        IF v.comentario IS NOT NULL THEN
            EXECUTE format('COMMENT ON VIEW %I IS %L',v.nombre,v.comentario);
        END IF;
        EXECUTE format('ALTER VIEW %I OWNER TO %I',v.nombre,v.propietario);
    END LOOP;
    FOR v IN SELECT * FROM _007_permisos_vistas LOOP
        EXECUTE format('GRANT %s ON %I TO %s%s',v.privilege_type,v.nombre,
            CASE WHEN v.grantee='PUBLIC' THEN 'PUBLIC' ELSE quote_ident(v.grantee) END,
            CASE WHEN v.is_grantable='YES' THEN ' WITH GRANT OPTION' ELSE '' END);
    END LOOP;
END $$;

COMMENT ON VIEW vw_hito_seguimiento IS
    'Compatibilidad 006: superficie_ha y monto conservan valores declarados históricos, no impactos 007.';
COMMENT ON VIEW vw_reporte_avance_periodo IS
    'Compatibilidad 006: no sustituir por subtotales 007; usar vistas de impacto para nuevas métricas.';
COMMENT ON VIEW vw_dashboard_kpi IS
    'Compatibilidad 006: no sustituir por subtotales 007; usar vistas de impacto para nuevas métricas.';

-- Un registro por instrumento y concepto declarado; 90%, 100% y BDT son
-- universos paralelos y nunca se suman entre sí.
CREATE VIEW vw_convenio_valor_declarado AS
WITH firma AS (
    SELECT c.id_convenio,
           fn_convenio_firma_acreditada_007(c.id_convenio) firma_acreditada
    FROM convenio c
)
SELECT pn.id_proyecto,e.id_entidad,c.id_proyecto_nucleo,c.id_convenio,c.ambito,
       vco.tipo_cop_operativo_codigo tipo_cop_operativo,c.tipo_convenio,
       x.concepto,x.unidad,x.valor_declarado,c.fecha_firma fecha_instrumento_reportada,
       f.firma_acreditada
FROM convenio c JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo
JOIN municipio m ON m.id_municipio=n.id_municipio
JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
JOIN firma f ON f.id_convenio=c.id_convenio
LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio=c.id_convenio
CROSS JOIN LATERAL (VALUES
    ('superficie_declarada','ha',c.superficie_ha::numeric),
    ('monto_90_declarado','MXN',c.monto_90::numeric),
    ('monto_100_declarado','MXN',c.monto_100::numeric),
    ('monto_bdt_declarado','MXN',c.monto_bdt::numeric)
) x(concepto,unidad,valor_declarado)
WHERE c.activo AND pn.activo AND x.valor_declarado IS NOT NULL;

COMMENT ON VIEW vw_convenio_valor_declarado IS
    'Valores literales declarados por instrumento y unidad; no son impacto ni total consolidado.';

-- Superficie: una fila por ConvenioAfectacion. Monto: una fila por Convenio;
-- por diseño no existe join N:M en las ramas económicas.
CREATE VIEW vw_convenio_impacto AS
WITH firma AS (
    SELECT c.id_convenio,
           fn_convenio_firma_acreditada_007(c.id_convenio) firma_acreditada
    FROM convenio c
), base AS (
    SELECT c.*,pn.id_proyecto,e.id_entidad,vco.tipo_cop_operativo_codigo,f.firma_acreditada
    FROM convenio c JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
    JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo
    JOIN municipio m ON m.id_municipio=n.id_municipio
    JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
    JOIN firma f ON f.id_convenio=c.id_convenio
    LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio=c.id_convenio
    WHERE c.activo AND pn.activo
)
SELECT b.id_proyecto,b.id_entidad,b.id_proyecto_nucleo,b.id_convenio,
       ca.id_convenio_afectacion,ca.id_afectacion,b.ambito,
       b.tipo_cop_operativo_codigo tipo_cop_operativo,b.tipo_convenio,
       'superficie:'||ca.id_convenio_afectacion clave_impacto,
       'superficie'::text concepto,'ha'::text unidad,ca.efecto_superficie efecto,
       CASE WHEN b.firma_acreditada THEN b.fecha_firma END fecha_efecto,
       ca.superficie_impacto_ha::numeric valor_impacto,
       ca.efecto_superficie='pendiente' pendiente,b.firma_acreditada
FROM base b JOIN convenio_afectacion ca ON ca.id_convenio=b.id_convenio AND ca.activo
UNION ALL
SELECT b.id_proyecto,b.id_entidad,b.id_proyecto_nucleo,b.id_convenio,
       NULL::integer,NULL::integer,b.ambito,b.tipo_cop_operativo_codigo,b.tipo_convenio,
       'monto:'||b.id_convenio||':'||x.concepto,x.concepto,'MXN',b.efecto_monto,
       CASE WHEN b.firma_acreditada THEN b.fecha_firma END,
       x.valor_impacto,b.efecto_monto='pendiente',b.firma_acreditada
FROM base b
CROSS JOIN LATERAL (VALUES
    ('monto_90',b.monto_90::numeric,b.monto_90_impacto::numeric),
    ('monto_100',b.monto_100::numeric,b.monto_100_impacto::numeric),
    ('monto_bdt',b.monto_bdt::numeric,b.monto_bdt_impacto::numeric)
) x(concepto,valor_declarado,valor_impacto)
WHERE x.valor_declarado IS NOT NULL OR x.valor_impacto IS NOT NULL
UNION ALL
-- Si ni siquiera se conoce el universo 90/100/BDT, se conserva un pendiente
-- económico por instrumento; no se fabrican tres importes cero.
SELECT b.id_proyecto,b.id_entidad,b.id_proyecto_nucleo,b.id_convenio,
       NULL::integer,NULL::integer,b.ambito,b.tipo_cop_operativo_codigo,b.tipo_convenio,
       'monto:'||b.id_convenio||':pendiente_clasificar','monto_pendiente_clasificar','MXN',
       b.efecto_monto,CASE WHEN b.firma_acreditada THEN b.fecha_firma END,
       NULL::numeric,true,b.firma_acreditada
FROM base b
WHERE b.efecto_monto='pendiente'
  AND b.monto_90 IS NULL AND b.monto_100 IS NULL AND b.monto_bdt IS NULL
  AND b.monto_90_impacto IS NULL AND b.monto_100_impacto IS NULL
  AND b.monto_bdt_impacto IS NULL;

COMMENT ON VIEW vw_convenio_impacto IS
    'Impactos separados: superficie por ConvenioAfectacion y montos por instrumento/concepto; NULL pendiente nunca equivale a cero.';

CREATE VIEW vw_reporte_convenio_impacto_periodo AS
SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,
       concepto,unidad,efecto,
       extract(year FROM fecha_efecto)::integer anio,
       extract(month FROM fecha_efecto)::integer mes,
       extract(quarter FROM fecha_efecto)::integer trimestre,
       count(DISTINCT clave_impacto)::bigint cantidad,
       sum(valor_impacto)::numeric valor_impacto
FROM vw_convenio_impacto
WHERE firma_acreditada AND NOT pendiente AND fecha_efecto IS NOT NULL
  AND valor_impacto IS NOT NULL
GROUP BY id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,
         concepto,unidad,efecto,extract(year FROM fecha_efecto),
         extract(month FROM fecha_efecto),extract(quarter FROM fecha_efecto);

COMMENT ON VIEW vw_reporte_convenio_impacto_periodo IS
    'Subtotales conocidos por periodo, concepto, unidad y efecto; excluye pendientes y firmas no acreditadas, por lo que no es un total definitivo.';

CREATE VIEW vw_convenio_cobertura_impacto AS
SELECT id_proyecto,id_entidad,ambito,concepto,unidad,
       count(DISTINCT clave_impacto)::bigint universo,
       count(DISTINCT clave_impacto) FILTER(
           WHERE NOT pendiente AND valor_impacto IS NOT NULL
       )::bigint clasificados,
       count(DISTINCT clave_impacto) FILTER(WHERE pendiente)::bigint pendientes,
       count(DISTINCT clave_impacto) FILTER(WHERE NOT firma_acreditada)::bigint sin_firma_acreditada
FROM vw_convenio_impacto
GROUP BY id_proyecto,id_entidad,ambito,concepto,unidad;

COMMENT ON VIEW vw_convenio_cobertura_impacto IS
    'Cobertura del universo de impactos con clasificados, pendientes y sin firma acreditada; acompaña a todo subtotal conocido.';

GRANT SELECT ON vw_proyecto_nucleo_resumen,
    vw_hito_seguimiento_005,vw_hito_seguimiento,
    vw_reporte_avance_periodo,vw_dashboard_kpi,vw_reporte_snapshot_actual,
    vw_convenio_valor_declarado,vw_convenio_impacto,
    vw_reporte_convenio_impacto_periodo,vw_convenio_cobertura_impacto
TO software_pa_app;
