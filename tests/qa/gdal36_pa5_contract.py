"""Emit focused pa5 source-derived units with bounded I/O doubles.
Never build GDAL, packages or images. Executing these units is logic QA only;
all 23 mapped-library functional gates remain NOT RUN until a future campaign.
"""
import argparse
from pathlib import Path
import re
import sys
sys.dont_write_bytecode=True
FUNCTIONS = {
  "field-contract.c": [
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHparsestr"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHfieldvalue"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHfindfield"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHmetagroupstatus"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHmetagroup"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHfieldinventory"
    ]
  ],
  "fieldinfo-contract.c": [
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHparsestr"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHfieldvalue"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHfindfield"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHmetagroupstatus"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHmetagroup"
    ],
    [
      "frmts/hdf4/hdf-eos/EHapi.c",
      "EHfieldinventory"
    ],
    [
      "frmts/hdf4/hdf-eos/SWapi.c",
      "SWfinfo"
    ],
    [
      "frmts/hdf4/hdf-eos/SWapi.c",
      "SWfieldinventory"
    ],
    [
      "frmts/hdf4/hdf-eos/GDapi.c",
      "GDfieldinfo"
    ],
    [
      "frmts/hdf4/hdf-eos/GDapi.c",
      "GDfieldinventory"
    ]
  ],
  "consumer-contract.cpp": [
    [
      "frmts/hdf4/hdf4multidim.cpp",
      "HDF4SwathSubGroup::GetMDArrayNames"
    ],
    [
      "frmts/hdf4/hdf4multidim.cpp",
      "HDF4EOSGridSubGroup::GetMDArrayNames"
    ],
    [
      "frmts/hdf4/hdf4multidim.cpp",
      "HDF4SwathSubGroup::OpenMDArray"
    ],
    [
      "frmts/hdf4/hdf4multidim.cpp",
      "HDF4EOSGridSubGroup::OpenMDArray"
    ]
  ]
}

TEMPLATES = {
    'field-contract.c': r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef int intn; typedef int32_t int32;
#define UTLSTR_MAX_SIZE 512
#define UTLSTRSIZE 32000
#define H4_MAX_NC_NAME 256
#define DFNT_MASK 0xfff
#define DFNT_CHAR8 4
#define DFNT_UCHAR8 3
#define H4_MAX_VAR_DIMS 32
typedef enum { HDFE_FIELD_ERROR=-1,HDFE_FIELD_UNAVAILABLE=0,HDFE_FIELD_RETAIN=1 } HDFEFieldInventoryStatus;
#define EH_METAGROUP_ERROR (-1)
#define EH_METAGROUP_ABSENT 0
#define EH_METAGROUP_PRESENT 1
static const char *metadata;
static int fail_read,fail_sds,nonmerged;
static const char *extra_metadata;
int32 SDfindattr(int32 id,const char *name){(void)id; if(!strcmp(name,"StructMetadata.0"))return 0; if(extra_metadata && !strcmp(name,"StructMetadata.1"))return 1; return -1;}
int SDattrinfo(int32 id,int32 index,char *name,int32 *type,int32 *count){(void)id;strcpy(name,index?"StructMetadata.1":"StructMetadata.0");*type=DFNT_CHAR8;*count=(int32)strlen(index?extra_metadata:metadata)+1;return 0;}
int SDreadattr(int32 id,int32 index,void *out){(void)id;if(fail_read)return -1;strcpy(out,index?extra_metadata:metadata);return 0;}
int32 SDgetinfo(int32 id,char *name,int32 *rank,int32 *dims,int32 *type,int32 *attrs){(void)id;if(fail_sds)return -1;strcpy(name,nonmerged?"Temperature":"MRGFLD_test");*rank=2;dims[0]=2;dims[1]=2;*type=5;*attrs=0;return 0;}
int32 EHnumstr(const char *name){return !strcmp(name,"DFNT_FLOAT32")?5:-1;}

int32
@@FUNCTION_0@@

intn
@@FUNCTION_1@@

intn
@@FUNCTION_2@@

char *
@@FUNCTION_3@@

char *
@@FUNCTION_4@@

HDFEFieldInventoryStatus
@@FUNCTION_5@@

static char whole[12000];
static void make(int grid,const char *field,const char *first,const char *mapping,int quoted){
 snprintf(whole,sizeof(whole),"GROUP=%sStructure\n\tGROUP=%s_1\n\t\t%sName=\"Synthetic\"\n\t\tGROUP=Dimension\n\t\t\tOBJECT=Dim_1\n\t\t\t\tDimensionName=\"AppDim\"\n\t\t\t\tSize=0\n\t\t\tEND_OBJECT=Dim_1\n\t\t\tOBJECT=Dim_2\n\t\t\t\tDimensionName=\"YDim\"\n\t\t\t\tSize=10\n\t\t\tEND_OBJECT=Dim_2\n\t\tEND_GROUP=Dimension\n\t\tGROUP=DataField\n\t\t\tOBJECT=Field_1\n\t\t\t\tDataFieldName=%s%s%s\n\t\t\t\tDataType=DFNT_FLOAT32\n\t\t\t\tDimList=(\"%s\",\"YDim\")\n\t\t\tEND_OBJECT=Field_1\n\t\tEND_GROUP=DataField\n%s\tEND_GROUP=%s_1\nEND_GROUP=%sStructure\n",grid?"Grid":"Swath",grid?"GRID":"SWATH",grid?"Grid":"Swath",quoted?"\"":"",field,quoted?"\"":"",first,mapping,grid?"GRID":"SWATH",grid?"Grid":"Swath");metadata=whole;
}
static const char *empty="\t\tGROUP=MergedFields\n\t\t\tOBJECT=Merged_1\n\t\t\t\tMergedFieldName=\"MRGFLD_test\"\n\t\t\t\tFieldList=\n\t\t\tEND_OBJECT=Merged_1\n\t\tEND_GROUP=MergedFields\n";
static const char *mapped="\t\tGROUP=MergedFields\n\t\t\tOBJECT=Merged_1\n\t\t\t\tMergedFieldName=\"MRGFLD_test\"\n\t\t\t\tFieldList=\"Temperature\"\n\t\t\tEND_OBJECT=Merged_1\n\t\tEND_GROUP=MergedFields\n";
int main(void){
 int32 ids[2]={1,0};char *p[2];char *b;char value[512];
 for(int grid=0;grid<2;grid++)for(int quoted=0;quoted<2;quoted++){
  make(grid,"Temperature","AppDim",empty,quoted);
  assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_UNAVAILABLE);
  fail_read=1;assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);fail_read=0;
  fail_sds=1;assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);fail_sds=0;
  nonmerged=1;assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_RETAIN);nonmerged=0;
  b=EHmetagroup(0,"Synthetic",grid?"g":"s","DataField",p);assert(b);assert(EHfindfield(p,"DataFieldName","Temp")==0);assert(EHfindfield(p,"DataFieldName","Temperature")==1);assert(EHfieldvalue(p,"DataType",value,sizeof(value))==0&&!strcmp(value,"DFNT_FLOAT32"));free(b);
  make(grid,"Temperature","AppDim",mapped,quoted);assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_RETAIN);
  make(grid,"Temperature","AppDim","",quoted);assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);
 }
 /* Grid implicit dimensions are valid without explicit Dimension entries. */
 make(1,"fld_01__","XDim","",0);assert(EHfieldinventory(0,"Synthetic","g","DataField","DataFieldName","fld_01__",2,ids)==HDFE_FIELD_RETAIN);
 /* CRLF and split attribute storage are checked through actual pa4 helper. */
 make(0,"Temperature","AppDim",empty,1);char crlf[24000];size_t j=0;for(size_t i=0;whole[i];i++){if(whole[i]=='\n')crlf[j++]='\r';crlf[j++]=whole[i];}crlf[j]=0;metadata=crlf;assert(EHfieldinventory(0,"Synthetic","s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_UNAVAILABLE);
 make(0,"Temperature","AppDim",empty,1);char part0[12000],part1[12000];size_t half=strlen(whole)/2;memcpy(part0,whole,half);part0[half]=0;strcpy(part1,whole+half);metadata=part0;extra_metadata=part1;assert(EHfieldinventory(0,"Synthetic","s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_UNAVAILABLE);extra_metadata=NULL;
 /* Old ODL exact OBJECT name and nonmatching adjacent names. */
 char old[]="\t\tOBJECT=\"A long name\"\r\n\t\t\tDataType=DFNT_FLOAT32\r\n\t\tEND_OBJECT=\"A long name\"\r\n";p[0]=old;p[1]=old+strlen(old);assert(EHfindfield(p,"DataFieldName","A long name")==1);assert(EHfieldvalue(p,"DataType",value,sizeof(value))==0&&!strcmp(value,"DFNT_FLOAT32"));
 char bad[]="OBJECT=X\nDataFieldName=Temperature\nEND_OBJECT=Y\n";p[0]=bad;p[1]=bad+strlen(bad);assert(EHfindfield(p,"DataFieldName","Temperature")==-1);
 char duplicate[]="OBJECT=X\nDataFieldName=A\nEND_OBJECT=X\nOBJECT=Y\nDataFieldName=A\nEND_OBJECT=Y\n";p[0]=duplicate;p[1]=duplicate+strlen(duplicate);assert(EHfindfield(p,"DataFieldName","A")==-1);
 char cap[]="Key=abc\n";p[0]=cap;p[1]=cap+strlen(cap);assert(EHfieldvalue(p,"Key",value,4)==0);assert(EHfieldvalue(p,"Key",value,3)==-1);
 /* A valid empty field collection is different from an invalid requested field. */
 metadata="GROUP=SwathStructure\n\tGROUP=S\n\t\tSwathName=\"Synthetic\"\n\t\tGROUP=DataField\n\t\tEND_GROUP=DataField\n\tEND_GROUP=S\nEND_GROUP=SwathStructure\n";b=EHmetagroup(0,"Synthetic","s","DataField",p);assert(b);assert(EHfindfield(p,"DataFieldName","Temperature")==0);free(b);assert(EHfieldinventory(0,"Synthetic","s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);
 puts("PA5_FIELD_INVENTORY_CONTRACT_OK");return 0;
}
''',
    'fieldinfo-contract.c': r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef int intn; typedef int32_t int32;
#define UTLSTR_MAX_SIZE 512
#define UTLSTRSIZE 32000
#define H4_MAX_NC_NAME 256
#define DFNT_MASK 0xfff
#define DFNT_CHAR8 4
#define DFNT_UCHAR8 3
#define H4_MAX_VAR_DIMS 32
typedef enum { HDFE_FIELD_ERROR=-1,HDFE_FIELD_UNAVAILABLE=0,HDFE_FIELD_RETAIN=1 } HDFEFieldInventoryStatus;
#define EH_METAGROUP_ERROR (-1)
#define EH_METAGROUP_ABSENT 0
#define EH_METAGROUP_PRESENT 1
static const char *metadata;
static int fail_read,fail_sds,nonmerged;
static const char *extra_metadata;
int32 SDfindattr(int32 id,const char *name){(void)id; if(!strcmp(name,"StructMetadata.0"))return 0; if(extra_metadata && !strcmp(name,"StructMetadata.1"))return 1; return -1;}
int SDattrinfo(int32 id,int32 index,char *name,int32 *type,int32 *count){(void)id;strcpy(name,index?"StructMetadata.1":"StructMetadata.0");*type=DFNT_CHAR8;*count=(int32)strlen(index?extra_metadata:metadata)+1;return 0;}
int SDreadattr(int32 id,int32 index,void *out){(void)id;if(fail_read)return -1;strcpy(out,index?extra_metadata:metadata);return 0;}
int32 SDgetinfo(int32 id,char *name,int32 *rank,int32 *dims,int32 *type,int32 *attrs){(void)id;if(fail_sds)return -1;strcpy(name,nonmerged?"Temperature":"MRGFLD_test");*rank=2;dims[0]=2;dims[1]=2;*type=5;*attrs=0;return 0;}
int32 EHnumstr(const char *name){return !strcmp(name,"DFNT_FLOAT32")?5:-1;}

int32
@@FUNCTION_0@@

intn
@@FUNCTION_1@@

intn
@@FUNCTION_2@@

char *
@@FUNCTION_3@@

char *
@@FUNCTION_4@@

HDFEFieldInventoryStatus
@@FUNCTION_5@@


typedef unsigned char uint8;
#define DFE_GENAPP 1
#define DFE_NOSPACE 2
#define HDFE_NENTDFLD 4
#define HDFE_NENTGFLD 3
#define SWIDOFFSET 1048576
#define GDIDOFFSET 4194304
#define NSWATH 200
#define NGRID 200
#define FULL_INTERLACE 0
struct swentry { int32 IDTable; int32 nSDS; int32 *sdsID; } SWXSwath[NSWATH],GDXGrid[NGRID];
int HEpush(int e,const char*n,const char*f,int l){(void)e;(void)n;(void)f;(void)l;return 0;}
void HEreport(const char *f,...){(void)f;}
int32 SWchkswid(int32 id,const char*n,int32*f,int32*s,int32*v){(void)id;(void)n;*f=*s=*v=0;return 0;}
int32 GDchkgdid(int32 id,const char*n,int32*f,int32*s,int32*v){return SWchkswid(id,n,f,s,v);}
int Vgetname(int32 id,char *name){(void)id;strcpy(name,"Synthetic");return 0;}
int32 SWdiminfo(int32 id,const char *n){(void)id;return !strcmp(n,"AppDim")?0:10;}
int32 GDdiminfo(int32 id,const char *n){return SWdiminfo(id,n);}
int GDgridinfo(int32 id,int32*x,int32*y,double*a,double*b){(void)id;(void)a;(void)b;*x=*y=10;return 0;}
int SW1dfldsrch(int32 a,int32 b,const char*c,const char*d,int32*e,int32*f,int32*g){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;return -1;}
int VSelts(int32 a){(void)a;return 0;}
int VSsizeof(int32 a,char*b){(void)a;(void)b;return 0;}
int VSsetfields(int32 a,const char*b){(void)a;(void)b;return 0;}
int VSseek(int32 a,int b){(void)a;(void)b;return 0;}
int VSread(int32 a,uint8*b,int c,int d){(void)a;(void)b;(void)c;(void)d;return 0;}
int VSdetach(int32 a){(void)a;return 0;}
int SWSDfldsrch(int32 a,int32 b,const char*c,int32*d,int32*e,int32*f,int32*g,int32*h,int32*i){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h;(void)i;return -1;}
int GDSDfldsrch(int32 a,int32 b,const char*c,int32*d,int32*e,int32*f,int32*g,int32*h,int32*i){return SWSDfldsrch(a,b,c,d,e,f,g,h,i);}

int32
@@FUNCTION_6@@

HDFEFieldInventoryStatus
@@FUNCTION_7@@

intn
@@FUNCTION_8@@

HDFEFieldInventoryStatus
@@FUNCTION_9@@
static char whole[12000];
static void make(int grid,const char *field,const char *first,const char *mapping,int quoted){
 snprintf(whole,sizeof(whole),"GROUP=%sStructure\n\tGROUP=%s_1\n\t\t%sName=\"Synthetic\"\n\t\tGROUP=Dimension\n\t\t\tOBJECT=Dim_1\n\t\t\t\tDimensionName=\"AppDim\"\n\t\t\t\tSize=0\n\t\t\tEND_OBJECT=Dim_1\n\t\t\tOBJECT=Dim_2\n\t\t\t\tDimensionName=\"YDim\"\n\t\t\t\tSize=10\n\t\t\tEND_OBJECT=Dim_2\n\t\tEND_GROUP=Dimension\n\t\tGROUP=DataField\n\t\t\tOBJECT=Field_1\n\t\t\t\tDataFieldName=%s%s%s\n\t\t\t\tDataType=DFNT_FLOAT32\n\t\t\t\tDimList=(\"%s\",\"YDim\")\n\t\t\tEND_OBJECT=Field_1\n\t\tEND_GROUP=DataField\n%s\tEND_GROUP=%s_1\nEND_GROUP=%sStructure\n",grid?"Grid":"Swath",grid?"GRID":"SWATH",grid?"Grid":"Swath",quoted?"\"":"",field,quoted?"\"":"",first,mapping,grid?"GRID":"SWATH",grid?"Grid":"Swath");metadata=whole;
}
static const char *empty="\t\tGROUP=MergedFields\n\t\t\tOBJECT=Merged_1\n\t\t\t\tMergedFieldName=\"MRGFLD_test\"\n\t\t\t\tFieldList=\n\t\t\tEND_OBJECT=Merged_1\n\t\tEND_GROUP=MergedFields\n";
static const char *mapped="\t\tGROUP=MergedFields\n\t\t\tOBJECT=Merged_1\n\t\t\t\tMergedFieldName=\"MRGFLD_test\"\n\t\t\t\tFieldList=\"Temperature\"\n\t\t\tEND_OBJECT=Merged_1\n\t\tEND_GROUP=MergedFields\n";
int main(void){
 int32 ids[2]={1,0};char *p[2];char *b;char value[512];
 for(int grid=0;grid<2;grid++)for(int quoted=0;quoted<2;quoted++){
  make(grid,"Temperature","AppDim",empty,quoted);
  assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_UNAVAILABLE);
  fail_read=1;assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);fail_read=0;
  fail_sds=1;assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);fail_sds=0;
  nonmerged=1;assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_RETAIN);nonmerged=0;
  b=EHmetagroup(0,"Synthetic",grid?"g":"s","DataField",p);assert(b);assert(EHfindfield(p,"DataFieldName","Temp")==0);assert(EHfindfield(p,"DataFieldName","Temperature")==1);assert(EHfieldvalue(p,"DataType",value,sizeof(value))==0&&!strcmp(value,"DFNT_FLOAT32"));free(b);
  make(grid,"Temperature","AppDim",mapped,quoted);assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_RETAIN);
  make(grid,"Temperature","AppDim","",quoted);assert(EHfieldinventory(0,"Synthetic",grid?"g":"s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);
 }
 /* Grid implicit dimensions are valid without explicit Dimension entries. */
 make(1,"fld_01__","XDim","",0);assert(EHfieldinventory(0,"Synthetic","g","DataField","DataFieldName","fld_01__",2,ids)==HDFE_FIELD_RETAIN);
 /* CRLF and split attribute storage are checked through actual pa4 helper. */
 make(0,"Temperature","AppDim",empty,1);char crlf[24000];size_t j=0;for(size_t i=0;whole[i];i++){if(whole[i]=='\n')crlf[j++]='\r';crlf[j++]=whole[i];}crlf[j]=0;metadata=crlf;assert(EHfieldinventory(0,"Synthetic","s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_UNAVAILABLE);
 make(0,"Temperature","AppDim",empty,1);char part0[12000],part1[12000];size_t half=strlen(whole)/2;memcpy(part0,whole,half);part0[half]=0;strcpy(part1,whole+half);metadata=part0;extra_metadata=part1;assert(EHfieldinventory(0,"Synthetic","s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_UNAVAILABLE);extra_metadata=NULL;
 /* Old ODL exact OBJECT name and nonmatching adjacent names. */
 char old[]="\t\tOBJECT=\"A long name\"\r\n\t\t\tDataType=DFNT_FLOAT32\r\n\t\tEND_OBJECT=\"A long name\"\r\n";p[0]=old;p[1]=old+strlen(old);assert(EHfindfield(p,"DataFieldName","A long name")==1);assert(EHfieldvalue(p,"DataType",value,sizeof(value))==0&&!strcmp(value,"DFNT_FLOAT32"));
 char bad[]="OBJECT=X\nDataFieldName=Temperature\nEND_OBJECT=Y\n";p[0]=bad;p[1]=bad+strlen(bad);assert(EHfindfield(p,"DataFieldName","Temperature")==-1);
 char duplicate[]="OBJECT=X\nDataFieldName=A\nEND_OBJECT=X\nOBJECT=Y\nDataFieldName=A\nEND_OBJECT=Y\n";p[0]=duplicate;p[1]=duplicate+strlen(duplicate);assert(EHfindfield(p,"DataFieldName","A")==-1);
 char cap[]="Key=abc\n";p[0]=cap;p[1]=cap+strlen(cap);assert(EHfieldvalue(p,"Key",value,4)==0);assert(EHfieldvalue(p,"Key",value,3)==-1);
 /* A valid empty field collection is different from an invalid requested field. */
 metadata="GROUP=SwathStructure\n\tGROUP=S\n\t\tSwathName=\"Synthetic\"\n\t\tGROUP=DataField\n\t\tEND_GROUP=DataField\n\tEND_GROUP=S\nEND_GROUP=SwathStructure\n";b=EHmetagroup(0,"Synthetic","s","DataField",p);assert(b);assert(EHfindfield(p,"DataFieldName","Temperature")==0);free(b);assert(EHfieldinventory(0,"Synthetic","s","DataField","DataFieldName","Temperature",2,ids)==HDFE_FIELD_ERROR);
 
 int32 rank, dims[32]={0}, nt;char dimnames[512];
 make(1,"fld_01__","XDim","",0);assert(GDfieldinfo(GDIDOFFSET,"fld_01__",&rank,dims,&nt,dimnames)==0);assert(rank==2&&nt==5&&dims[0]==10&&dims[1]==10&&!strcmp(dimnames,"XDim,YDim"));assert(GDfieldinfo(GDIDOFFSET,"fld_01",&rank,dims,&nt,dimnames)==-1);
 make(0,"Temperature","AppDim",empty,1);assert(SWfinfo(SWIDOFFSET,"Data Fields","Temperature",&rank,dims,&nt,dimnames)==-1);
 make(1,"Temperature","AppDim",empty,1);assert(GDfieldinfo(GDIDOFFSET,"Temperature",&rank,dims,&nt,dimnames)==-1);
 puts("PA5_FIELD_INVENTORY_CONTRACT_OK");return 0;
}
''',
    'consumer-contract.cpp': r'''
#include <cassert>
#include <algorithm>
#include <memory>
#include <string>
#include <vector>
#include <cstring>
#include <cstdio>
#include <cstdarg>
using int32=int;using CSLConstList=const char*const*;
#define CE_Failure 3
#define CE_Warning 2
#define CPLE_AppDefined 1
#define HDFE_NENTDIM 0
#define HDFE_NENTDFLD 4
#define H4_MAX_VAR_DIMS 32
#define HDFE_DIMBUFSIZE 256
#define CSLT_HONOURSTRINGS 1
#define CPLAssert(x) assert(x)
#define CPLMutexHolderD(x) ((void)(x))
int hHDF4Mutex,errorType=0,mode=0,fieldFail=0;
enum HDFEFieldInventoryStatus {HDFE_FIELD_ERROR=-1,HDFE_FIELD_UNAVAILABLE=0,HDFE_FIELD_RETAIN=1};
void CPLError(int severity,int,const char*,...){errorType=severity;}
int SWnentries(int,int entry,int *size){if(entry==0){*size=11;return 2;}if(mode==6){*size=0;return 0;}*size=3;return mode==3?-1:2;}
int GDnentries(int id,int e,int*s){return SWnentries(id,e,s);}
int SWinqdatafields(int,char *names,int*r,int*t){strcpy(names,"A,B");r[0]=r[1]=2;t[0]=t[1]=5;return mode==4?1:2;}
int SWinqgeofields(int i,char*n,int*r,int*t){return SWinqdatafields(i,n,r,t);}
int GDinqfields(int i,char*n,int*r,int*t){return SWinqdatafields(i,n,r,t);}
HDFEFieldInventoryStatus SWfieldinventory(int,int,const char*n){if(mode==5)return static_cast<HDFEFieldInventoryStatus>(9);if(mode==1&&!strcmp(n,"A"))return HDFE_FIELD_UNAVAILABLE;if(mode==2&&!strcmp(n,"B"))return HDFE_FIELD_ERROR;return HDFE_FIELD_RETAIN;}
HDFEFieldInventoryStatus GDfieldinventory(int i,const char*n){return SWfieldinventory(i,4,n);}
int SWfieldinfo(int,const char*,int*r,int*d,int*t,char*n){if(fieldFail)return -1;*r=2;d[0]=d[1]=10;*t=5;strcpy(n,"XDim,YDim");return 0;}
int GDfieldinfo(int i,const char*n,int*r,int*d,int*t,char*b){return SWfieldinfo(i,n,r,d,t,b);}
static char* tokens[]={const_cast<char*>("A"),const_cast<char*>("B"),nullptr};
char **CSLTokenizeString2(const char*,const char*,int){return tokens;}
class CPLStringList {std::vector<std::string>v; public:CPLStringList(char**p){for(;*p;p++)v.emplace_back(*p);}int size()const{return (int)v.size();}const char*operator[](int i)const{return v[i].c_str();}};
class GDALDimension{};class GDALMDArray{};struct Handle{int m_handle=1;};
class HDF4SwathArray {public:template<class...T>static std::shared_ptr<GDALMDArray>Create(T...){return std::make_shared<GDALMDArray>();}};
class HDF4EOSGridArray {public:template<class...T>static std::shared_ptr<GDALMDArray>Create(T...){return std::make_shared<GDALMDArray>();}};
class HDF4SwathSubGroup{public:std::shared_ptr<Handle>m_poSwathHandle=std::make_shared<Handle>();int m_entryType=4;std::shared_ptr<void>m_poShared;std::vector<std::shared_ptr<GDALDimension>>m_groupDims;std::string GetFullName()const{return "/synthetic";}std::vector<std::string>GetMDArrayNames(CSLConstList=nullptr)const;std::shared_ptr<GDALMDArray>OpenMDArray(const std::string&,CSLConstList=nullptr)const;};
class HDF4EOSGridSubGroup{public:std::shared_ptr<Handle>m_poGDHandle=std::make_shared<Handle>();int m_entryType=4;std::shared_ptr<void>m_poShared;std::vector<std::shared_ptr<GDALDimension>>m_groupDims;std::string GetFullName()const{return "/synthetic";}std::vector<std::string>GetMDArrayNames(CSLConstList=nullptr)const;std::shared_ptr<GDALMDArray>OpenMDArray(const std::string&,CSLConstList=nullptr)const;};

std::vector<std::string>
@@FUNCTION_0@@

std::vector<std::string>
@@FUNCTION_1@@

std::shared_ptr<GDALMDArray>
@@FUNCTION_2@@

std::shared_ptr<GDALMDArray>
@@FUNCTION_3@@

template<class G>void check(){G group;mode=0;errorType=0;auto names=group.GetMDArrayNames();assert(names.size()==2&&errorType==0);mode=1;errorType=0;names=group.GetMDArrayNames();assert(names.size()==1&&names[0]=="B"&&errorType==CE_Warning);mode=2;errorType=0;names=group.GetMDArrayNames();assert(names.empty()&&errorType==CE_Failure);mode=3;errorType=0;names=group.GetMDArrayNames();assert(names.empty()&&errorType==CE_Failure);mode=4;errorType=0;names=group.GetMDArrayNames();assert(names.empty()&&errorType==CE_Failure);mode=5;errorType=0;names=group.GetMDArrayNames();assert(names.empty()&&errorType==CE_Failure);mode=6;errorType=0;names=group.GetMDArrayNames();assert(names.empty()&&errorType==0);mode=0;fieldFail=1;errorType=0;auto array=group.OpenMDArray("unavailable");assert(!array&&errorType==CE_Failure);fieldFail=0;errorType=0;array=group.OpenMDArray("valid");assert(array&&errorType==0);}
int main(){check<HDF4SwathSubGroup>();check<HDF4EOSGridSubGroup>();puts("PA5_CONSUMER_AND_EXPLICIT_ARRAY_CONTRACT_OK");}
''',
}

def emit(source, output):
    if output.exists(): raise ValueError('Refusing to overwrite QA evidence')
    output.mkdir(parents=True)
    for filename, functions in FUNCTIONS.items():
        unit = TEMPLATES[filename]
        for index, (relative, name) in enumerate(functions):
            text = (source / relative).read_text()
            start = text.index(name) if '::' in name else re.search('^'+re.escape(name)+r'\(', text, re.M).start()
            body = text[start:text.index('\n}',text.index('{',start))+2]
            unit = unit.replace('@@FUNCTION_'+str(index)+'@@', body)
        (output / filename).write_text(unit)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--emit-only',type=Path,required=True)
    args=parser.parse_args();emit(args.source,args.emit_only)
