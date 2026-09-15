-- Normaliza el contexto de Asamblea para ciclos de superficie adicional (ADICIONAL y 2A_ADICIONAL).
-- contexto_asamblea = modificatorio para autorizar convenios modificatorios.
-- Depreca la opcion contexto_asamblea/superficie_adicional en catalogo_operativo.
SET search_path = public, pg_catalog;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM schema_migrations
        WHERE version = '016'
          AND checksum_sha256 = '246eb8247d1f3256e40453afa5f5d13d09586d90f0d3e599680ed8865160c810'
    ) THEN
        RAISE EXCEPTION '017 requiere la migracion 016 exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '017') THEN
        RAISE EXCEPTION '017 ya se encuentra registrada';
    END IF;
END $$;

SELECT pg_advisory_xact_lock(
    hashtextextended('software-pa:017:normalizar-contexto-asamblea-adicional', 0)
);

LOCK TABLE asamblea IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE catalogo_operativo, convenio IN SHARE MODE;

DO $$
DECLARE
    v_ctx_cop_original bigint;
    v_ctx_modificatorio bigint;
    v_ctx_superficie_adicional bigint;
    v_cop_adicional bigint;
    v_cop_2a_adicional bigint;
    v_ids text;
BEGIN
    -- 1. Validar unicidad y existencia de opciones canonicas en catalogo_operativo
    IF (SELECT count(*) FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'cop_original' AND activo) <> 1 THEN
        RAISE EXCEPTION '017: opcion contexto_asamblea/cop_original inexistente o no unica';
    END IF;
    SELECT id_catalogo_opcion INTO STRICT v_ctx_cop_original
      FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'cop_original' AND activo;

    IF (SELECT count(*) FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'modificatorio' AND activo) <> 1 THEN
        RAISE EXCEPTION '017: opcion contexto_asamblea/modificatorio inexistente o no unica';
    END IF;
    SELECT id_catalogo_opcion INTO STRICT v_ctx_modificatorio
      FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'modificatorio' AND activo;

    IF (SELECT count(*) FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional' AND activo) <> 1 THEN
        RAISE EXCEPTION '017: opcion contexto_asamblea/superficie_adicional inexistente o no unica';
    END IF;
    SELECT id_catalogo_opcion INTO STRICT v_ctx_superficie_adicional
      FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional' AND activo;

    IF (SELECT count(*) FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = 'ADICIONAL' AND activo) <> 1 THEN
        RAISE EXCEPTION '017: opcion tipo_cop_operativo/ADICIONAL inexistente o no unica';
    END IF;
    SELECT id_catalogo_opcion INTO STRICT v_cop_adicional
      FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = 'ADICIONAL' AND activo;

    IF (SELECT count(*) FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = '2A_ADICIONAL' AND activo) <> 1 THEN
        RAISE EXCEPTION '017: opcion tipo_cop_operativo/2A_ADICIONAL inexistente o no unica';
    END IF;
    SELECT id_catalogo_opcion INTO STRICT v_cop_2a_adicional
      FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = '2A_ADICIONAL' AND activo;

    -- 2. PREFLIGHT: Abortar si existe Asamblea ADICIONAL o 2A_ADICIONAL vinculada a un convenio activo cuyo tipo_convenio <> 'modificatorio'
    SELECT string_agg(DISTINCT a.id_asamblea::text, ',' ORDER BY a.id_asamblea::text)
      INTO v_ids
      FROM asamblea a
      JOIN convenio c ON c.id_asamblea_autorizacion = a.id_asamblea AND c.activo
     WHERE a.id_tipo_cop_operativo IN (v_cop_adicional, v_cop_2a_adicional)
       AND c.tipo_convenio IS DISTINCT FROM 'modificatorio';

    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '017 abortada: asambleas ADICIONAL/2A_ADICIONAL vinculadas a convenios no modificatorios: %', v_ids;
    END IF;

    -- PREFLIGHT: Abortar si alguna Asamblea ADICIONAL/2A_ADICIONAL tiene un contexto activo inesperado
    SELECT string_agg(DISTINCT a.id_asamblea::text, ',' ORDER BY a.id_asamblea::text)
      INTO v_ids
      FROM asamblea a
      JOIN catalogo_operativo ctx ON ctx.id_catalogo_opcion = a.id_contexto_asamblea
     WHERE a.id_tipo_cop_operativo IN (v_cop_adicional, v_cop_2a_adicional)
       AND a.id_contexto_asamblea IS NOT NULL
       AND (
           ctx.tipo_catalogo IS DISTINCT FROM 'contexto_asamblea'
           OR ctx.codigo NOT IN ('cop_original', 'modificatorio', 'superficie_adicional', 'otro')
       );

    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '017 abortada: asambleas ADICIONAL/2A_ADICIONAL con contexto inesperado: %', v_ids;
    END IF;

    -- PREFLIGHT: Abortar si alguna Asamblea ACTIVA tiene contexto_asamblea='superficie_adicional'
    -- y su ciclo NO es ADICIONAL ni 2A_ADICIONAL (ej. NULL, ORIGEN, COMPLEMENTARIAS, etc.)
    SELECT string_agg(DISTINCT a.id_asamblea::text, ',' ORDER BY a.id_asamblea::text)
      INTO v_ids
      FROM asamblea a
     WHERE a.activo
       AND a.id_contexto_asamblea = v_ctx_superficie_adicional
       AND (
           a.id_tipo_cop_operativo IS NULL
           OR a.id_tipo_cop_operativo NOT IN (v_cop_adicional, v_cop_2a_adicional)
       );

    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '017 abortada: asambleas activas con contexto superficie_adicional y ciclo no normalizable: %', v_ids;
    END IF;
END $$;

-- 3. NORMALIZAR ASAMBLEAS ADICIONAL / 2A_ADICIONAL
-- Se desactiva el trigger de auditoria durante el backfill para evitar fabricar un actor de aplicacion inexistente.
ALTER TABLE asamblea DISABLE TRIGGER trg_audit_asamblea;

UPDATE asamblea
   SET id_contexto_asamblea = (
       SELECT id_catalogo_opcion
         FROM catalogo_operativo
        WHERE tipo_catalogo = 'contexto_asamblea'
          AND codigo = 'modificatorio'
          AND activo
   )
 WHERE id_tipo_cop_operativo IN (
       SELECT id_catalogo_opcion
         FROM catalogo_operativo
        WHERE tipo_catalogo = 'tipo_cop_operativo'
          AND codigo IN ('ADICIONAL', '2A_ADICIONAL')
          AND activo
   )
   AND id_contexto_asamblea IN (
       SELECT id_catalogo_opcion
         FROM catalogo_operativo
        WHERE tipo_catalogo = 'contexto_asamblea'
          AND codigo IN ('cop_original', 'superficie_adicional')
   );

SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE asamblea ENABLE TRIGGER trg_audit_asamblea;

-- 4. GUARDA ANTES DE DEPRECAR: Comprobar que 0 asambleas activas referencien contexto_asamblea superficie_adicional
DO $$
DECLARE
    v_ids text;
BEGIN
    SELECT string_agg(DISTINCT a.id_asamblea::text, ',' ORDER BY a.id_asamblea::text)
      INTO v_ids
      FROM asamblea a
      JOIN catalogo_operativo ctx ON ctx.id_catalogo_opcion = a.id_contexto_asamblea
     WHERE a.activo
       AND ctx.tipo_catalogo = 'contexto_asamblea'
       AND ctx.codigo = 'superficie_adicional';

    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '017 abortada: existen asambleas activas que referencian contexto_asamblea superficie_adicional antes de deprecacion: %', v_ids;
    END IF;
END $$;

-- 5. DEPRECAR CATALOGO LEGADO contexto_asamblea/superficie_adicional
-- Se actualiza chk_catalogo_operativo_baja para admitir id_usuario_baja NULL unicamente
-- como excepcion acotada para la migracion de sistema de superficie_adicional en schema 017.
ALTER TABLE catalogo_operativo DROP CONSTRAINT chk_catalogo_operativo_baja;
ALTER TABLE catalogo_operativo ADD CONSTRAINT chk_catalogo_operativo_baja CHECK (
    (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
    OR
    (
        NOT activo
        AND fecha_baja IS NOT NULL
        AND NULLIF(btrim(motivo_baja), '') IS NOT NULL
        AND (
            id_usuario_baja IS NOT NULL
            OR
            (
                tipo_catalogo = 'contexto_asamblea'
                AND codigo = 'superficie_adicional'
                AND id_usuario_baja IS NULL
                AND motivo_baja = 'Deprecado por normalización del modelo en schema 017'
            )
        )
    )
);

ALTER TABLE catalogo_operativo DISABLE TRIGGER trg_audit_catalogo_operativo;

UPDATE catalogo_operativo
   SET activo = false,
       vigencia_fin = CURRENT_DATE,
       fecha_baja = now(),
       id_usuario_baja = NULL,
       motivo_baja = 'Deprecado por normalización del modelo en schema 017',
       observaciones = CASE
           WHEN observaciones IS NULL OR btrim(observaciones) = '' THEN
               'Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL.'
           WHEN observaciones LIKE '%Para superficie adicional usar contexto_asamblea=modificatorio%' THEN
               observaciones
           ELSE
               btrim(observaciones) || ' | Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL.'
       END
 WHERE tipo_catalogo = 'contexto_asamblea'
   AND codigo = 'superficie_adicional'
   AND activo;

SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE catalogo_operativo ENABLE TRIGGER trg_audit_catalogo_operativo;

-- 6. POSTCONDICIONES
DO $$
DECLARE
    v_ctx_cop_original bigint;
    v_ctx_modificatorio bigint;
    v_ctx_superficie_adicional bigint;
    v_cop_adicional bigint;
    v_cop_2a_adicional bigint;
    v_cop_origen bigint;
BEGIN
    SELECT id_catalogo_opcion INTO STRICT v_ctx_cop_original
      FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'cop_original';

    SELECT id_catalogo_opcion INTO STRICT v_ctx_modificatorio
      FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'modificatorio';

    SELECT id_catalogo_opcion INTO STRICT v_ctx_superficie_adicional
      FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional';

    SELECT id_catalogo_opcion INTO STRICT v_cop_adicional
      FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = 'ADICIONAL';

    SELECT id_catalogo_opcion INTO STRICT v_cop_2a_adicional
      FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = '2A_ADICIONAL';

    SELECT id_catalogo_opcion INTO STRICT v_cop_origen
      FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = 'ORIGEN';

    -- A. No existe Asamblea activa con ciclo ADICIONAL/2A_ADICIONAL y contexto cop_original o superficie_adicional
    IF EXISTS (
        SELECT 1
          FROM asamblea
         WHERE activo
           AND id_tipo_cop_operativo IN (v_cop_adicional, v_cop_2a_adicional)
           AND id_contexto_asamblea IN (v_ctx_cop_original, v_ctx_superficie_adicional)
    ) THEN
        RAISE EXCEPTION '017 postcondicion A violada: quedan asambleas adicionales con contexto sin normalizar';
    END IF;

    -- B. Todas las asambleas activas ADICIONAL/2A_ADICIONAL normalizadas tienen modificatorio
    IF EXISTS (
        SELECT 1
          FROM asamblea
         WHERE activo
           AND id_tipo_cop_operativo IN (v_cop_adicional, v_cop_2a_adicional)
           AND id_contexto_asamblea IS NOT NULL
           AND id_contexto_asamblea <> v_ctx_modificatorio
           AND id_contexto_asamblea NOT IN (SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'otro')
    ) THEN
        RAISE EXCEPTION '017 postcondicion B violada: asamblea adicional con contexto distinto de modificatorio';
    END IF;

    -- C. La opcion contexto_asamblea/superficie_adicional queda inactiva con id_usuario_baja NULL y motivo neutral
    IF EXISTS (
        SELECT 1
          FROM catalogo_operativo
         WHERE id_catalogo_opcion = v_ctx_superficie_adicional
           AND (
               activo IS NOT FALSE
               OR id_usuario_baja IS NOT NULL
               OR motivo_baja <> 'Deprecado por normalización del modelo en schema 017'
               OR fecha_baja IS NULL
           )
    ) THEN
        RAISE EXCEPTION '017 postcondicion C violada: superficie_adicional no quedo inactiva con baja de sistema';
    END IF;

    -- D. Cero asambleas activas referencian contexto_asamblea superficie_adicional
    IF EXISTS (
        SELECT 1
          FROM asamblea
         WHERE activo
           AND id_contexto_asamblea = v_ctx_superficie_adicional
    ) THEN
        RAISE EXCEPTION '017 postcondicion D violada: existen asambleas activas con contexto superficie_adicional';
    END IF;

    -- E. ADICIONAL sigue activo
    IF (
        SELECT activo
          FROM catalogo_operativo
         WHERE id_catalogo_opcion = v_cop_adicional
    ) IS NOT TRUE THEN
        RAISE EXCEPTION '017 postcondicion E violada: ADICIONAL no esta activo';
    END IF;

    -- F. 2A_ADICIONAL sigue activo
    IF (
        SELECT activo
          FROM catalogo_operativo
         WHERE id_catalogo_opcion = v_cop_2a_adicional
    ) IS NOT TRUE THEN
        RAISE EXCEPTION '017 postcondicion F violada: 2A_ADICIONAL no esta activo';
    END IF;

    -- G. Las Asambleas ORIGEN conservan cop_original
    IF EXISTS (
        SELECT 1
          FROM asamblea
         WHERE activo
           AND id_tipo_cop_operativo = v_cop_origen
           AND id_contexto_asamblea IS NOT NULL
           AND id_contexto_asamblea <> v_ctx_cop_original
           AND id_contexto_asamblea NOT IN (SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo IN ('otro', 'retiro_fondos'))
    ) THEN
        RAISE EXCEPTION '017 postcondicion G violada: asambleas ORIGEN modificadas indebidamente';
    END IF;
END $$;
