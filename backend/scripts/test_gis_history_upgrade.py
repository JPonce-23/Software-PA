#!/usr/bin/env python3
"""Prueba DDL 025→026 en tmpfs; nunca conecta al servidor persistente."""
import os
from test_gis_lineage_equivalence import run, reset, runner


def main():
    for name,value in {'APP_ENV':'test','DB_NAME':'software_pa_test','TEST_ALLOW_DATABASE':'software_pa_test'}.items():
        if os.getenv(name)!=value: raise RuntimeError('Falta guarda '+name)
    try:
        run(['up','-d','--wait','db'],'history-upgrade-start')
        reset()
        runner()
        print(run(['run','--rm','--no-deps','worker','pytest','-q','tests/test_gis_backfill_026.py'],'history-upgrade-tests'))
        run(['exec','-T','db','sh','-lc','MIGRATIONS_DIR=/opt/software-pa/db/migrations POSTGRES_DB=software_pa_test /opt/software-pa/scripts/run_migrations.sh'],'history-026-install')
        run(['exec','-T','db','sh','-lc','psql -U "$POSTGRES_USER" -d software_pa_test -X -v ON_ERROR_STOP=1 -f /opt/software-pa/db/tests/026_historia_cambios_gis_contract.sql'],'history-026-contract')
        code='''import sys; sys.path.insert(0,"scripts")
import reconcile_gis_migration_lineage as r
c=r.connect()
with c.cursor() as cur:
 cur.execute("SELECT current_database()")
 assert cur.fetchone()[0]=="software_pa_test"
 cur.execute("SELECT set_config('app.current_user_id','1',true)")
 cur.execute("INSERT INTO usuario(id_usuario,nombre,apellido_paterno,correo,contrasena_hash,rol) VALUES(1,'QA','Sintético','bootstrap@example.invalid','unused-fixture','admin')")
 cur.execute("INSERT INTO entidad_federativa(id_entidad,clave_inegi,nombre) VALUES(1,'01','QA')")
 cur.execute("INSERT INTO municipio(id_municipio,id_entidad,clave_inegi,nombre) VALUES(1,1,'01001','QA')")
 for table,pk in [('usuario','id_usuario'),('entidad_federativa','id_entidad'),('municipio','id_municipio')]:
  cur.execute("SELECT setval(pg_get_serial_sequence(%s,%s),1,true)",(table,pk))
c.commit();c.close()
'''
        run(['run','--rm','--no-deps','worker','python','-c',code],'history-026-bootstrap')
        print(run(['run','--rm','--no-deps','worker','pytest','-q','tests/test_gis_history_026.py','tests/test_gis_concurrency_026.py'], 'history-026-functional-tests'))
    finally:
        run(['down','-v','--remove-orphans'],'history-upgrade-cleanup')


if __name__=='__main__': main()
