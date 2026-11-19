"""Emit source-derived standalone regression/syntax units; never compile or run.

The existing pa3 emitter remains immutable. Native acceptance requires the future
pa4 image and the separate fixture/consumer gates; I/O doubles do not replace it.
"""
import argparse
import importlib.util
from pathlib import Path
import sys
sys.dont_write_bytecode=True

def fn(text,name):
    import re
    start=re.search(r'^'+name+r'\(',text,re.M).start()
    return text[start:text.index('\n}',text.index('{',start))+2]

def method(text,name):
    start=text.index(name)
    return text[start:text.index('\n}',text.index('{',start))+2]

EXTRA = r'''
void HEreport(const char *format,...){(void)format;errors++;}
#define EH_METAGROUP_ERROR (-1)
#define EH_METAGROUP_ABSENT 0
#define EH_METAGROUP_PRESENT 1
#define HDFE_NENTDIM 0
#define HDFE_NENTMAP 1
#define HDFE_NENTIMAP 2
#define HDFE_NENTGFLD 3
#define HDFE_NENTDFLD 4
#define GDIDOFFSET 4194304
#define NGRID 200
#define H4_MAX_VAR_DIMS 32
struct grid {int32 IDTable;} GDXGrid[NGRID];
char *EHmetagroupstatus(int32,const char*,const char*,const char*,char*[],intn*);
int32 SWchkswid(int32 id,const char*n,int32*f,int32*s,int32*v){(void)id;(void)n;*f=*s=*v=0;return 0;}
int32 GDchkgdid(int32 id,const char*n,int32*f,int32*s,int32*v){return SWchkswid(id,n,f,s,v);}
int32 EHnumstr(const char *v){return !strcmp(v,"DFNT_FLOAT32")?5:-1;}
int32 EHparsestr(const char *s,char sep,char **ptr,int32 *len){(void)s;(void)sep;(void)ptr;(void)len;return 0;}
#define REMQUOTE(x) do {size_t z=strlen(x);if(z>=2 && (x)[0]=='"' && (x)[z-1]=='"'){memmove(x,(x)+1,z-2);(x)[z-2]=0;}}while(0)
'''
CASES = r'''
static void check_optional_contract(void){
 char *p[2]={0};intn state=123;int32 count=-7;char names[64]="sentinel";
 metadata="GROUP=SwathStructure\n\tGROUP=SWATH_1\n\t\tSwathName=\"SyntheticSwath\"\n\tEND_GROUP=SWATH_1\nEND_GROUP=SwathStructure\n";
 char *b=EHmetagroupstatus(0,"SyntheticSwath","s","DataField",p,&state);
 assert(!b && !p[0] && !p[1] && state==EH_METAGROUP_ABSENT);
 assert(SWnentries(SWIDOFFSET,HDFE_NENTDFLD,&count)==0 && count==0);
 assert(SWinqfields(SWIDOFFSET,"Data Fields",names,NULL,NULL)==0 && names[0]==0);
 assert(EHmetagroup(0,"SyntheticSwath","s","MergedFields",p)==NULL);
 fail_read=1;b=EHmetagroupstatus(0,"SyntheticSwath","s","DataField",p,&state);
 assert(!b && state==EH_METAGROUP_ERROR);assert(SWnentries(SWIDOFFSET,HDFE_NENTDFLD,&count)==-1);fail_read=0;
 metadata="GROUP=GridStructure\n\tGROUP=GRID_1\n\t\tGridName=\"SyntheticSwath\"\n\t\tGROUP=DataField\n\t\tEND_GROUP=DataField\n\tEND_GROUP=GRID_1\nEND_GROUP=GridStructure\n";
 b=EHmetagroupstatus(0,"SyntheticSwath","g","DataField",p,&state);assert(b && state==EH_METAGROUP_PRESENT);free(b);
 assert(GDnentries(GDIDOFFSET,HDFE_NENTDFLD,&count)==0 && count==0);
 metadata="GROUP=PointStructure\n\tGROUP=POINT_1\n\t\tPointName=\"SyntheticSwath\"\n\tEND_GROUP=POINT_1\nEND_GROUP=PointStructure\n";
 b=EHmetagroupstatus(0,"SyntheticSwath","p","DataField",p,&state);assert(!b && state==EH_METAGROUP_ABSENT);
}
'''
CPP_PREFIX = r'''
#include <algorithm>
#include <memory>
#include <string>
#include <vector>
#include <set>
#include <stdexcept>
#include <cstdint>
#include <cstring>
using int32=int;using CSLConstList=const char*const*;
#define CE_Failure 3
#define CPLE_AppDefined 1
#define HDFE_NENTDIM 0
#define HDFE_NENTDFLD 4
#define H4_MAX_VAR_DIMS 32
#define HDFE_DIMBUFSIZE 256
#define CSLT_HONOURSTRINGS 1
#define CPLAssert(x) ((void)(x))
#define CPLMutexHolderD(x) ((void)(x))
extern int hHDF4Mutex;extern void CPLError(int,int,const char*,...);
extern unsigned CPLGetErrorCounter();extern int CPLGetLastErrorType();extern const char*CPLGetLastErrorMsg();
extern int32 SWnentries(int32,int32,int32*);extern int32 GDnentries(int32,int32,int32*);
extern int32 SWinqdatafields(int32,char*,int32*,int32*);extern int32 SWinqgeofields(int32,char*,int32*,int32*);extern int32 GDinqfields(int32,char*,int32*,int32*);
extern int32 SWinqdims(int32,char*,int32*);extern int32 SWfieldinfo(int32,const char*,int32*,int32*,int32*,char*);extern int32 GDfieldinfo(int32,const char*,int32*,int32*,int32*,char*);
extern char**CSLTokenizeString2(const char*,const char*,int);
class CPLStringList{public:CPLStringList()=default;CPLStringList(char**);int size()const;const char*operator[](int)const;void SetNameValue(const char*,const char*);CSLConstList List()const;};
class GDALDimension{public:GDALDimension(std::string,std::string,std::string,std::string,int);};
class GDALAttribute{};
class GDALMDArray{public:std::string GetName()const;};
struct Handle{int m_handle;};
class HDF4SwathArray{public:template<class...T>static std::shared_ptr<GDALMDArray>Create(T...);};
class HDF4EOSGridArray{public:template<class...T>static std::shared_ptr<GDALMDArray>Create(T...);};
class HDF4SwathSubGroup{public:std::shared_ptr<Handle>m_poSwathHandle;int m_entryType;std::shared_ptr<void>m_poShared;std::vector<std::shared_ptr<GDALDimension>>m_groupDims;std::string GetFullName()const;std::vector<std::string>GetMDArrayNames(CSLConstList)const;std::shared_ptr<GDALMDArray>OpenMDArray(const std::string&,CSLConstList)const;};
class HDF4EOSGridSubGroup{public:std::shared_ptr<Handle>m_poGDHandle;int m_entryType;std::shared_ptr<void>m_poShared;std::vector<std::shared_ptr<GDALDimension>>m_groupDims;std::string GetFullName()const;std::vector<std::string>GetMDArrayNames(CSLConstList)const;std::shared_ptr<GDALMDArray>OpenMDArray(const std::string&,CSLConstList)const;};
class HDF4SwathGroup{public:std::shared_ptr<Handle>m_poSwathHandle;mutable std::vector<std::shared_ptr<GDALDimension>>m_dims;std::string GetFullName()const;std::vector<std::shared_ptr<GDALDimension>>GetDimensions(CSLConstList=nullptr)const;};
struct Context{~Context();};class CPLJSonStreamingWriter{public:Context MakeObjectContext();Context MakeArrayContext();void AddObjKey(const char*);void AddObjKey(const std::string&);template<class T>void Add(T);};
class GDALGroup{public:std::string GetName()const;std::string GetFullName()const;std::vector<std::shared_ptr<GDALAttribute>>GetAttributes(CSLConstList)const;std::vector<std::shared_ptr<GDALDimension>>GetDimensions()const;std::vector<std::string>GetMDArrayNames(CSLConstList)const;CSLConstList GetStructuralInfo()const;std::vector<std::string>GetGroupNames()const;std::shared_ptr<GDALGroup>OpenGroup(const std::string&)const;std::shared_ptr<GDALMDArray>OpenMDArray(const std::string&)const;};
struct GDALMultiDimInfoOptions{bool bDetailed;CPLStringList aosArrayOptions;};
template<class...T>void DumpAttrs(T&&...);template<class...T>void DumpDimensions(T&&...);template<class...T>void DumpStructuralInfo(T&&...);template<class...T>void DumpArray(T&&...);template<class...T>bool HasUniqueNames(T&&...);
'''

def emit(source,output,parent_path):
    if output.exists():raise ValueError('Refusing to overwrite existing QA output')
    output.mkdir()
    loader=importlib.util.spec_from_file_location('pa3_emitter',parent_path)
    parent=importlib.util.module_from_spec(loader);loader.loader.exec_module(parent)
    eos=source/'frmts/hdf4/hdf-eos';eh=(eos/'EHapi.c').read_text();sw=(eos/'SWapi.c').read_text();gd=(eos/'GDapi.c').read_text()
    code=parent.PREFIX+EXTRA
    for name,typ in [('EHgetmetavalue','intn'),('EHmetagroupstatus','char *'),('EHmetagroup','char *')]:code+='\n'+typ+'\n'+fn(eh,name)+'\n'
    code+='\nintn\n'+fn(sw,'SWSDfldsrch')+'\n'
    for name in ['SWdiminfo','SWinqdims','SWinqmaps','SWinqidxmaps','SWinqfields','SWnentries']:code+='\nint32\n'+fn(sw,name)+'\n'
    for name in ['GDinqfields','GDnentries']:code+='\nint32\n'+fn(gd,name)+'\n'
    old_cases=parent.CASES.replace('int main(void) {','int parent_cases(void) {')
    code+=old_cases+CASES+'\nint main(void){parent_cases();check_optional_contract();puts("PA4_ENUMERATION_CONTRACT_OK");return 0;}\n'
    (output/'metadata-contract.c').write_text(code)
    md=(source/'frmts/hdf4/hdf4multidim.cpp').read_text();cpp=CPP_PREFIX
    for name,typ in [('HDF4SwathSubGroup::GetMDArrayNames','std::vector<std::string>'),('HDF4SwathSubGroup::OpenMDArray','std::shared_ptr<GDALMDArray>'),('HDF4SwathGroup::GetDimensions','std::vector<std::shared_ptr<GDALDimension>>'),('HDF4EOSGridSubGroup::GetMDArrayNames','std::vector<std::string>'),('HDF4EOSGridSubGroup::OpenMDArray','std::shared_ptr<GDALMDArray>')]:cpp+='\n'+typ+'\n'+method(md,name)+'\n'
    app=(source/'apps/gdalmdiminfo_lib.cpp').read_text()
    for name in ['DumpArrays','DumpGroup']:
        # Skip forward declarations by taking the column-zero definition followed by '{'.
        import re
        found=[m for m in re.finditer(r'^static void '+name+r'\([^;]+?\)\n\{',app,re.M)]
        start=found[0].start();end=app.index('\n}',app.index('{',start))+2;cpp+='\n'+app[start:end]+'\n'
    (output/'multidim-syntax.cpp').write_text(cpp)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--emit-only',type=Path,required=True)
    parser.add_argument('--parent-emitter',type=Path,default=Path(__file__).with_name('gdal36_pa3_metadata_contract.py'))
    args=parser.parse_args();emit(args.source,args.emit_only,args.parent_emitter)
