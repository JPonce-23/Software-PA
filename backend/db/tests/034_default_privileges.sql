\set ON_ERROR_STOP on

SELECT set_config('app.expected_runtime_user', :'runtime_user', false);
SELECT set_config('app.runtime_probe_table', :'probe_table', false);

DO $contract$
DECLARE
    v_runtime name := current_setting('app.expected_runtime_user')::name;
    v_probe name := current_setting('app.runtime_probe_table')::name;
    v_owner name;
    v_sequence text;
BEGIN
    SELECT pg_get_userbyid(relowner) INTO v_owner
    FROM pg_class
    WHERE oid = format('public.%I', v_probe)::regclass;
    IF v_owner <> current_user OR v_owner = v_runtime THEN
        RAISE EXCEPTION 'Owner futuro incorrecto: %, migrador %, runtime %',
            v_owner, current_user, v_runtime;
    END IF;

    IF NOT has_table_privilege(v_runtime, format('public.%I', v_probe), 'SELECT,INSERT,UPDATE')
       OR has_table_privilege(v_runtime, format('public.%I', v_probe), 'DELETE,TRUNCATE') THEN
        RAISE EXCEPTION 'Default privileges de tabla incorrectos para %', v_runtime;
    END IF;

    SELECT pg_get_serial_sequence(format('public.%I', v_probe), 'id') INTO v_sequence;
    IF v_sequence IS NULL
       OR NOT has_sequence_privilege(v_runtime, v_sequence, 'USAGE,SELECT') THEN
        RAISE EXCEPTION 'Default privileges de secuencia incorrectos para %', v_runtime;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_default_acl d
        CROSS JOIN LATERAL aclexplode(d.defaclacl) acl
        JOIN pg_roles grantor_role ON grantor_role.oid = d.defaclrole
        JOIN pg_roles grantee_role ON grantee_role.oid = acl.grantee
        WHERE grantor_role.rolname = current_user
          AND grantee_role.rolname = 'software_pa_app'
          AND d.defaclnamespace = 'public'::regnamespace
          AND d.defaclobjtype = 'r'
          AND acl.privilege_type IN ('SELECT', 'INSERT', 'UPDATE')
        GROUP BY d.defaclrole, d.defaclnamespace, d.defaclobjtype
        HAVING count(DISTINCT acl.privilege_type) = 3
    ) THEN
        RAISE EXCEPTION 'No existe el default ACL esperado para tablas futuras';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_default_acl d
        CROSS JOIN LATERAL aclexplode(d.defaclacl) acl
        JOIN pg_roles grantor_role ON grantor_role.oid = d.defaclrole
        JOIN pg_roles grantee_role ON grantee_role.oid = acl.grantee
        WHERE grantor_role.rolname = current_user
          AND grantee_role.rolname = 'software_pa_app'
          AND d.defaclnamespace = 'public'::regnamespace
          AND d.defaclobjtype = 'S'
          AND acl.privilege_type IN ('USAGE', 'SELECT')
        GROUP BY d.defaclrole, d.defaclnamespace, d.defaclobjtype
        HAVING count(DISTINCT acl.privilege_type) = 2
    ) THEN
        RAISE EXCEPTION 'No existe el default ACL esperado para secuencias futuras';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_default_acl d
        CROSS JOIN LATERAL aclexplode(d.defaclacl) acl
        JOIN pg_roles grantor_role ON grantor_role.oid = d.defaclrole
        LEFT JOIN pg_roles grantee_role ON grantee_role.oid = acl.grantee
        WHERE grantor_role.rolname = current_user
          AND d.defaclnamespace = 'public'::regnamespace
          AND d.defaclobjtype IN ('r', 'S')
          AND (
              (grantee_role.rolname = 'software_pa_app'
               AND acl.privilege_type IN ('DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'))
              OR acl.grantee = 0
          )
    ) THEN
        RAISE EXCEPTION 'Default ACL destructivo o PUBLIC detectado';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_default_acl d
        CROSS JOIN LATERAL aclexplode(d.defaclacl) acl
        JOIN pg_roles grantor_role ON grantor_role.oid = d.defaclrole
        WHERE grantor_role.rolname = current_user
          AND d.defaclnamespace = 'public'::regnamespace
          AND d.defaclobjtype = 'f'
          AND acl.grantee = 0
          AND acl.privilege_type = 'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'PUBLIC conserva EXECUTE por defecto en funciones futuras';
    END IF;
END
$contract$;

\echo 'DEFAULT PRIVILEGES 034: OK'
