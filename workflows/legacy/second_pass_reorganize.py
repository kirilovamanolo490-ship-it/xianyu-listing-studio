"""Second-pass cloud structure cleanup, preserving all presentation FIDs and content."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import json,collections,concurrent.futures,hashlib,sys
from pathlib import Path
from urllib.parse import urlsplit
from reorganize_quark_ppt import Reorganizer,scan,ROOT,BASE
from quark_ppt_transfer import atomic_json,now

OUT=BASE/'发布记录/2026-10-13_二次整理'
CS=ROOT+'/创新创业';ZG=ROOT+'/大学生职业规划'
CS_GROUP='01_精选PPT与行业参考'
CS_GENERIC='02_通用PPT模板'
CS_GUIDES='03_创新创业比赛指南与填写参考'

class SecondPass(Reorganizer):
    def __init__(self):
        super().__init__()
        self.folder_file=OUT/'当前目录映射.json'
        has_current_map=self.folder_file.exists()
        if has_current_map:self.folders=json.loads(self.folder_file.read_text())
        for name in ['创新创业','大学生职业规划']:
            j=json.loads((OUT/(name+'整理前清单.json')).read_text());self.folders[ROOT+'/'+name]=j['root_fid']
            if not has_current_map:
                for x in j['items']:
                    if x['dir']:self.folders[x['path']]=x['fid']
        self.journal=OUT/'云端操作日志.jsonl';self.logfile=OUT/'配套上传日志.jsonl';self.known={}
        def direct_adapter(method,url,headers,params,payload,timeout):
            parts=urlsplit(url)
            assert parts.scheme=='https' and parts.hostname in {'drive-pc.quark.cn','drive.quark.cn'}
            assert parts.path.startswith('/1/clouddrive/')
            return self.req(method,parts.path.removeprefix('/1/clouddrive'),payload=payload,params=params)
        self.q.request_fn=direct_adapter
        if self.logfile.exists():
            for l in self.logfile.read_text().splitlines():
                x=json.loads(l)
                if x.get('status') in ('verified','uploaded'):self.known[x['cloud_path']]=x
    def refresh_map(self,rows):
        for x in rows:
            if x['dir']:self.folders[x['path']]=x['fid']
        atomic_json(self.folder_file,self.folders)

def verify_preserved(before,after):
    a={x['fid']:x for x in before if not x['dir'] and Path(x['file_name']).suffix.lower() in ('.ppt','.pptx','.pptm','.ppsx')}
    b={x['fid']:x for x in after if not x['dir'] and Path(x['file_name']).suffix.lower() in ('.ppt','.pptx','.pptm','.ppsx')}
    assert set(a)==set(b),(len(a),len(b))
    assert all(x['size']==b[fid]['size'] for fid,x in a.items())
    return len(a)

def cs_group():
    t=SecondPass();fid=t.folders[CS];j=json.loads((OUT/'创新创业整理前清单.json').read_text());before=j['items']
    group=t.folder(CS+'/'+CS_GROUP);current=t.list_files(fid)
    industries={'教育','科技','农业','社会治理','生态环保','商业服务','文化文旅','医疗健康'}
    moving=[x['fid'] for x in current if x['file_name'] in industries and x['dir']]
    if moving:t.move(moving,group,'group eight industry folders under one browse entry')
    assert {x['file_name'] for x in t.list_files(group)}==industries
    for old,new in [('通用模板',CS_GENERIC),('99_备赛资料',CS_GUIDES)]:
        current=t.list_files(fid);obj=next((x for x in current if x['file_name']==old),None)
        if obj:t.rename(obj['fid'],new)
        else:obj=next(x for x in current if x['file_name']==new)
        t.folders[CS+'/'+new]=obj['fid']
    gen=t.folders[CS+'/'+CS_GENERIC]
    wrapper=next((x for x in t.list_files(gen) if x['dir'] and x['file_name']=='02_参考模板'),None)
    if wrapper:
        contents=t.list_files(wrapper['fid']);assert all(not x['dir'] for x in contents)
        for i in range(0,len(contents),50):t.move([x['fid'] for x in contents[i:i+50]],gen,'flatten universal template wrapper')
        assert not t.list_files(wrapper['fid']);t.delete([wrapper['fid']],'remove empty generic-template wrapper')
    after=scan(t,fid,CS);t.refresh_map(after);count=verify_preserved(before,after)
    atomic_json(OUT/'创新创业结构核验.json',{'at':now(),'complete':True,'presentation_files':count,'items':after})
    print('CS STRUCTURE COMPLETE',count,flush=True)

def apply_career():
    t=SecondPass();plan=json.loads((OUT/'职业规划整理计划.json').read_text());root=t.folders[ZG];current=scan(t,root,ZG);byid={x['fid']:x for x in current};t.refresh_map(current)
    assert len(plan)==784 and len({x['fid'] for x in plan})==784 and len({x['target_path'] for x in plan})==784
    assert all(x['fid'] in byid and byid[x['fid']]['size']==x['bytes'] for x in plan)
    # Names are globally unique within their future parent and stable across a retry.
    changed=[x for x in plan if byid[x['fid']]['file_name']!=x['name']]
    def rename_one(x):
        assert not any(y['parent_fid']==byid[x['fid']]['parent_fid'] and y['file_name']==x['name'] and y['fid']!=x['fid'] for y in current),x['name']
        t.rename(x['fid'],x['name'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i,_ in enumerate(pool.map(rename_one,changed),1):
            if i%50==0:print('ZG RENAMED',i,len(changed),flush=True)
    groups=collections.defaultdict(list)
    for x in plan:groups[x['folder']].append(x)
    for folder,items in groups.items():
        if all(byid[x['fid']]['path']==x['target_path'] for x in items):continue
        parent=t.folder(folder);actual={x['fid']:x for x in t.list_files(parent)}
        moving=[x['fid'] for x in items if x['fid'] not in actual]
        for i in range(0,len(moving),50):t.move(moving[i:i+50],parent,'career category '+folder)
        print('ZG GROUP',folder,len(items),flush=True)
    after=scan(t,root,ZG);a={x['fid']:x for x in after};assert all(a[x['fid']]['path']==x['target_path'] and a[x['fid']]['size']==x['bytes'] for x in plan)
    before=json.loads((OUT/'大学生职业规划整理前清单.json').read_text())['items'];verify_preserved(before,after)
    atomic_json(OUT/'职业规划分类移动核验.json',{'at':now(),'complete':True,'items':after})
    print('ZG PLAN VERIFIED',len(plan),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='cs':cs_group()
    elif sys.argv[1]=='career':apply_career()
