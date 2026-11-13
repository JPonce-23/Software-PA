SET search_path = public, pg_catalog;
SELECT pg_advisory_xact_lock(hashtextextended('software-pa:034:seguimiento-fifonafe', 0));
CREATE TABLE etiqueta_seguimiento_fifonafe (
    id_etiqueta bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_convenio integer NOT NULL REFERENCES convenio(id_convenio),
    codigo varchar(40) NOT NULL CHECK (codigo IN ('espera_firma','bienes_distintos_tierra','observaciones_importantes')),
    habilitada boolean NOT NULL,
    motivo text NOT NULL CHECK (length(btrim(motivo)) BETWEEN 5 AND 2000),
    creado_por integer NOT NULL REFERENCES usuario(id_usuario),
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_etiqueta_fifonafe_convenio ON etiqueta_seguimiento_fifonafe(id_convenio, codigo, id_etiqueta DESC);
CREATE FUNCTION fn_etiqueta_fifonafe_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'El historial de etiquetas no se modifica; registre una nueva decisión'; END $$;
CREATE TRIGGER trg_etiqueta_fifonafe_inmutable BEFORE UPDATE OR DELETE ON etiqueta_seguimiento_fifonafe
FOR EACH ROW EXECUTE FUNCTION fn_etiqueta_fifonafe_inmutable();
CREATE TRIGGER trg_audit_etiqueta_fifonafe AFTER INSERT ON etiqueta_seguimiento_fifonafe
FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_etiqueta');
GRANT SELECT, INSERT ON etiqueta_seguimiento_fifonafe TO software_pa_app;
GRANT USAGE, SELECT ON SEQUENCE etiqueta_seguimiento_fifonafe_id_etiqueta_seq TO software_pa_app;
