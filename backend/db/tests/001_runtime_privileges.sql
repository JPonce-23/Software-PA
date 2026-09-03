\set ON_ERROR_STOP on

BEGIN;

SELECT set_config('app.expected_runtime_user', :'expected_runtime_user', true);
SELECT set_config('app.expected_owner_user', :'expected_owner_user', true);

DO $contract$
DECLARE
    v_runtime name := current_setting('app.expected_runtime_user')::name;
    v_owner name := current_setting('app.expected_owner_user')::name;
    v_role pg_roles%ROWTYPE;
BEGIN
    IF current_user <> v_runtime THEN
        RAISE EXCEPTION 'Conexión runtime incorrecta: actual %, esperada %', current_user, v_runtime;
    END IF;
    SELECT * INTO STRICT v_role FROM pg_roles WHERE rolname=v_runtime;
    IF NOT v_role.rolcanlogin OR v_role.rolsuper OR v_role.rolcreatedb
       OR v_role.rolcreaterole OR v_role.rolreplication OR v_role.rolbypassrls THEN
        RAISE EXCEPTION 'Atributos inseguros para el runtime %', v_runtime;
    END IF;
    IF NOT pg_has_role(v_runtime,'software_pa_app','MEMBER')
       OR pg_has_role(v_runtime,v_owner,'MEMBER') THEN
        RAISE EXCEPTION 'Membresías runtime incorrectas';
    END IF;
    IF has_schema_privilege(v_runtime,'public','CREATE') THEN
        RAISE EXCEPTION 'El runtime conserva CREATE en public';
    END IF;
    IF NOT has_table_privilege(v_runtime,'public.proyecto','SELECT,INSERT,UPDATE')
       OR has_table_privilege(v_runtime,'public.proyecto','DELETE,TRUNCATE') THEN
        RAISE EXCEPTION 'DML runtime incorrecto sobre proyecto';
    END IF;
    IF NOT has_table_privilege(v_runtime,'public.schema_migrations','SELECT')
       OR has_table_privilege(v_runtime,'public.schema_migrations','INSERT,UPDATE,DELETE,TRUNCATE') THEN
        RAISE EXCEPTION 'schema_migrations no es read-only para runtime';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S')
          AND c.relname NOT LIKE 'pg_%'
          AND pg_get_userbyid(c.relowner) <> v_owner
    ) THEN
        RAISE EXCEPTION 'Hay objetos SOFTWARE-PA cuyo owner no es %', v_owner;
    END IF;
END
$contract$;

SELECT id_usuario AS actor_id FROM usuario WHERE activo ORDER BY id_usuario LIMIT 1 \gset
SELECT set_config('app.current_user_id', :'actor_id', true);

INSERT INTO proyecto(clave_proyecto,nombre_proyecto)
VALUES('ACL-' || txid_current()::text,'Contrato ACL baseline')
RETURNING id_proyecto \gset
UPDATE proyecto SET nombre_proyecto='Contrato ACL baseline actualizado'
 WHERE id_proyecto=:id_proyecto;

DO $denied$
BEGIN
    BEGIN
        DELETE FROM proyecto WHERE false;
        RAISE EXCEPTION 'DELETE permitido inesperadamente';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    BEGIN
        EXECUTE 'CREATE TABLE public.runtime_forbidden_baseline(id integer)';
        RAISE EXCEPTION 'CREATE permitido inesperadamente';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
    BEGIN
        UPDATE schema_migrations SET nombre=nombre WHERE false;
        RAISE EXCEPTION 'UPDATE del ledger permitido inesperadamente';
    EXCEPTION WHEN insufficient_privilege THEN NULL;
    END;
END
$denied$;

ROLLBACK;
SELECT 'CONTRATO ACL/RUNTIME BASELINE V1 APROBADO' AS resultado;
