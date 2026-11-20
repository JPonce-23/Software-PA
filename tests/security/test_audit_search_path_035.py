"""Offline SQL review gates; native before/after tests live in the PA5-QA harness."""
import hashlib
from pathlib import Path
import unittest
from pglast import ast,parse_sql

ROOT=Path(__file__).resolve().parents[2]
MIGRATIONS=ROOT/'backend/db/migrations'
TABLES=('evento_acceso','convenio','afectacion','indemnizacion','proyecto_nucleo','bitacora')
def functions(path):return [x.stmt for x in parse_sql(path.read_text()) if isinstance(x.stmt,ast.CreateFunctionStmt)]
def body(fn):return next(x.arg[0].sval for x in fn.options if x.defname=='as')

class Audit035Tests(unittest.TestCase):
    def test_all_historical_security_definers_have_been_reviewed(self):
        found=[]
        for p in sorted(MIGRATIONS.glob('[0-9][0-9][0-9]_*.sql')):
            if p.name[:3]>'034':continue
            for fn in functions(p):
                if any(x.defname=='security' and x.arg.boolval for x in fn.options):found.append((p.name[:3],'.'.join(x.sval for x in fn.funcname)))
        self.assertEqual(found,[(v,'public.fn_audit_log') for v in ['001','010','011','020']])

    def test_hardened_function_preserves_020_business_logic(self):
        before=body(functions(MIGRATIONS/'020_auditoria_heartbeat_sesion.sql')[0])
        after=body(functions(MIGRATIONS/'035_endurecer_auditoria_search_path.sql')[0])
        guard="    IF TG_TABLE_SCHEMA <> 'public' THEN\n        RAISE EXCEPTION 'Auditoría sólo admite relaciones de public';\n    END IF;\n"
        self.assertIn(guard,after)
        after=after.replace(guard,'',1)
        for table in TABLES:after=after.replace('public.'+table,table)
        self.assertEqual(before,after,'Only namespace hardening and trigger origin may change')

    def test_035_is_forward_only_and_does_not_change_global_privileges(self):
        statements=[x.stmt for x in parse_sql((MIGRATIONS/'035_endurecer_auditoria_search_path.sql').read_text())]
        fn=next(x for x in statements if isinstance(x,ast.CreateFunctionStmt))
        self.assertTrue(fn.replace)
        self.assertEqual([x.sval for x in fn.funcname],['public','fn_audit_log'])
        options={x.defname:x.arg for x in fn.options}
        self.assertTrue(options['security'].boolval)
        self.assertEqual([x.val.sval for x in options['set'].args],['pg_catalog','public','pg_temp'])
        self.assertFalse(any(isinstance(x,(ast.GrantStmt,ast.AlterRoleStmt,ast.DropStmt)) for x in statements))
        sql=(MIGRATIONS/'035_endurecer_auditoria_search_path.sql').read_text()
        h=hashlib.sha256((MIGRATIONS/'034_seguimiento_fifonafe_etiquetas.sql').read_bytes()).hexdigest()
        self.assertIn(h,sql)

if __name__=='__main__':unittest.main()
