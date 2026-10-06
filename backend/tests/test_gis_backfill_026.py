"""Aplica 026 transaccionalmente sobre fixtures 025 sólo en PostGIS desechable."""
import os
from pathlib import Path

import psycopg2
import pytest
from psycopg2.extras import RealDictCursor


@pytest.fixture
def schema_025():
    if os.getenv('LINEAGE_DISPOSABLE_INSTANCE') != '1':
        pytest.skip('Backfill DDL requiere instancia desechable aislada')
    connection = psycopg2.connect(host=os.environ['DB_HOST'],port=os.environ['DB_PORT'],
        dbname='software_pa_test',user=os.environ['POSTGRES_ADMIN_USER'],password=os.environ['POSTGRES_ADMIN_PASSWORD'])
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),current_setting(\'cluster_name\')')
        assert cursor.fetchone() == ('software_pa_test','software-pa-lineage-equivalence')
        cursor.execute("SELECT max(version::int) FROM schema_migrations")
        assert cursor.fetchone()[0] == 25
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize('finalized', [False,True])
def test_backfill_preserves_ids_dates_users_decisions_and_geometry(schema_025,finalized):
    c=schema_025
    with c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT set_config('app.current_user_id','990001',true)")
        cur.execute("""INSERT INTO usuario(id_usuario,nombre,apellido_paterno,correo,contrasena_hash,rol)
            VALUES(990001,'QA','Sintético','upgrade@example.invalid','fixture-unused','admin');
            INSERT INTO entidad_federativa(id_entidad,clave_inegi,nombre) VALUES(990001,'99','QA');
            INSERT INTO municipio(id_municipio,id_entidad,clave_inegi,nombre) VALUES(990001,990001,'99001','QA');
            INSERT INTO proyecto(id_proyecto,clave_proyecto,nombre_proyecto,creado_por)
            VALUES(990001,'UPGRADE-026','QA',990001);
            INSERT INTO nucleo_agrario(id_nucleo,id_municipio,nombre_nucleo,id_tipo_tenencia,creado_por)
            SELECT 990001,990001,'QA',id_catalogo_opcion,990001 FROM catalogo_operativo
            WHERE tipo_catalogo='tipo_tenencia' AND codigo='ejido';
            INSERT INTO proyecto_nucleo(id_proyecto_nucleo,id_proyecto,id_nucleo,creado_por) VALUES(990001,990001,990001,990001);
            INSERT INTO importacion_archivo(id_importacion,id_proyecto,tipo_objetivo,nombre_original,nombre_almacenado,
              formato_detectado,tamano_bytes,sha256,fuente,version_pipeline,estado,id_usuario_carga,creado_por)
            VALUES(990001,990001,'nucleo_agrario_gpkg','qa.gpkg','qa.gpkg','gpkg',1,repeat('a',64),'QA','conciliacion-v2','previsualizado',990001,990001);
            INSERT INTO importacion_feature(id_importacion_feature,id_importacion,indice_feature,estado,estado_conciliacion,
              geometria_normalizada,geometria_trabajo) VALUES(990001,990001,0,'valido','candidato',
              ST_Multi(ST_GeomFromText('POLYGON((0 0,0 1,1 1,1 0,0 0))',4326)),
              ST_Multi(ST_GeomFromText('POLYGON((0 0,0 1,1 1,1 0,0 0))',4326)));
            INSERT INTO importacion_feature_candidato(id_candidato,id_importacion,id_importacion_feature,id_proyecto_nucleo,
              criterio,clasificacion,estado,creado_por) VALUES(990001,990001,990001,990001,'QA','exacta','confirmado',990001);
            UPDATE importacion_feature SET estado='confirmado',estado_conciliacion='confirmado',registro_destino_id=990001 WHERE id_importacion_feature=990001;
            INSERT INTO importacion_feature_decision(id_decision,id_importacion_feature,id_candidato,accion,motivo,creado_por)
            VALUES(990001,990001,990001,'confirmar','Decisión anterior',990001);
            INSERT INTO proyecto_nucleo_geometria(id_geometria,id_proyecto_nucleo,id_importacion_feature,version,
              geometria_poligono,geometria_trabajo,srid_trabajo,fuente,creado_por)
            SELECT 990001,990001,990001,1,geometria_normalizada,geometria_trabajo,4326,'QA',990001 FROM importacion_feature WHERE id_importacion_feature=990001;
        """)
        if finalized:
            cur.execute("UPDATE importacion_archivo SET estado='completo' WHERE id_importacion=990001")
        before={}
        tables=('importacion_archivo','importacion_feature','importacion_feature_candidato',
                'importacion_feature_decision','proyecto_nucleo_geometria')
        for table in tables:
            cur.execute(f'SELECT to_jsonb(t) data FROM {table} t')
            before[table]=[x['data'] for x in cur.fetchall()]
        cur.execute((Path(__file__).parents[1]/'db/migrations/026_historia_cambios_gis.sql').read_text())
        cur.execute('SELECT * FROM importacion_conciliacion_ciclo')
        cycle=cur.fetchone()
        assert cycle['numero_ciclo']==1 and cycle['tipo_ciclo']=='historico'
        assert cycle['estado']==('finalizado' if finalized else 'abierto')
        assert cycle['resumen']['universo_historico_no_reconstruible'] is True
        for table in tables:
            cur.execute(f'SELECT to_jsonb(t) data FROM {table} t')
            after=[x['data'] for x in cur.fetchall()]
            for row in after:
                if table in ('importacion_feature_candidato','importacion_feature_decision'):
                    assert row.pop('id_ciclo')==cycle['id_ciclo']
                if table=='importacion_archivo':
                    assert row.pop('alcance_entrega')=='parcial'
                    assert row.pop('id_importacion_anterior') is None
            assert after==before[table]
        cur.execute("SELECT count(*) n FROM pg_trigger WHERE NOT tgisinternal AND tgenabled='D'")
        assert cur.fetchone()['n']==0
        cur.execute('SAVEPOINT immutable')
        with pytest.raises(psycopg2.Error,match='append-only'):
            cur.execute("UPDATE importacion_feature_decision SET motivo='alterado' WHERE id_decision=990001")
        cur.execute('ROLLBACK TO SAVEPOINT immutable')
