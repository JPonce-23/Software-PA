"""Prepare a private opt-in psql script OFFLINE. Never connects or executes SQL.

The lexical checks protect this reviewed fixed template from common accidental
edits; they are not a PostgreSQL parser or a sandbox for arbitrary SQL.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
FIELDS = {'autorizacion', 'clon_verificado', 'database', 'server_addr', 'server_port',
          'cluster_marker', 'inspector', 'runtime', 'migrator'}
CATALOGS = {'pg_roles','pg_auth_members','pg_database','pg_namespace','pg_class',
 'pg_attribute','pg_depend','pg_extension','pg_proc','pg_language','pg_default_acl',
 'pg_trigger','pg_rewrite','pg_db_role_setting','pg_policy','pg_type','pg_parameter_acl'}
FUNCTIONS = {'current_database','current_setting','pg_has_role','pg_get_userbyid',
 'has_database_privilege','has_schema_privilege','has_table_privilege','has_column_privilege',
 'has_sequence_privilege','has_function_privilege','aclexplode','acldefault','unnest',
 'has_type_privilege','has_language_privilege','has_parameter_privilege'}

class PreparationError(ValueError):
    pass


class QuietArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error includes unknown values supplied on the CLI.
        raise PreparationError('Argumentos inválidos; no se muestran sus valores.')


def validate_config(data, authorization, disposable_confirmed):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise PreparationError('Configuración inválida: sólo metadatos QA previstos; no credenciales.')
    if disposable_confirmed is not True or data['clon_verificado'] is not True:
        raise PreparationError('Se requiere comprobación y autorización externa de clon QA desechable.')
    if not isinstance(authorization, str) or not re.fullmatch(r'QA-[A-Z0-9-]{4,60}', authorization) or 'PENDIENTE' in authorization:
        raise PreparationError('Se requiere identificador de autorización QA válido.')
    if data['autorizacion'] != authorization:
        raise PreparationError('La autorización QA no coincide.')
    for key in ('database','cluster_marker','inspector','runtime','migrator'):
        if not isinstance(data[key], str) or not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', data[key]):
            raise PreparationError('Identificador de metadatos inválido.')
    if type(data['server_port']) is not int or not 1 <= data['server_port'] <= 65535:
        raise PreparationError('Puerto QA inválido.')
    if not isinstance(data['server_addr'], str):
        raise PreparationError('Se requiere IP numérica explícita del servidor QA.')
    try:
        ipaddress.ip_address(data['server_addr'])
    except (ValueError, TypeError):
        raise PreparationError('Se requiere IP numérica explícita del servidor QA.') from None
    return data


def masked_sql(sql):
    """Mask strings/comments; check lexical balance, not SQL grammar."""
    result=[]; pos=0; depth=0
    while pos < len(sql):
        if sql.startswith('--', pos):
            end=sql.find('\n',pos); end=len(sql) if end<0 else end
            result.append(' '*(end-pos));pos=end;continue
        if sql.startswith('/*',pos):
            start=pos; nesting=1;pos+=2
            while pos<len(sql) and nesting:
                if sql.startswith('/*',pos):nesting+=1;pos+=2
                elif sql.startswith('*/',pos):nesting-=1;pos+=2
                else:pos+=1
            if nesting:raise PreparationError('Comentario SQL incompleto.')
            result.append(' '*(pos-start));continue
        char=sql[pos]
        if char=="'":
            start=pos;pos+=1
            while pos<len(sql):
                if sql[pos]=="'":
                    if pos+1<len(sql) and sql[pos+1]=="'":pos+=2;continue
                    pos+=1;break
                if sql[pos]=='\\':raise PreparationError('Escape SQL no admitido en plantilla.')
                pos+=1
            else:raise PreparationError('Literal SQL incompleto.')
            result.append(' '*(pos-start));continue
        if char=='"':
            if not sql.startswith('"char"',pos):raise PreparationError('Identificador citado inesperado.')
            result.append(' char ');pos+=6;continue
        if char in ('\\','$','\x00'):raise PreparationError('Construcción SQL no permitida.')
        if char=='(':depth+=1
        if char==')':
            depth-=1
            if depth<0:raise PreparationError('Paréntesis SQL inválidos.')
        result.append(char);pos+=1
    if depth:raise PreparationError('Paréntesis SQL incompletos.')
    return ''.join(result)


def validate_template(sql):
    rendered=sql.replace('@@RUNTIME@@',"'runtime_qa'").replace('@@MIGRATOR@@',"'migrator_qa'")
    if '@@' in rendered:raise PreparationError('Marcador SQL desconocido.')
    masked=masked_sql(rendered)
    words={w.upper() for w in re.findall(r'\b[A-Za-z_]\w*\b',masked)}
    forbidden={'INSERT','UPDATE','DELETE','TRUNCATE','CREATE','ALTER','DROP','GRANT','REVOKE',
               'COPY','CALL','DO','EXECUTE','INTO','LOCK','VACUUM','ANALYZE','SET','RESET','COMMIT'}
    if words & forbidden:raise PreparationError('La plantilla no es exclusivamente de inspección.')
    statements=[s.strip() for s in masked.split(';') if s.strip()]
    if not statements or not masked.rstrip().endswith(';'):
        raise PreparationError('Sentencias SQL incompletas.')
    for statement in statements:
        if not re.match(r'^(SELECT|WITH)\b',statement,re.I):raise PreparationError('Sentencia no permitida.')
    for match in re.finditer(r'\b(FROM|JOIN)\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)',masked,re.I):
        source=match[2].lower()
        if source not in {'identidades','objetos','lateral'} and source not in {'pg_catalog.'+n for n in CATALOGS|{'aclexplode','unnest'}}:
            raise PreparationError('Origen fuera del catálogo permitido.')
    for match in re.finditer(r'(?<![\w.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*\(',masked):
        token=match[1].lower()
        if token in {'as','in','exists','array','coalesce'}:continue
        if token not in {'pg_catalog.'+n for n in FUNCTIONS}:
            raise PreparationError('Función fuera de la lista de metadatos permitida.')
    return len(statements)


def render(data):
    template=(ROOT/'consultas-privilegios.sql.in').read_text()
    validate_template(template)
    # All inserted values were constrained to identifiers/IP/int above.
    sql=template.replace('@@RUNTIME@@',"'"+data['runtime']+"'").replace('@@MIGRATOR@@',"'"+data['migrator']+"'")
    header=f"""-- SS-07; autorización externa {data['autorizacion']}; metadatos QA, NO credenciales.
-- No ejecutar sin aprobación independiente, destino explícito y psql -X.
\\set ON_ERROR_STOP on
\\if :{{?SS07_QA_AUTORIZADA}}
\\else
\\echo SS07_RECHAZADO_FALTA_OPT_IN
\\quit
\\endif
\\if :SS07_QA_AUTORIZADA
\\else
\\echo SS07_RECHAZADO_FALTA_OPT_IN
\\quit
\\endif
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL search_path = pg_catalog, pg_temp;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '1s';
SELECT pg_catalog.current_database()='{data['database']}'
 AND session_user='{data['inspector']}' AND current_user=session_user
 AND pg_catalog.host(pg_catalog.inet_server_addr())='{data['server_addr']}'
 AND pg_catalog.inet_server_port()={data['server_port']}
 AND pg_catalog.current_setting('cluster_name',true)='{data['cluster_marker']}'
 AND pg_catalog.current_setting('server_version_num')::integer BETWEEN 150000 AND 159999
 AS ss07_destino_verificado
\\gset
\\if :ss07_destino_verificado
\\echo SS07_DESTINO_QA_COINCIDE_NO_EQUIVALE_A_AUTORIZACION
"""
    footer="""
ROLLBACK;
\\echo SS07_INSPECCION_COMPLETA_REVISAR_OMISIONES_Y_RESULTADOS
\\else
ROLLBACK;
\\echo SS07_RECHAZADO_DESTINO_NO_COINCIDE
\\quit
\\endif
"""
    return header+sql+footer


def write_private(path, content):
    # Never overwrite a report or follow an output symlink.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:stream.write(content)


def main(argv=None):
    parser=QuietArgumentParser(description='Preparación OFFLINE; no conecta ni ejecuta SQL.')
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--autorizacion-qa',required=True)
    parser.add_argument('--clon-desechable-verificado',action='store_true')
    parser.add_argument('--salida',required=True,type=Path)
    try:
        args=parser.parse_args(argv)
        data=json.loads(args.config.read_text())
        validate_config(data,args.autorizacion_qa,args.clon_desechable_verificado)
        write_private(args.salida,render(data))
    except (PreparationError,OSError,ValueError,TypeError):
        # No paths/config contents/exception objects in output.
        print('SS07_PREPARACION_RECHAZADA: revisar autorización, metadatos y salida exclusiva.',file=sys.stderr)
        return 2
    print('SS07_SQL_PREPARADO_OFFLINE: no se abrió ninguna conexión.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
