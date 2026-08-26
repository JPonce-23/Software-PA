-- Migración 034: contrato de privilegios para el rol NOLOGIN de aplicación.
-- El LOGIN runtime y su contraseña pertenecen al entorno y se provisionan
-- fuera de esta migración con backend/scripts/utils/set_runtime_credentials.sh.
BEGIN;

SELECT pg_advisory_xact_lock(20260825, 34);

DO $preflight$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '033') THEN
        RAISE EXCEPTION '034 requiere la migración 033';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '034') THEN
        RAISE EXCEPTION 'La migración 034 ya fue aplicada';
    END IF;
END;
$preflight$;

-- Rol estable de privilegios. Nunca es el LOGIN utilizado por FastAPI.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'software_pa_app') THEN
        CREATE ROLE software_pa_app;
    END IF;
END
$$;

ALTER ROLE software_pa_app
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- PUBLIC y el rol de aplicación no pueden crear objetos en el schema funcional.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM software_pa_app;
GRANT USAGE ON SCHEMA public TO software_pa_app;

-- El contrato runtime es DML no destructivo sobre objetos existentes.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO software_pa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO software_pa_app;
REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM software_pa_app;
-- Catálogo de migraciones y catálogo PostGIS son de lectura para FastAPI.
REVOKE INSERT, UPDATE ON TABLE schema_migrations, spatial_ref_sys FROM software_pa_app;

-- Una función propia SECURITY DEFINER nunca queda ejecutable por PUBLIC.
-- Las funciones de extensiones (por ejemplo PostGIS) conservan su ACL de la
-- extensión y se auditan por separado.
DO $revoke_security_definer$
DECLARE
    v_function regprocedure;
BEGIN
    FOR v_function IN
        SELECT p.oid::regprocedure
        FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace
          AND p.prosecdef
          AND NOT EXISTS (
              SELECT 1
              FROM pg_depend dependency
              WHERE dependency.classid = 'pg_proc'::regclass
                AND dependency.objid = p.oid
                AND dependency.deptype = 'e'
          )
    LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC', v_function);
    END LOOP;
END
$revoke_security_definer$;

-- Sin FOR ROLE: PostgreSQL aplica estos defaults al current_user que ejecuta
-- migraciones y, por tanto, al owner real de los objetos futuros.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO software_pa_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO software_pa_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES FROM software_pa_app;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('034', 'Aislamiento real del usuario runtime de PostgreSQL');

COMMIT;
