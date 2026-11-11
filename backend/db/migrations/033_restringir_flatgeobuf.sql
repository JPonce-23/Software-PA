-- CVE-2026-73515: deny the unused FlatGeobuf decoders before C code executes.
-- PostGIS 3.6.4 has no backport; 3.7 removes tiger_geocoder (replacement needs PG16).
-- This is a privilege mitigation, not a binary patch. Owners/superusers remain trusted.
-- Reapply this file after every ALTER EXTENSION postgis UPDATE: extension scripts
-- can recreate functions and default privileges grant execution to software_pa_app.
DO $policy$
DECLARE
    decoder record;
    member_role record;
    decoder_count integer := 0;
BEGIN
    FOR decoder IN
        SELECT p.oid, p.oid::regprocedure AS signature, p.proowner
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_depend d ON d.classid = 'pg_proc'::regclass AND d.objid = p.oid
            AND d.deptype = 'e'
        JOIN pg_extension e ON e.oid = d.refobjid AND e.extname = 'postgis'
        WHERE n.nspname = 'public'
          AND p.proname IN ('st_fromflatgeobuf', 'st_fromflatgeobuftotable')
    LOOP
        decoder_count := decoder_count + 1;
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, software_pa_app', decoder.signature);
        FOR member_role IN
            SELECT oid, rolname FROM pg_roles
            WHERE NOT rolsuper AND pg_has_role(oid, 'software_pa_app', 'MEMBER')
        LOOP
            IF member_role.oid = decoder.proowner THEN
                RAISE EXCEPTION 'Application role must not own a FlatGeobuf decoder';
            END IF;
            EXECUTE format('REVOKE ALL ON FUNCTION %s FROM %I', decoder.signature, member_role.rolname);
        END LOOP;
        IF EXISTS (
            SELECT 1 FROM pg_roles r
            WHERE NOT r.rolsuper AND r.oid <> decoder.proowner
              AND has_function_privilege(r.oid, decoder.oid, 'EXECUTE')
        ) THEN
            RAISE EXCEPTION 'Unexpected non-owner FlatGeobuf execution grant';
        END IF;
    END LOOP;
    IF decoder_count <> 2 THEN
        RAISE EXCEPTION 'Unexpected PostGIS FlatGeobuf decoder inventory: %', decoder_count;
    END IF;
END
$policy$;
