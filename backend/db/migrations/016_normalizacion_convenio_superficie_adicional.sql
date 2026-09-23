-- Normaliza la naturaleza juridica de los convenios de superficie adicional.
-- ADICIONAL y 2A_ADICIONAL permanecen como clasificacion operativa en Afectacion.
SET search_path = public, pg_catalog;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM schema_migrations
        WHERE version = '015'
          AND checksum_sha256 = '4e5d7fa8926f8026923146d3a0695d933bb43e9bb5f8c71ef8f9ecd9bae4b422'
    ) THEN
        RAISE EXCEPTION '016 requiere la migracion 015 exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '016') THEN
        RAISE EXCEPTION '016 ya se encuentra registrada';
    END IF;
    IF to_regclass('public.vw_convenio_tipo_cop_operativo') IS NULL
       OR to_regclass('public.vw_hito_seguimiento_005') IS NULL
       OR to_regclass('public.vw_hito_seguimiento_007') IS NULL
       OR to_regclass('public.vw_hito_seguimiento') IS NULL
       OR to_regclass('public.vw_reporte_avance_periodo') IS NULL
       OR to_regclass('public.vw_dashboard_kpi') IS NULL THEN
        RAISE EXCEPTION '016 requiere las vistas efectivas de reporting de 015';
    END IF;
END $$;

SELECT pg_advisory_xact_lock(
    hashtextextended('software-pa:016:normalizacion-convenio-superficie-adicional', 0)
);

-- Impide que cambien convenios, relaciones o catalogos entre las guardas y el
-- backfill. El runner ejecuta todo el archivo en una unica transaccion.
LOCK TABLE convenio IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE convenio_afectacion, afectacion, catalogo_operativo, asamblea IN SHARE MODE;

DO $$
DECLARE
    v_ids text;
BEGIN
    IF (
        SELECT count(*)
        FROM catalogo_operativo
        WHERE tipo_catalogo = 'tipo_cop_operativo'
          AND codigo IN ('ADICIONAL', '2A_ADICIONAL')
          AND activo
    ) <> 2 THEN
        RAISE EXCEPTION '016 requiere ADICIONAL y 2A_ADICIONAL activos y unicos';
    END IF;

    -- Una relacion activa debe apuntar a una afectacion activa del mismo PN y
    -- ambito. Cada convenio conserva exactamente una relacion principal activa.
    SELECT string_agg(id_convenio::text, ',' ORDER BY id_convenio)
      INTO v_ids
      FROM (
        SELECT c.id_convenio
        FROM convenio c
        LEFT JOIN convenio_afectacion ca
          ON ca.id_convenio = c.id_convenio AND ca.activo
        LEFT JOIN afectacion a ON a.id_afectacion = ca.id_afectacion
        WHERE c.tipo_convenio = 'superficie_adicional'
        GROUP BY c.id_convenio, c.id_proyecto_nucleo, c.ambito
        HAVING count(ca.id_convenio_afectacion) = 0
            OR count(*) FILTER (WHERE ca.rol = 'principal') <> 1
            OR bool_or(
                a.id_afectacion IS NULL
                OR a.activo IS NOT TRUE
                OR a.id_proyecto_nucleo IS DISTINCT FROM c.id_proyecto_nucleo
                OR a.tipo_afectacion IS DISTINCT FROM c.ambito
            )
      ) relaciones_invalidas;
    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '016 abortada: relaciones contradictorias en convenios %', v_ids;
    END IF;

    SELECT string_agg(DISTINCT c.id_convenio::text, ',' ORDER BY c.id_convenio::text)
      INTO v_ids
      FROM convenio c
      JOIN convenio_afectacion ca
        ON ca.id_convenio = c.id_convenio AND ca.activo
      JOIN afectacion a
        ON a.id_afectacion = ca.id_afectacion AND a.activo
     WHERE c.tipo_convenio = 'superficie_adicional'
       AND a.id_tipo_cop_operativo IS NULL;
    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '016 abortada: ciclo NULL en convenios %', v_ids;
    END IF;

    SELECT string_agg(id_convenio::text, ',' ORDER BY id_convenio)
      INTO v_ids
      FROM (
        SELECT c.id_convenio
        FROM convenio c
        JOIN convenio_afectacion ca
          ON ca.id_convenio = c.id_convenio AND ca.activo
        JOIN afectacion a
          ON a.id_afectacion = ca.id_afectacion AND a.activo
        WHERE c.tipo_convenio = 'superficie_adicional'
        GROUP BY c.id_convenio
        HAVING count(DISTINCT a.id_tipo_cop_operativo) <> 1
      ) ciclos_multiples;
    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '016 abortada: multiples ciclos en convenios %', v_ids;
    END IF;

    SELECT string_agg(DISTINCT c.id_convenio::text, ',' ORDER BY c.id_convenio::text)
      INTO v_ids
      FROM convenio c
      JOIN convenio_afectacion ca
        ON ca.id_convenio = c.id_convenio AND ca.activo
      JOIN afectacion a
        ON a.id_afectacion = ca.id_afectacion AND a.activo
      LEFT JOIN catalogo_operativo cop
        ON cop.id_catalogo_opcion = a.id_tipo_cop_operativo
     WHERE c.tipo_convenio = 'superficie_adicional'
       AND (
           cop.tipo_catalogo IS DISTINCT FROM 'tipo_cop_operativo'
           OR cop.activo IS NOT TRUE
           OR cop.codigo NOT IN ('ADICIONAL', '2A_ADICIONAL')
       );
    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION
            '016 abortada: ciclo distinto de ADICIONAL/2A_ADICIONAL en convenios %',
            v_ids;
    END IF;

    -- La vista canonica debe resolver la misma clasificacion sin usar
    -- consecutivo. NULL incluye ausencia o ambiguedad operacional.
    SELECT string_agg(c.id_convenio::text, ',' ORDER BY c.id_convenio)
      INTO v_ids
      FROM convenio c
     LEFT JOIN vw_convenio_tipo_cop_operativo vco
        ON vco.id_convenio = c.id_convenio
     WHERE c.tipo_convenio = 'superficie_adicional'
       AND (
           vco.tipo_cop_operativo_codigo IS NULL
           OR vco.tipo_cop_operativo_codigo NOT IN ('ADICIONAL', '2A_ADICIONAL')
       );
    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '016 abortada: clasificacion operacional ambigua en convenios %', v_ids;
    END IF;

    -- Conserva las reglas de padre vigentes y exige que una Asamblea asociada
    -- sea compatible con la naturaleza juridica posterior al backfill.
    SELECT string_agg(DISTINCT c.id_convenio::text, ',' ORDER BY c.id_convenio::text)
      INTO v_ids
      FROM convenio c
      LEFT JOIN convenio padre ON padre.id_convenio = c.id_convenio_padre
      LEFT JOIN asamblea asm ON asm.id_asamblea = c.id_asamblea_autorizacion
      LEFT JOIN catalogo_operativo contexto
        ON contexto.id_catalogo_opcion = asm.id_contexto_asamblea
     WHERE c.tipo_convenio = 'superficie_adicional'
       AND (
           (c.id_convenio_padre IS NOT NULL AND (
               padre.id_convenio IS NULL
               OR padre.activo IS NOT TRUE
               OR padre.id_proyecto_nucleo IS DISTINCT FROM c.id_proyecto_nucleo
               OR padre.ambito IS DISTINCT FROM c.ambito
               OR padre.tipo_instrumento IS DISTINCT FROM 'convenio'
               OR padre.tipo_convenio NOT IN ('cop_original', 'superficie_adicional')
           ))
           OR (c.id_asamblea_autorizacion IS NOT NULL AND (
               c.ambito IS DISTINCT FROM 'colectivo'
               OR asm.id_asamblea IS NULL
               OR asm.activo IS NOT TRUE
               OR asm.id_proyecto_nucleo IS DISTINCT FROM c.id_proyecto_nucleo
               OR (
                   contexto.codigo IS NOT NULL
                   AND contexto.codigo NOT IN ('otro', 'modificatorio')
               )
           ))
       );
    IF v_ids IS NOT NULL THEN
        RAISE EXCEPTION '016 abortada: linaje o Asamblea contradictorios en convenios %', v_ids;
    END IF;
END $$;

-- Superficie adicional deja de tener una rama juridica propia. Las reglas
-- generales de padre, PN, ambito, Asamblea y deteccion de ciclos se conservan.
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
            RAISE EXCEPTION '007: el padre debe ser convenio activo del mismo ProyectoNucleo y ambito';
        END IF;
        IF NEW.tipo_convenio='cop_original'
           OR (NEW.tipo_convenio='obras_complementarias' AND v_padre.tipo_convenio NOT IN ('cop_original','obras_complementarias'))
           OR (NEW.tipo_convenio IN ('ampliacion','ampliacion_remanente') AND v_padre.tipo_convenio NOT IN ('cop_original','ampliacion')) THEN
            RAISE EXCEPTION '007: relacion padre/hijo no permitida para los tipos de convenio';
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
        ) THEN RAISE EXCEPTION '007: la relacion de convenios produciria un ciclo'; END IF;
    END IF;
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        SELECT * INTO v_asamblea FROM asamblea
         WHERE id_asamblea=NEW.id_asamblea_autorizacion AND activo;
        IF NEW.ambito IS DISTINCT FROM 'colectivo' OR v_asamblea.id_asamblea IS NULL
           OR v_asamblea.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo THEN
            RAISE EXCEPTION '007: la Asamblea solo autoriza convenios colectivos del mismo ProyectoNucleo';
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

CREATE OR REPLACE FUNCTION fn_validar_estado_antecedente_007() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    es_derivado boolean := NEW.tipo_instrumento = 'convenio'
        AND NEW.tipo_convenio IN ('modificatorio','obras_complementarias','ampliacion','ampliacion_remanente');
BEGIN
    IF NOT NEW.activo THEN RETURN NEW; END IF;
    IF NEW.estado_antecedente IS NULL
       OR (TG_OP='UPDATE'
           AND NEW.estado_antecedente IS NOT DISTINCT FROM OLD.estado_antecedente
           AND (NEW.tipo_instrumento IS DISTINCT FROM OLD.tipo_instrumento
                OR NEW.tipo_convenio IS DISTINCT FROM OLD.tipo_convenio
                OR NEW.id_convenio_padre IS DISTINCT FROM OLD.id_convenio_padre)) THEN
        NEW.estado_antecedente := CASE
            WHEN NEW.tipo_instrumento='convenio'
             AND NEW.tipo_convenio IN ('modificatorio','obras_complementarias','ampliacion','ampliacion_remanente')
             AND NEW.id_convenio_padre IS NOT NULL THEN 'vinculado'
            WHEN NEW.tipo_instrumento='convenio'
             AND NEW.tipo_convenio IN ('modificatorio','obras_complementarias','ampliacion','ampliacion_remanente')
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

-- El trigger de antecedente derivaria valores por el cambio de tipo. Se omite
-- exclusivamente durante este UPDATE para conservar el hecho historico. La
-- bitacora automatica tambien se omite: la version de schema documenta el
-- backfill y no se fabrica un actor de aplicacion.
ALTER TABLE convenio DISABLE TRIGGER trg_estado_antecedente_007;
ALTER TABLE convenio DISABLE TRIGGER trg_audit_convenio;

UPDATE convenio
   SET tipo_convenio = 'modificatorio'
 WHERE tipo_convenio = 'superficie_adicional';

ALTER TABLE convenio ENABLE TRIGGER trg_audit_convenio;
ALTER TABLE convenio ENABLE TRIGGER trg_estado_antecedente_007;

ALTER TABLE convenio DROP CONSTRAINT chk_convenio_tipo_ambito;
ALTER TABLE convenio ADD CONSTRAINT chk_convenio_tipo_ambito CHECK (
    (
        tipo_instrumento = 'otro'
        AND tipo_convenio IS NULL
        AND NULLIF(btrim(descripcion_instrumento), '') IS NOT NULL
    )
    OR (
        tipo_instrumento = 'convenio'
        AND (
            (
                ambito = 'colectivo'
                AND tipo_convenio IN ('cop_original','modificatorio','obras_complementarias')
            )
            OR (
                ambito = 'individual'
                AND tipo_convenio IN ('cop_original','modificatorio','ampliacion','ampliacion_remanente')
            )
        )
    )
);

-- La vista historica 005 conserva su definicion. Su envoltura 007 normaliza
-- solamente el indicador del hito directo de convenio. No usa consecutivo.
CREATE OR REPLACE VIEW vw_hito_seguimiento_007 AS
SELECT h.id_proyecto,
       h.id_entidad,
       h.id_proyecto_nucleo,
       h.ambito,
       h.tipo_cop_operativo,
       h.tipo_convenio,
       h.destino_superficie,
       h.clave_hito,
       CASE
           WHEN h.clave_hito LIKE 'convenio:%'
            AND h.tipo_convenio = 'modificatorio'
            AND h.tipo_cop_operativo IN ('ADICIONAL','2A_ADICIONAL')
               THEN 'superficie_adicional'::text
           ELSE h.indicador
       END AS indicador,
       h.fecha_programada,
       h.fecha_realizada,
       h.cantidad,
       h.superficie_ha,
       h.monto
FROM vw_hito_seguimiento_005 h
WHERE h.indicador NOT IN ('asambleas','retiro_fondos','ingreso_ran_acta','inscripcion_ran_acta','ingreso_ran_convenio','inscripcion_ran_convenio','fifonafe','informe_no_conflictos')
  AND h.indicador NOT LIKE 'sensibilizacion_%'
  AND h.indicador NOT LIKE 'caminamiento_%'
UNION ALL
SELECT pn.id_proyecto,e.id_entidad,pn.id_proyecto_nucleo,'colectivo'::text,c.codigo,NULL::text,NULL::text,
 'actividad:'||pn.id_proyecto_nucleo||':'||a.tipo_actividad||':'||coalesce(a.id_tipo_cop_operativo,0),
 a.tipo_actividad||'_'||coalesce(c.codigo,'SIN_CICLO'),min(a.fecha_programada),min(a.fecha_realizada),1::bigint,NULL::numeric,NULL::numeric
FROM actividad_campo a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio
JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN catalogo_operativo c ON c.id_catalogo_opcion=a.id_tipo_cop_operativo
WHERE a.activo AND pn.activo AND (a.fecha_programada IS NOT NULL OR a.fecha_realizada IS NOT NULL)
GROUP BY pn.id_proyecto,e.id_entidad,pn.id_proyecto_nucleo,a.tipo_actividad,a.id_tipo_cop_operativo,c.codigo
UNION ALL
SELECT pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,'colectivo'::text,cop.codigo,NULL::text,NULL::text,
 'asamblea:'||a.id_asamblea,'asambleas',min(ac.fecha_programada),min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada'),1::bigint,NULL::numeric,NULL::numeric
FROM asamblea a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo
JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
JOIN asamblea_convocatoria ac ON ac.id_asamblea=a.id_asamblea LEFT JOIN catalogo_operativo r ON r.id_catalogo_opcion=ac.id_resultado
LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo
LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
WHERE a.activo AND pn.activo AND ac.activo AND coalesce(ta.codigo,'')<>'retiro_fondos' AND coalesce(ca.codigo,'')<>'retiro_fondos'
GROUP BY pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,a.id_asamblea,cop.codigo
HAVING min(ac.fecha_programada) IS NOT NULL OR min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada') IS NOT NULL
UNION ALL
SELECT pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,'colectivo'::text,NULL::text,NULL::text,NULL::text,
 'retiro_fondos:'||a.id_asamblea,'retiro_fondos',min(ac.fecha_programada),min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada'),1::bigint,NULL::numeric,NULL::numeric
FROM asamblea a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo
JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN asamblea_convocatoria ac ON ac.id_asamblea=a.id_asamblea
LEFT JOIN catalogo_operativo r ON r.id_catalogo_opcion=ac.id_resultado LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
WHERE a.activo AND pn.activo AND ac.activo AND (ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos')
GROUP BY pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,a.id_asamblea
HAVING min(ac.fecha_programada) IS NOT NULL OR min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada') IS NOT NULL
UNION ALL
SELECT pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,coalesce(cv.ambito,'colectivo')::text,
 CASE WHEN tr.id_asamblea IS NOT NULL THEN acop.codigo ELSE vco.tipo_cop_operativo_codigo END,cv.tipo_convenio::text,NULL::text,
 'ran_ingreso:'||tr.id_tramite_ran,CASE WHEN ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos' THEN 'ingreso_ran_retiro_fondos' WHEN tr.id_asamblea IS NOT NULL THEN 'ingreso_ran_acta' ELSE 'ingreso_ran_convenio' END,
 tr.fecha_programada_ingreso,min(ev.fecha_evento) FILTER(WHERE te.codigo IN ('ingreso','reingreso')),1::bigint,NULL::numeric,NULL::numeric
FROM tramite_ran tr JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
LEFT JOIN asamblea a ON a.id_asamblea=tr.id_asamblea LEFT JOIN catalogo_operativo acop ON acop.id_catalogo_opcion=a.id_tipo_cop_operativo LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
LEFT JOIN convenio cv ON cv.id_convenio=tr.id_convenio LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio=tr.id_convenio LEFT JOIN tramite_ran_evento ev ON ev.id_tramite_ran=tr.id_tramite_ran AND ev.activo LEFT JOIN catalogo_operativo te ON te.id_catalogo_opcion=ev.id_tipo_evento
WHERE tr.activo AND pn.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
GROUP BY pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,tr.id_tramite_ran,tr.id_asamblea,acop.codigo,ta.codigo,ca.codigo,cv.ambito,vco.tipo_cop_operativo_codigo,cv.tipo_convenio,tr.fecha_programada_ingreso
HAVING tr.fecha_programada_ingreso IS NOT NULL OR min(ev.fecha_evento) FILTER(WHERE te.codigo IN ('ingreso','reingreso')) IS NOT NULL
UNION ALL
SELECT pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,coalesce(cv.ambito,'colectivo')::text,
 CASE WHEN tr.id_asamblea IS NOT NULL THEN acop.codigo ELSE vco.tipo_cop_operativo_codigo END,cv.tipo_convenio::text,NULL::text,
 'ran_inscripcion:'||tr.id_tramite_ran,CASE WHEN ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos' THEN 'inscripcion_ran_retiro_fondos' WHEN tr.id_asamblea IS NOT NULL THEN 'inscripcion_ran_acta' ELSE 'inscripcion_ran_convenio' END,
 NULL::date,min(ev.fecha_evento),1::bigint,NULL::numeric,NULL::numeric
FROM tramite_ran tr JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
LEFT JOIN asamblea a ON a.id_asamblea=tr.id_asamblea LEFT JOIN catalogo_operativo acop ON acop.id_catalogo_opcion=a.id_tipo_cop_operativo LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
LEFT JOIN convenio cv ON cv.id_convenio=tr.id_convenio LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio=tr.id_convenio JOIN tramite_ran_evento ev ON ev.id_tramite_ran=tr.id_tramite_ran AND ev.activo JOIN catalogo_operativo te ON te.id_catalogo_opcion=ev.id_tipo_evento AND te.codigo='inscripcion'
WHERE tr.activo AND pn.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
GROUP BY pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,tr.id_tramite_ran,tr.id_asamblea,acop.codigo,ta.codigo,ca.codigo,cv.ambito,vco.tipo_cop_operativo_codigo,cv.tipo_convenio
UNION ALL
SELECT pn.id_proyecto,e.id_entidad,t.id_proyecto_nucleo,t.ambito::text,NULL::text,NULL::text,NULL::text,'fifonafe:'||t.id_tramite_fifonafe,'fifonafe',NULL::date,
 CASE WHEN t.ambito='colectivo' AND count(DISTINCT co.codigo) FILTER(WHERE co.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe') AND nullif(btrim(fe.numero_oficio),'') IS NOT NULL AND fe.fecha_oficio IS NOT NULL)=4
 THEN max(fe.fecha_oficio) FILTER(WHERE co.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe') AND nullif(btrim(fe.numero_oficio),'') IS NOT NULL) WHEN t.ambito='individual' AND t.estatus='completo' THEN coalesce(max(fe.fecha_oficio),t.acuse_fifonafe_fecha) END,1::bigint,NULL::numeric,NULL::numeric
FROM tramite_fifonafe t JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=t.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN tramite_fifonafe_evento fe ON fe.id_tramite_fifonafe=t.id_tramite_fifonafe AND fe.activo LEFT JOIN catalogo_operativo co ON co.id_catalogo_opcion=fe.id_tipo_evento WHERE t.activo AND pn.activo GROUP BY t.id_tramite_fifonafe,pn.id_proyecto,e.id_entidad,t.id_proyecto_nucleo,t.ambito,t.estatus,t.acuse_fifonafe_fecha
HAVING (t.ambito='colectivo' AND count(DISTINCT co.codigo) FILTER(WHERE co.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe') AND nullif(btrim(fe.numero_oficio),'') IS NOT NULL AND fe.fecha_oficio IS NOT NULL)=4) OR (t.ambito='individual' AND t.estatus='completo' AND coalesce(max(fe.fecha_oficio),t.acuse_fifonafe_fecha) IS NOT NULL);

COMMENT ON VIEW vw_hito_seguimiento_007 IS
    'Contrato 007 normalizado por 016: modificatorios ADICIONAL/2A_ADICIONAL conservan indicador superficie_adicional sin usar consecutivo.';

GRANT SELECT ON vw_hito_seguimiento_007 TO software_pa_app;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM convenio WHERE tipo_convenio = 'superficie_adicional'
    ) THEN
        RAISE EXCEPTION '016 no normalizo todos los convenios superficie_adicional';
    END IF;
    IF (
        SELECT count(*)
        FROM catalogo_operativo
        WHERE tipo_catalogo = 'tipo_cop_operativo'
          AND codigo IN ('ADICIONAL', '2A_ADICIONAL')
          AND activo
    ) <> 2 THEN
        RAISE EXCEPTION '016 altero la vigencia de ADICIONAL/2A_ADICIONAL';
    END IF;
END $$;
