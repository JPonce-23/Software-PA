"""Read-only PostGIS runtime permission preflight; does not invoke decoders or apply SQL migrations."""
import os

QUERY = """
SELECT n.nspname, p.proname,
       has_function_privilege(current_user, p.oid, 'EXECUTE'),
       pg_has_role(current_user, p.proowner, 'MEMBER')
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
JOIN pg_depend d ON d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e'
JOIN pg_extension e ON e.oid = d.refobjid AND e.extname = 'postgis'
WHERE p.proname IN ('st_fromflatgeobuf', 'st_fromflatgeobuftotable')
"""


def verify(cursor):
    cursor.execute("SELECT rolsuper, rolcreaterole FROM pg_roles WHERE rolname = current_user")
    role = cursor.fetchone()
    if role is None or any(role):
        raise ValueError("ROL_RUNTIME_PRIVILEGIADO")
    cursor.execute(QUERY)
    rows = cursor.fetchall()
    expected = {('public', 'st_fromflatgeobuf'), ('public', 'st_fromflatgeobuftotable')}
    if len(rows) != 2 or {(r[0], r[1]) for r in rows} != expected:
        raise ValueError("INVENTARIO_POSTGIS_REQUIERE_REVISION")
    if any(r[2] or r[3] for r in rows):
        raise ValueError("DECODIFICADORES_ACCESIBLES_REVISAR_MIGRACION_033")
    return len(rows)


def main():
    import psycopg2
    try:
        # Explicit runtime credentials only; never use owner/admin fallbacks.
        config = {key: os.environ[name] for key, name in {
            'host': 'DB_HOST', 'port': 'DB_PORT', 'dbname': 'DB_NAME',
            'user': 'DB_RUNTIME_USER', 'password': 'DB_RUNTIME_PASSWORD',
        }.items()}
        connection = psycopg2.connect(**config, connect_timeout=5,
                                    options='-c statement_timeout=5000')
        try:
            connection.set_session(readonly=True, autocommit=False)
            with connection.cursor() as cursor:
                count = verify(cursor)
            connection.rollback()
        finally:
            connection.close()
    except ValueError as error:
        print('POSTGIS_PREFLIGHT_FAIL', str(error))
        return 1
    except Exception:
        print('POSTGIS_PREFLIGHT_FAIL', 'CONEXION_O_CONFIGURACION_NO_VERIFICADA')
        return 1
    print('POSTGIS_PREFLIGHT_OK', count)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
