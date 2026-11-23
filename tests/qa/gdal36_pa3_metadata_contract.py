"""Emit a C regression unit from prepared +pa3 source; never compile or run it.

F2 must compile/run the emitted unit under its explicitly authorized QA policy.
The real changed functions are tested with bounded HDF I/O doubles, not rewritten
Python models. Full GDAL/HDF fixture validation remains separately mandatory.
"""
import argparse
from pathlib import Path
import re


def function(source, name):
    start = re.search(r'^' + name + r'\(', source, re.M).start()
    end = source.index('\n}', source.index('{', start)) + 2
    return source[start:end]


PREFIX = r'''
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <stdio.h>
#include <assert.h>
typedef int intn; typedef int32_t int32; typedef void *VOIDP;
#define UTLSTR_MAX_SIZE 512
#define UTLSTRSIZE 32000
#define H4_MAX_NC_NAME 256
#define DFNT_MASK 0xfff
#define DFNT_CHAR8 4
#define DFNT_UCHAR8 3
#define SWIDOFFSET 1048576
#define NSWATH 200
#define DFE_GENAPP 1
#define DFE_NOSPACE 2
struct sw { int32 IDTable; int32 nSDS; int32 *sdsID; } SWXSwath[NSWATH];
static const char *metadata;
static int fail_read;
static int errors;
int32 SDfindattr(int32 id, const char *name) {
    (void)id;return !strcmp(name,"StructMetadata.0")?0:-1;
}
int SDattrinfo(int32 id,int32 index,char *name,int32 *type,int32 *count) {
    (void)id;(void)index;strcpy(name,"StructMetadata.0");
    *type=DFNT_CHAR8;*count=(int32)strlen(metadata)+1;return 0;
}
int SDreadattr(int32 id,int32 index,void *output) {
    (void)id;(void)index;if(fail_read)return -1;
    memcpy(output,metadata,strlen(metadata)+1);return 0;
}
int SDgetinfo(int32 id,char *name,int32 *rank,int32 *dims,int32 *type,int32 *attrs) {
    (void)id;strcpy(name,"MRGFLD_test");*rank=2;dims[0]=2;dims[1]=2;
    *type=5;*attrs=0;return 0;
}
int Vgetname(int32 id,char *name) {(void)id;strcpy(name,"SyntheticSwath");return 0;}
int EHstrwithin(const char *a,const char *b,char sep) {(void)a;(void)b;(void)sep;return -1;}
int HEpush(int error,const char *name,const char *file,int line) {
    (void)error;(void)name;(void)file;(void)line;errors++;return 0;
}
'''

CASES = r'''
static void check_helpers(void) {
    char input[]="Key=abc\nOther=outside\n";
    char *p[2]={input,input+8};char out[16];
    assert(EHgetmetavalue(p,"Key",out,sizeof(out))==0 && !strcmp(out,"abc"));
    p[0]=input;p[1]=input+7;strcpy(out,"sentinel");
    assert(EHgetmetavalue(p,"Key",out,sizeof(out))==-1 && out[0]==0);
    p[0]=input;p[1]=input+8;
    assert(EHgetmetavalue(p,"Other",out,sizeof(out))==-1 && out[0]==0);
    assert(EHgetmetavalue(p,"Key",out,3)==-1 && out[0]==0);
    assert(EHgetmetavalue(p,"Key",out,4)==0 && !strcmp(out,"abc"));
    p[0]=NULL;assert(EHgetmetavalue(p,"Key",out,sizeof(out))==-1 && out[0]==0);
    p[0]=input+8;p[1]=input;
    assert(EHgetmetavalue(p,"Key",out,sizeof(out))==-1);
    p[0]=p[1]=input;assert(EHgetmetavalue(p,"Key",out,sizeof(out))==-1);
    p[0]=input;p[1]=input+8;
    assert(EHgetmetavalue(p,"Key",out,0)==-1);
}
static void check_sections(void) {
    char *p[2]={(char*)1,(char*)1};char *buffer;
    metadata="GROUP=SwathStructure\n\tGROUP=SWATH_1\n\t\tSwathName=\"SyntheticSwath\"\n"
             "\t\tGROUP=DimensionMap\n\t\tEND_GROUP=DimensionMap\n"
             "\tEND_GROUP=SWATH_1\nEND_GROUP=SwathStructure\n";
    buffer=EHmetagroup(0,"SyntheticSwath","s","DimensionMap",p);
    assert(buffer && p[0] && p[1] && p[0]<p[1]);free(buffer);
    buffer=EHmetagroup(0,"SyntheticSwath","s","MergedFields",p);
    assert(!buffer && !p[0] && !p[1]);
    buffer=EHmetagroup(0,"SyntheticSwathExtra","s","DimensionMap",p);
    assert(!buffer && !p[0] && !p[1]);
    buffer=EHmetagroup(0,"Synthetic","s","DimensionMap",p);
    assert(!buffer && !p[0] && !p[1]);
    buffer=EHmetagroup(0,"SyntheticSwath","bad","DimensionMap",p);
    assert(!buffer && !p[0] && !p[1]);
    fail_read=1;buffer=EHmetagroup(0,"SyntheticSwath","s","DimensionMap",p);
    assert(!buffer && !p[0] && !p[1]);fail_read=0;
    metadata="GROUP=SwathStructure\n\tGROUP=\"SyntheticSwath\"\n"
             "\t\tGROUP=DimensionMap\n\t\tEND_GROUP=DimensionMap\n"
             "\tEND_GROUP=\"SyntheticSwath\"\nEND_GROUP=SwathStructure\n";
    buffer=EHmetagroup(0,"SyntheticSwath","s","DimensionMap",p);
    assert(buffer && p[0]<p[1]);free(buffer);
    metadata="GROUP=SwathStructure\nEND_GROUP=SwathStructure\n";
    buffer=EHmetagroup(0,"SyntheticSwath","s","MergedFields",p);
    assert(!buffer && !p[0] && !p[1]);
}
static void check_required_merged_section(void) {
    int32 sds[1]={1},sdid=0,rank=0,fieldrank=0,offset=0,dims[32]={0},solo=0;
    SWXSwath[0].IDTable=1;SWXSwath[0].nSDS=1;SWXSwath[0].sdsID=sds;
    metadata="GROUP=SwathStructure\n\tGROUP=SWATH_1\n\t\tSwathName=\"SyntheticSwath\"\n"
             "\tEND_GROUP=SWATH_1\nEND_GROUP=SwathStructure\n";
    assert(SWSDfldsrch(SWIDOFFSET,0,"Temperature",&sdid,&rank,&fieldrank,
                      &offset,dims,&solo)==-1);
    assert(errors>0);
}
int main(void) {
    check_helpers();check_sections();check_required_merged_section();
    puts("PA3_METADATA_HELPER_CONTRACTS_OK");return 0;
}
'''


def emit(source, output):
    eos = source / 'frmts/hdf4/hdf-eos'
    eh = (eos / 'EHapi.c').read_text()
    sw = (eos / 'SWapi.c').read_text()
    code = PREFIX + '\nintn\n' + function(eh, 'EHgetmetavalue')
    code += '\nchar *\n' + function(eh, 'EHmetagroup')
    code += '\nintn\n' + function(sw, 'SWSDfldsrch') + '\n' + CASES
    if output.exists():
        raise ValueError('Refusing to overwrite an existing QA unit')
    output.write_text(code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--emit-only', required=True, type=Path)
    args = parser.parse_args()
    emit(args.source, args.emit_only)
