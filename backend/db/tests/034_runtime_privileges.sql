\set ON_ERROR_STOP on

BEGIN;

SELECT set_config('app.expected_runtime_user', :'expected_runtime_user', true);
SELECT set_config('app.expected_owner_user', :'expected_owner_user', true);
SELECT set_config('app.runtime_probe_table', :'probe_table', true);

DO $identity$
DECLARE
    v_runtime name := current_setting('app.expected_runtime_user')::name;
    v_owner name := current_setting('app.expected_owner_user')::name;
    v_role pg_roles%ROWTYPE;
    v_group pg_roles%ROWTYPE;
    v_schema_owner name;
    v_relation_count integer;
    v_wrong_owner_count integer;
BEGIN
    IF current_user <> v_runtime THEN
        RAISE EXCEPTION 'Conexión runtime incorrecta: actual %, esperado %', current_user, v_runtime;
    END IF;

    SELECT * INTO STRICT v_role FROM pg_roles WHERE rolname = v_runtime;
    IF NOT v_role.rolcanlogin OR v_role.rolsuper OR v_role.rolcreatedb
       OR v_role.rolcreaterole OR v_role.rolreplication OR v_role.rolbypassrls THEN
        RAISE EXCEPTION 'Atributos inseguros para %', v_runtime;
    END IF;

    SELECT * INTO STRICT v_group FROM pg_roles WHERE rolname = 'software_pa_app';
    IF v_group.rolcanlogin OR v_group.rolsuper OR v_group.rolcreatedb
       OR v_group.rolcreaterole OR v_group.rolreplication OR v_group.rolbypassrls THEN
        RAISE EXCEPTION 'Atributos inseguros para software_pa_app';
    END IF;

    IF NOT pg_has_role(v_runtime, 'software_pa_app', 'MEMBER') THEN
        RAISE EXCEPTION '% no hereda software_pa_app', v_runtime;
    END IF;
    IF pg_has_role(v_runtime, v_owner, 'MEMBER') THEN
        RAISE EXCEPTION '% hereda privilegios del owner %', v_runtime, v_owner;
    END IF;

    SELECT pg_get_userbyid(nspowner) INTO v_schema_owner
    FROM pg_namespace WHERE nspname = 'public';
    IF v_schema_owner = v_runtime THEN
        RAISE EXCEPTION '% es owner del schema public', v_runtime;
    END IF;

    SELECT count(*), count(*) FILTER (WHERE pg_get_userbyid(relowner) <> v_owner)
    INTO v_relation_count, v_wrong_owner_count
    FROM pg_class
    WHERE relnamespace = 'public'::regnamespace
      AND relname IN (
          'proyecto', 'proyecto_nucleo', 'afectacion', 'convenio',
          'tramite_fifonafe', 'indemnizacion', 'pago'
      );
    IF v_relation_count <> 7 OR v_wrong_owner_count <> 0 THEN
        RAISE EXCEPTION 'Ownership funcional inesperado: owner %, objetos %, incorrectos %',
            v_owner, v_relation_count, v_wrong_owner_count;
    END IF;

    IF has_schema_privilege(v_runtime, 'public', 'CREATE') THEN
        RAISE EXCEPTION '% conserva CREATE en public', v_runtime;
    END IF;
    IF has_table_privilege(v_runtime, 'public.schema_migrations', 'INSERT,UPDATE')
       OR has_table_privilege(v_runtime, 'public.spatial_ref_sys', 'INSERT,UPDATE') THEN
        RAISE EXCEPTION '% puede modificar catálogos administrativos', v_runtime;
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) acl
        WHERE p.pronamespace = 'public'::regnamespace
          AND p.prosecdef
          AND acl.grantee = 0
          AND acl.privilege_type = 'EXECUTE'
          AND NOT EXISTS (
              SELECT 1 FROM pg_depend dependency
              WHERE dependency.classid = 'pg_proc'::regclass
                AND dependency.objid = p.oid
                AND dependency.deptype = 'e'
          )
    ) THEN
        RAISE EXCEPTION 'PUBLIC ejecuta una función propia SECURITY DEFINER';
    END IF;
END
$identity$;

-- SELECT, INSERT y UPDATE reales sobre una tabla funcional; el ROLLBACK final
-- impide conservar la fila de prueba.
SELECT id_usuario AS actor_id
FROM usuario
WHERE activo
ORDER BY id_usuario
LIMIT 1
\gset

SELECT set_config('app.current_user_id', :'actor_id', true);

INSERT INTO proyecto (clave_proyecto, nombre_proyecto)
VALUES ('RUNTIME-SQL-' || txid_current()::text, 'Prueba runtime SQL')
RETURNING id_proyecto
\gset

UPDATE proyecto
SET nombre_proyecto = 'Prueba runtime SQL actualizada'
WHERE id_proyecto = :id_proyecto;

\echo 'SELECT runtime: permitido'
\echo 'INSERT runtime: permitido'
\echo 'UPDATE runtime: permitido'

DO $positive$
DECLARE
    v_probe name := current_setting('app.runtime_probe_table')::name;
    v_count integer;
BEGIN
    IF NOT has_table_privilege(current_user, 'public.proyecto', 'SELECT,INSERT,UPDATE') THEN
        RAISE EXCEPTION 'Falta SELECT/INSERT/UPDATE sobre proyecto';
    END IF;
    IF has_table_privilege(current_user, 'public.proyecto', 'DELETE,TRUNCATE') THEN
        RAISE EXCEPTION 'Existe DELETE/TRUNCATE sobre proyecto';
    END IF;
    IF NOT has_table_privilege(current_user, format('public.%I', v_probe), 'SELECT,INSERT,UPDATE') THEN
        RAISE EXCEPTION 'Default privileges incompletos sobre %', v_probe;
    END IF;
    IF has_table_privilege(current_user, format('public.%I', v_probe), 'DELETE,TRUNCATE') THEN
        RAISE EXCEPTION 'Default privileges destructivos sobre %', v_probe;
    END IF;

    EXECUTE format('INSERT INTO public.%I (valor) VALUES ($1)', v_probe)
    USING 'runtime insert';
    EXECUTE format('UPDATE public.%I SET valor = $1 WHERE valor = $2', v_probe)
    USING 'runtime update', 'runtime insert';
    EXECUTE format('SELECT count(*) FROM public.%I WHERE valor = $1', v_probe)
    INTO v_count USING 'runtime update';
    IF v_count <> 1 THEN
        RAISE EXCEPTION 'INSERT/UPDATE default no verificables sobre %', v_probe;
    END IF;
END
$positive$;

DO $delete_denied$
BEGIN
    DELETE FROM proyecto WHERE false;
    RAISE EXCEPTION 'DELETE permitido inesperadamente';
EXCEPTION WHEN insufficient_privilege THEN
    NULL;
END
$delete_denied$;
\echo 'DELETE runtime: permission denied (42501)'

DO $truncate_denied$
BEGIN
    EXECUTE 'TRUNCATE TABLE proyecto';
    RAISE EXCEPTION 'TRUNCATE permitido inesperadamente';
EXCEPTION WHEN insufficient_privilege THEN
    NULL;
END
$truncate_denied$;
\echo 'TRUNCATE runtime: permission denied (42501)'

DO $create_denied$
BEGIN
    EXECUTE 'CREATE TABLE public.runtime_forbidden_sql_034 (id integer)';
    RAISE EXCEPTION 'CREATE TABLE permitido inesperadamente';
EXCEPTION WHEN insufficient_privilege THEN
    NULL;
END
$create_denied$;
\echo 'CREATE TABLE public runtime: permission denied (42501)'

DO $alter_denied$
BEGIN
    EXECUTE 'ALTER TABLE proyecto ADD COLUMN runtime_forbidden_sql_034 text';
    RAISE EXCEPTION 'ALTER TABLE permitido inesperadamente';
EXCEPTION WHEN insufficient_privilege THEN
    NULL;
END
$alter_denied$;
\echo 'ALTER TABLE runtime: permission denied (42501)'

DO $drop_denied$
DECLARE
    v_probe name := current_setting('app.runtime_probe_table')::name;
BEGIN
    EXECUTE format('DROP TABLE public.%I', v_probe);
    RAISE EXCEPTION 'DROP TABLE permitido inesperadamente';
EXCEPTION WHEN insufficient_privilege THEN
    NULL;
END
$drop_denied$;
\echo 'DROP TABLE runtime: permission denied (42501)'

ROLLBACK;

\echo 'CONTRATO SQL RUNTIME 034: OK'
