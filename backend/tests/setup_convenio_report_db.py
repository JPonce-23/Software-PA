"""Install existing schema and synthetic catalog in the disposable report DB only.

Run through convenio_report_compose.yml. Never accepts a host/production target;
refuses an existing schema instead of clearing it. No new migration is defined.
"""

import hashlib
import os
from pathlib import Path

import psycopg2


def main():
    required = {"APP_ENV": "test", "DB_HOST": "db", "DB_NAME": "software_pa_test",
                "TEST_ALLOW_DATABASE": "software_pa_test", "POSTGRES_ADMIN_USER": "report_owner"}
    if any(os.environ.get(key) != value for key, value in required.items()):
        raise RuntimeError("Use exclusivamente el Compose desechable de convenios")
    with psycopg2.connect(host="db", dbname="software_pa_test", user="report_owner",
                          password=os.environ["POSTGRES_ADMIN_PASSWORD"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_setting('cluster_name'), to_regclass('public.schema_migrations')")
            name, cluster, ledger = cur.fetchone()
            if (name, cluster, ledger) != ("software_pa_test", "convenio-report-disposable", None):
                raise RuntimeError("Instancia no desechable o esquema ya instalado: no se modifica")
        root = Path(__file__).resolve().parents[1] / "db/migrations"
        # Only canonical versions: an ignored legacy 001_init_schema.sql can
        # exist in a developer checkout and must never enter this test lineage.
        paths = [root / "001_baseline_v1.sql", *sorted(p for p in root.glob("[0-9][0-9][0-9]_*.sql")
                                                       if "002" <= p.name[:3] <= "030")]
        for path in paths:
            content = path.read_bytes()
            with conn.cursor() as cur:
                cur.execute(content.decode())
                cur.execute("SET search_path = public, pg_catalog")
                cur.execute("INSERT INTO schema_migrations(version,nombre,checksum_sha256) VALUES (%s,%s,%s)",
                            (path.name[:3], path.stem[4:], hashlib.sha256(content).hexdigest()))
            conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_id','1',true)")
            cur.execute("INSERT INTO usuario(id_usuario,nombre,apellido_paterno,correo,contrasena_hash,rol) "
                        "VALUES(1,'QA','Sintético','bootstrap@local.invalid','unused-fixture','admin')")
            cur.execute("INSERT INTO entidad_federativa(id_entidad,clave_inegi,nombre) VALUES "
                        "(1,'01','Entidad sintética A'),(2,'02','Entidad sintética B')")
            cur.execute("INSERT INTO municipio(id_municipio,id_entidad,clave_inegi,nombre) VALUES "
                        "(1,1,'01001','Municipio sintético A'),(2,2,'02001','Municipio sintético B')")
            for table, column in (("usuario", "id_usuario"), ("entidad_federativa", "id_entidad"), ("municipio", "id_municipio")):
                cur.execute(f"SELECT setval(pg_get_serial_sequence(%s,%s),(SELECT max({column}) FROM {table}),true)", (table, column))
        conn.commit()
    print("Instancia local desechable software_pa_test: esquema 001–030 y catálogo sintético instalados")


if __name__ == "__main__":
    main()
