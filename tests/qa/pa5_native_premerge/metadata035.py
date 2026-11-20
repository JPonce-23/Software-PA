import json,os,subprocess,sys
from pathlib import Path
assert os.environ['PGHOST'].startswith('/tmp/pa5-pr8-db.') and os.environ['PGDATABASE']=='software_pa_test'
query="""SELECT json_build_object(
 'has_035', EXISTS(SELECT 1 FROM public.schema_migrations WHERE version='035'),
 'function', (SELECT json_build_object('oid',oid,'owner',proowner,'acl',proacl::text,'definer',prosecdef,'path',proconfig) FROM pg_proc WHERE oid='public.fn_audit_log()'::regprocedure),
 'definers', (SELECT json_agg(json_build_object('name',p.oid::regprocedure::text,'path',p.proconfig,'owner',p.proowner)) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prosecdef AND NOT EXISTS(SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e')),
 'runtime_temp',has_database_privilege('qa_runtime',current_database(),'TEMP'),
 'runtime_public_create',has_schema_privilege('qa_runtime','public','CREATE'),
 'runtime_admin',(SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls FROM pg_roles WHERE rolname='qa_runtime'),
 'database_acl',(SELECT datacl::text FROM pg_database WHERE datname=current_database()),
 'public_acl',(SELECT nspacl::text FROM pg_namespace WHERE nspname='public'),
 'data',(SELECT json_build_object('projects',(SELECT json_agg(to_jsonb(t) ORDER BY id_proyecto) FROM public.proyecto t),'links',(SELECT json_agg(to_jsonb(t) ORDER BY id_convenio_afectacion) FROM public.convenio_afectacion t),'audit_rows',(SELECT count(*) FROM public.bitacora))))"""
data=json.loads(subprocess.check_output(['psql','-X','-At','-v','ON_ERROR_STOP=1','-c',query],text=True))
assert data['runtime_temp'] and not data['runtime_public_create'] and not data['runtime_admin']
assert len(data['definers'])==1 and data['definers'][0]['name']=='fn_audit_log()'
if data['has_035']:assert data['function']['path']==['search_path=pg_catalog, public, pg_temp']
if len(sys.argv)>2:
 before=json.loads(Path(sys.argv[2]).read_text())
 for key in ['oid','owner','acl','definer']:assert before['function'][key]==data['function'][key],key
 for key in ['runtime_temp','runtime_public_create','runtime_admin','database_acl','public_acl','data']:assert before[key]==data[key],key
 assert data['function']['path']==['search_path=pg_catalog, public, pg_temp'],data['function']
 print('AUDIT_035_OID_OWNER_ACL_TEMP_DATA_PRESERVED_OK')
Path(sys.argv[1]).write_text(json.dumps(data,indent=2)+'\n')
print('AUDIT_035_METADATA_OK')
