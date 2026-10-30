"""SS-07 offline checks: never import app/engine, run psql, or connect."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'docs/security/ss07'
spec=importlib.util.spec_from_file_location('ss07_offline',ASSETS/'preparar_verificador.py')
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def config():
    return dict(autorizacion='QA-SINTETICA-0007',clon_verificado=True,database='ss07_synthetic',
        server_addr='127.0.0.1',server_port=55432,cluster_marker='ss07_synthetic_disposable',
        inspector='ss07_inspector',runtime='ss07_runtime',migrator='ss07_migrator')


class PrivilegeAuditTests(unittest.TestCase):
    def setUp(self):
        self.template=(ASSETS/'consultas-privilegios.sql.in').read_text()

    def test_metadata_template_lexically_complete(self):
        self.assertEqual(audit.validate_template(self.template),23)
        self.assertEqual(self.template.count('-- Q'),23)

    @unittest.skipUnless(importlib.util.find_spec('pglast'), 'Parser PostgreSQL no instalado; gramática nativa pendiente QA')
    def test_postgresql_grammar_when_parser_available(self):
        from pglast import parse_sql
        sql=self.template.replace('@@RUNTIME@@', "'ss07_runtime'").replace('@@MIGRATOR@@', "'ss07_migrator'")
        self.assertEqual(len(parse_sql(sql)),23)

    def test_no_structural_or_data_writes(self):
        for sql in ('SELECT 1; DROP TABLE public.usuario;',
                    'WITH x AS (DELETE FROM public.usuario RETURNING *) SELECT * FROM x;',
                    'SELECT 1 INTO TEMP TABLE x;',
                    'GRANT SELECT ON public.usuario TO PUBLIC;',
                    'SELECT 1; SET ROLE owner;', 'COPY pg_catalog.pg_roles TO PROGRAM \'x\';'):
            with self.subTest(sql=sql),self.assertRaises(audit.PreparationError):audit.validate_template(sql)

    def test_only_reviewed_catalogs_and_functions(self):
        for sql in ('SELECT * FROM public.usuario;',
                    'SELECT pg_catalog.pg_sleep(1);','SELECT public.fn_audit_log();',
                    'SELECT pg_catalog.set_config(\'x\',\'y\',false);',
                    'SELECT * FROM pg_catalog.pg_authid;',
                    'SELECT * FROM pg_catalog.pg_stat_activity;',
                    'SELECT current_setting(\'secret\');',
                    'SELECT pg_catalog.nextval(\'x\');'):
            with self.subTest(sql=sql),self.assertRaises(audit.PreparationError):audit.validate_template(sql)

    def test_rejects_psql_escape_and_incomplete_lexical_syntax(self):
        for sql in ('SELECT 1;\\! echo bad','SELECT (1;',"SELECT 'bad;",'SELECT 1 /* bad',
                    'SELECT $$bad$$;','SELECT 1', 'SELECT "unknown";'):
            with self.subTest(sql=sql),self.assertRaises(audit.PreparationError):audit.validate_template(sql)

    def test_strings_and_nested_comments_are_not_commands(self):
        self.assertEqual(audit.validate_template("/* a /* nested */ b */ SELECT 'DELETE; DROP ''table''';"),1)

    def test_offline_opt_in_required_even_for_preparation(self):
        for data,approval,confirmed in ((config(),'QA-SINTETICA-0007',False),
                    ({**config(),'clon_verificado':False},'QA-SINTETICA-0007',True),
                    (config(),'QA-OTRA-0007',True),
                    ({**config(),'autorizacion':'QA-PENDIENTE'},'QA-PENDIENTE',True)):
            with self.assertRaises(audit.PreparationError):audit.validate_config(data,approval,confirmed)

    def test_a_qa_database_name_alone_is_insufficient(self):
        data=config();data['database']='software_pa_test';data['clon_verificado']=False
        with self.assertRaises(audit.PreparationError):audit.validate_config(data,data['autorizacion'],True)

    def test_rejects_credentials_and_injected_metadata(self):
        for changes in ({'password':'SENTINEL_PASSWORD_SS07_7941'},
                        {'runtime':"x'; SELECT pg_sleep(1); --"}, {'server_port':True},
                        {'server_addr':'institutional.example'}, {'database':'postgresql://secret'}):
            data={**config(),**changes}
            with self.subTest(changes=changes),self.assertRaises(audit.PreparationError):
                audit.validate_config(data,data['autorizacion'],True)

    def test_both_identities_are_checked_not_switched(self):
        script=audit.render(config())
        self.assertIn("'ss07_runtime' <> 'ss07_migrator'",script)
        self.assertIn('runtime_migrator_distintos',script)
        self.assertNotIn('SET ROLE',script)
        # Same supplied identity is reported as a failed separation, never hidden.
        data=config();data['migrator']=data['runtime']
        self.assertIn("'ss07_runtime' <> 'ss07_runtime'",audit.render(data))

    def test_generated_script_requires_runtime_opt_in_and_target_guard(self):
        script=audit.render(config())
        self.assertLess(script.index('\\if :{?SS07_QA_AUTORIZADA}'),script.index('BEGIN'))
        self.assertLess(script.index('\\if :ss07_destino_verificado'),script.index('-- Q00'))
        for token in ('session_user=','current_user=session_user','inet_server_addr','inet_server_port',
                      'cluster_name','server_version_num','READ ONLY','ROLLBACK;',
                      'search_path = pg_catalog, pg_temp','statement_timeout','lock_timeout'):
            self.assertIn(token,script)
        self.assertNotIn('COMMIT;',script)

    def test_coverage_of_privileges_and_objects(self):
        for token in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER',
                      'USAGE','EXECUTE','CREATE','CONNECT','TEMPORARY',
                      'pg_default_acl','pg_auth_members','pg_parameter_acl','pg_attribute',
                      'prosecdef','proconfig','pg_extension','pg_depend','pg_trigger','polroles'):
            self.assertIn(token,self.template)
        self.assertNotIn('pg_get_functiondef',self.template)
        self.assertNotIn('pg_get_viewdef',self.template)
        self.assertNotIn('last_value',audit.masked_sql(self.template))

    def test_existing_output_and_symlinks_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'owned.sql';audit.write_private(path,'owned')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            with self.assertRaises(FileExistsError):audit.write_private(path,'replacement')
            symlink=Path(directory)/'alias.sql';symlink.symlink_to(path)
            with self.assertRaises(FileExistsError):audit.write_private(symlink,'replacement')
            self.assertEqual(path.read_text(),'owned')

    def test_main_prepares_only_a_private_local_file(self):
        with tempfile.TemporaryDirectory() as directory:
            settings=Path(directory)/'qa.json';settings.write_text(json.dumps(config()))
            output=Path(directory)/'verify.sql';stdout=io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result=audit.main(['--config',str(settings),'--autorizacion-qa','QA-SINTETICA-0007',
                                   '--clon-desechable-verificado','--salida',str(output)])
            self.assertEqual(result,0)
            self.assertEqual(stdout.getvalue(),'SS07_SQL_PREPARADO_OFFLINE: no se abrió ninguna conexión.\n')
            self.assertIn('READ ONLY',output.read_text())

    def test_no_sensitive_values_printed_on_error(self):
        sentinel='SS07_SYNTHETIC_CREDENTIAL_SENTINEL_7941'
        with tempfile.TemporaryDirectory() as directory:
            settings=Path(directory)/'qa.json';settings.write_text(json.dumps({**config(),'password':sentinel}))
            stdout,stderr=io.StringIO(),io.StringIO()
            with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                status=audit.main(['--config',str(settings),'--autorizacion-qa','QA-SINTETICA-0007',
                                  '--clon-desechable-verificado','--salida',str(Path(directory)/'out.sql')])
            self.assertEqual(status,2)
            self.assertNotIn(sentinel,stdout.getvalue()+stderr.getvalue())
            self.assertNotIn(str(settings),stdout.getvalue()+stderr.getvalue())
            self.assertNotIn('Traceback',stderr.getvalue())

    def test_unknown_cli_values_are_not_echoed(self):
        sentinel='SS07_UNKNOWN_ARGUMENT_SECRET_7143'
        stdout,stderr=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            status=audit.main(['--password',sentinel])
        self.assertEqual(status,2)
        self.assertNotIn(sentinel,stdout.getvalue()+stderr.getvalue())
        self.assertNotIn('Traceback',stderr.getvalue())

    def test_helper_has_no_execution_network_env_or_backend_imports(self):
        tree=ast.parse((ASSETS/'preparar_verificador.py').read_text())
        imported=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imported.update(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom):imported.add(node.module)
            if isinstance(node,ast.Attribute):self.assertNotIn(node.attr,{'environ','getenv','system','popen','connect','execv','execve'})
        self.assertLessEqual(imported,{'argparse','ipaddress','json','os','pathlib','re','sys'})

    def test_migration_manifest_matches_all_current_sources(self):
        inventory=json.loads((ASSETS/'inventario-estatico.json').read_text())
        expected={m['file'] for m in inventory['migrations']}
        actual={str(p.relative_to(ROOT)) for p in (ROOT/'backend/db/migrations').glob('[0-9][0-9][0-9]_*.sql') if p.is_file()}
        self.assertEqual(expected,actual)
        self.assertEqual(len(expected),30)
        for migration in inventory['migrations']:
            self.assertEqual(hashlib.sha256((ROOT/migration['file']).read_bytes()).hexdigest(),migration['sha256'])

    def test_all_declared_models_and_object_kinds_are_inventoried(self):
        inventory=json.loads((ASSETS/'inventario-estatico.json').read_text())
        tree=ast.parse((ROOT/'backend/app/models.py').read_text())
        model_tables=set()
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef):
                for item in cls.body:
                    if isinstance(item,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__tablename__' for t in item.targets):model_tables.add(ast.literal_eval(item.value))
        self.assertEqual(model_tables,{m['relation'] for m in inventory['models']})
        names={o['name'] for o in inventory['objects']}
        self.assertLessEqual(model_tables,names)
        self.assertEqual({o['kind'] for o in inventory['objects']},{'TABLE','VIEW','FUNCTION','SEQUENCE'})
        self.assertIn('fn_audit_log',names)
        self.assertIn('schema_migrations',names)

    def test_safe_example_cannot_enable_qa(self):
        data=json.loads((ASSETS/'config-ejemplo.json').read_text())
        with self.assertRaises(audit.PreparationError):audit.validate_config(data,data['autorizacion'],True)

    def test_triggers_extensions_and_implicit_sequences_have_sources(self):
        inventory=json.loads((ASSETS/'inventario-estatico.json').read_text())
        self.assertEqual({e['name'] for e in inventory['extension_declarations']},{'postgis','btree_gist'})
        self.assertIn('trg_documento_version_inmutable',{t['name'] for t in inventory['literal_trigger_declarations']})
        self.assertIn('trg_auth_evento_inmutable',{t['name'] for t in inventory['literal_trigger_declarations']})
        self.assertEqual({s['table'] for s in inventory['implicit_sequence_columns_without_explicit_name']},
                         {'seguimiento_evento','catalogo_tipo_documento'})
        self.assertTrue(inventory['dynamic_execute_format_sites'])


if __name__=='__main__':unittest.main()
