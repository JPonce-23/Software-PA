"""Logical PostgreSQL signatures; no personal values are emitted."""
import hashlib
import json
from psycopg2 import sql

DATA_TABLES = (
    'proyecto', 'proyecto_nucleo', 'nucleo_agrario', 'parcela', 'afectacion',
    'convenio', 'seguimiento_evento', 'tramite_ran', 'tramite_ran_evento',
    'derecho_via_proyecto', 'proyecto_configuracion_gis',
    'proyecto_nucleo_geometria', 'proyecto_parcela_geometria',
    'importacion_archivo', 'importacion_feature',
    'importacion_feature_candidato', 'importacion_feature_decision',
)

QUERIES = {
    'relations': """SELECT c.relname,c.relkind,c.relpersistence,c.relrowsecurity,c.relforcerowsecurity,
        pg_get_userbyid(c.relowner),COALESCE((SELECT array_agg(x::text ORDER BY x::text) FROM unnest(c.relacl) x),'{}'),
        CASE WHEN c.relkind IN ('v','m') THEN pg_get_viewdef(c.oid,false) END
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f') ORDER BY c.relname""",
    'columns': """SELECT c.relname,a.attnum,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,
        a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid),
        CASE WHEN a.atttypid='geometry'::regtype AND a.atttypmod>=0 THEN postgis_typmod_type(a.atttypmod) END,
        CASE WHEN a.atttypid='geometry'::regtype AND a.atttypmod>=0 THEN postgis_typmod_dims(a.atttypmod) END,
        CASE WHEN a.atttypid='geometry'::regtype AND a.atttypmod>=0 THEN postgis_typmod_srid(a.atttypmod) END
        FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
        WHERE n.nspname='public' AND a.attnum>0 AND NOT a.attisdropped
        AND c.relkind IN ('r','p','v','m','f') ORDER BY c.relname,a.attnum""",
    'constraints': """SELECT c.relname,k.conname,k.contype,k.convalidated,k.condeferrable,k.condeferred,
        pg_get_constraintdef(k.oid,false) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname,k.conname""",
    'indexes': """SELECT t.relname,c.relname,pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,
        i.indisvalid,i.indisready,pg_get_expr(i.indpred,i.indrelid),am.amname
        FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_class t ON t.oid=i.indrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace JOIN pg_am am ON am.oid=c.relam
        WHERE n.nspname='public' ORDER BY t.relname,c.relname""",
    'triggers': """SELECT c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid,false)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname""",
    'functions': """SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid),
        pg_get_userbyid(p.proowner),COALESCE((SELECT array_agg(x::text ORDER BY x::text) FROM unnest(p.proacl) x),'{}')
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND p.prokind IN ('f','p') AND NOT EXISTS
        (SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e')
        ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)""",
    'sequences': """SELECT c.relname,format_type(s.seqtypid,NULL),s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle,
        t.relname,a.attname,d.deptype FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_depend d ON d.classid='pg_class'::regclass
        AND d.objid=c.oid AND d.deptype IN ('a','i') LEFT JOIN pg_class t ON t.oid=d.refobjid
        LEFT JOIN pg_attribute a ON a.attrelid=d.refobjid AND a.attnum=d.refobjsubid
        WHERE n.nspname='public' ORDER BY c.relname""",
    'extensions': "SELECT e.extname,e.extversion,n.nspname,pg_get_userbyid(e.extowner) FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace ORDER BY e.extname",
    'types': """SELECT t.typname,t.typtype,format_type(t.typbasetype,t.typtypmod),t.typnotnull,t.typdefault,
        pg_get_userbyid(t.typowner),(SELECT array_agg(e.enumlabel ORDER BY e.enumsortorder) FROM pg_enum e WHERE e.enumtypid=t.oid)
        FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public'
        AND t.typtype IN ('d','e') ORDER BY t.typname""",
    'policies': "SELECT tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname",
    'schema_acl': "SELECT nspname,pg_get_userbyid(nspowner),nspacl::text FROM pg_namespace WHERE nspname='public'",
    'default_acl': """SELECT pg_get_userbyid(d.defaclrole),COALESCE(n.nspname,''),d.defaclobjtype,
        (SELECT array_agg(x::text ORDER BY x::text) FROM unnest(d.defaclacl) x)
        FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace ORDER BY 1,2,3""",
}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def schema_signature(connection):
    result={}
    with connection.cursor() as cur:
        cur.execute('SET LOCAL search_path=public,pg_catalog')
        for name,query in QUERIES.items():
            cur.execute(query)
            result[name]=[list(row) for row in cur.fetchall()]
    return result

def data_signature(connection):
    result={}
    with connection.cursor() as cur:
        for table in DATA_TABLES:
            cur.execute("SELECT a.attname,a.atttypid='geometry'::regtype FROM pg_attribute a WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",('public.'+table,))
            cols=cur.fetchall()
            expressions=[sql.SQL("encode(ST_AsEWKB({},'NDR'),'hex')").format(sql.Identifier(n)) if geom else sql.Identifier(n) for n,geom in cols]
            # Digest every complete row inside PostgreSQL; only count/hash leave it.
            query=sql.SQL("SELECT count(*),md5(COALESCE(string_agg(h,'' ORDER BY h),'')) FROM (SELECT md5(row_to_json(r)::text) h FROM (SELECT {} FROM public.{}) r) rows").format(sql.SQL(',').join(expressions),sql.Identifier(table))
            cur.execute(query)
            count,checksum=cur.fetchone()
            result[table]={'count':count,'rows_md5':checksum}
    return result

def ledger(connection):
    with connection.cursor() as cur:
        cur.execute('SELECT version,nombre,checksum_sha256,aplicada_en FROM public.schema_migrations ORDER BY version')
        return [dict(zip(('version','nombre','checksum_sha256','aplicada_en'),r)) for r in cur.fetchall()]
