"""Logged, FID-preserving reorganization limited to the two authorized products."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import json,sys,time,concurrent.futures,threading,collections,requests,hashlib
from pathlib import Path
from quark_ppt_transfer import Transfer,atomic_json,now,AUTH

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'发布记录/2026-10-13_分类整理'
ROOT='/商品发布/PPT资料'

class Reorganizer(Transfer):
    def __init__(self):
        super().__init__()
        self.folder_file=OUT/'当前目录映射.json'
        self.folders=json.loads(self.folder_file.read_text()) if self.folder_file.exists() else {'/':'0','/商品发布':self.folders['/商品发布'],ROOT:self.folders[ROOT]}
        self.journal=OUT/'云端操作日志.jsonl'
        self.sessions=threading.local()
        self.logfile=OUT/'配套上传日志.jsonl'
        self.known={}
        if self.logfile.exists():
            for line in self.logfile.read_text().splitlines():
                r=json.loads(line)
                if r.get('status') in ('verified','uploaded'):self.known[r['cloud_path']]=r
    def req(self,method,endpoint,payload=None,params=None):
        if not hasattr(self,'sessions'):return super().req(method,endpoint,payload,params)
        if not hasattr(self.sessions,'session'):
            self.sessions.session=requests.Session();self.sessions.session.trust_env=False;self.sessions.session.headers.update(self.q.headers)
        with self.rate_lock:
            remain=.22-(time.monotonic()-self.last_request)
            if remain>0:time.sleep(remain)
            self.last_request=time.monotonic()
        for attempt in range(3 if method=='GET' else 1):
            try:
                response=self.sessions.session.request(method,'https://drive-pc.quark.cn/1/clouddrive'+endpoint,params={'pr':'ucpro','fr':'pc','uc_param_str':'',**(params or {})},json=payload,timeout=(12,35))
                break
            except (requests.ConnectionError,requests.Timeout):
                if method!='GET' or attempt==2:raise
                time.sleep(1+attempt)
        response.raise_for_status()
        return self.q._check_response(response.json())
    def write_op(self,endpoint,payload,description):
        with self.lock:
            with self.journal.open('a') as f:f.write(json.dumps({'at':now(),'stage':'requested','operation':description,'endpoint':endpoint,'payload':payload},ensure_ascii=False)+'\n')
        res=self.req('POST',endpoint,payload=payload)
        task=(res.get('data') or {}).get('task_id')
        if task:self.q.wait_task(task)
        with self.lock:
            with self.journal.open('a') as f:f.write(json.dumps({'at':now(),'stage':'completed','operation':description,'task_id':task},ensure_ascii=False)+'\n')
        return res
    def move(self,fids,target,desc):
        return self.write_op('/file/move',{'action_type':1,'exclude_fids':[],'filelist':fids,'to_pdir_fid':target},desc)
    def rename(self,fid,name):
        return self.write_op('/file/rename',{'fid':fid,'file_name':name},'rename '+name)
    def delete(self,fids,desc):
        return self.write_op('/file/delete',{'action_type':1,'exclude_fids':[],'filelist':fids},desc)

def roots():
    t=Reorganizer();before=json.loads((OUT/'云端整理前清单.json').read_text())
    assert before['complete']
    manifest=json.loads((BASE/'发布记录/2026-10-11_夸克首次入库/正式交付上传清单.json').read_text())['files']
    old={x['path']:x for x in before['items']}
    assert all(old[r['delivery_cloud_path']]['size']==r['bytes'] for r in manifest)
    root=t.folders[ROOT];current=t.list_files(root)
    wrapper=next((x for x in current if x['file_name']=='01_正式交付'),None)
    for code,name,oldname in [('CS','创新创业','创新创业PPT资料合集'),('ZG','大学生职业规划','大学生职业规划PPT资料合集')]:
        fid=old[ROOT+'/01_正式交付/'+oldname]['fid']
        current=t.list_files(root)
        if fid not in {x['fid'] for x in current}:
            assert wrapper and fid in {x['fid'] for x in t.list_files(wrapper['fid'])}
            assert not any(x['file_name']==name for x in current)
            t.move([fid],root,'promote '+name)
        obj=next(x for x in t.list_files(root) if x['fid']==fid)
        if obj['file_name']!=name:t.rename(fid,name)
        t.folders[ROOT+'/'+name]=fid;atomic_json(t.folder_file,t.folders)
        print('Promoted',name,flush=True)
    if wrapper:
        assert not t.list_files(wrapper['fid']), 'Wrapper not empty; refuse deletion'
        t.delete([wrapper['fid']],'delete verified empty delivery wrapper')
    backup=next((x for x in t.list_files(root) if x['file_name']=='00_源库备份'),None)
    if backup:
        archive=json.loads((BASE/'发布记录/2026-10-11_夸克首次入库/本地上传清单.json').read_text())
        items=archive['items']
        assert all(Path(x['source_path']).exists() and Path(x['source_path']).stat().st_size==x['bytes'] for x in items),'Original source missing'
        assert backup['fid'] not in [t.folders[ROOT+'/创新创业'],t.folders[ROOT+'/大学生职业规划']]
        t.delete([backup['fid']],'delete user-authorized cloud source backup; local originals verified')
    after=t.list_files(root);assert {x['file_name'] for x in after}=={'创新创业','大学生职业规划'}
    atomic_json(OUT/'顶层整理结果.json',{'at':now(),'items':[{'name':x['file_name'],'fid':x['fid']} for x in after],'local_originals_preserved':True})
    print('ROOT COMPLETE',flush=True)

def scan(t,fid,path):
    result=[];pending=[(fid,path)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        while pending:
            batch=pending;pending=[]
            for (parent,path),items in zip(batch,pool.map(lambda x:t.list_files(x[0]),batch)):
                for x in items:
                    r={k:x.get(k) for k in ['fid','file_name','dir','size']};r.update(parent_fid=parent,path=path+'/'+x['file_name']);result.append(r)
                    if x.get('dir'):pending.append((x['fid'],r['path']))
    return result

def apply_plan():
    t=Reorganizer();plan=json.loads((OUT/'创新创业整理计划.json').read_text());rootpath=ROOT+'/创新创业';root=t.folders[rootpath]
    current=scan(t,root,rootpath);byid={x['fid']:x for x in current}
    assert all(x['fid'] in byid and byid[x['fid']]['size']==x['bytes'] for x in plan),'Missing or changed PPT before mutation'
    for x in current:
        if x['dir']:t.folders[x['path']]=x['fid']
    atomic_json(t.folder_file,t.folders)
    # Rename each unique object in place, then move batches. Every mutation is recoverable by FID journal.
    changed=[x for x in plan if byid[x['fid']]['file_name']!=x['name']]
    def rename_one(x):
        same_parent=[y for y in current if y['parent_fid']==byid[x['fid']]['parent_fid'] and y['file_name']==x['name'] and y['fid']!=x['fid']]
        if same_parent:raise RuntimeError('Name collision before move: '+x['name'])
        t.rename(x['fid'],x['name']);return x['fid']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i,fid in enumerate(pool.map(rename_one,changed),1):
            if i%30==0:print('RENAMED',i,'/',len(changed),flush=True)
    groups=collections.defaultdict(list)
    for x in plan:groups[x['folder']].append(x)
    for folder,items in groups.items():
        if all(byid[x['fid']]['path']==x['target_path'] and byid[x['fid']]['file_name']==x['name'] for x in items):continue
        target=t.folder(folder);live={x['fid']:x for x in t.list_files(target)}
        pending=[x['fid'] for x in items if x['fid'] not in live]
        for start in range(0,len(pending),50):t.move(pending[start:start+50],target,'classify '+folder)
        actual={x['fid']:x for x in t.list_files(target)}
        assert all(x['fid'] in actual and actual[x['fid']]['file_name']==x['name'] and actual[x['fid']]['size']==x['bytes'] for x in items),folder
        print('CLASSIFIED',folder,len(items),flush=True)
    after=scan(t,root,rootpath);byid={x['fid']:x for x in after}
    assert all(byid[x['fid']]['path']==x['target_path'] and byid[x['fid']]['size']==x['bytes'] for x in plan)
    atomic_json(OUT/'分类移动核验.json',{'at':now(),'complete':True,'ppt_count':len(plan),'items':after})
    print('ALL PPT VERIFIED',len(plan),flush=True)

def finish():
    t=Reorganizer();plan=json.loads((OUT/'创新创业整理计划.json').read_text());rootpath=ROOT+'/创新创业';root=t.folders[rootpath]
    before=json.loads((OUT/'云端整理前清单.json').read_text())['items']
    oldroot=ROOT+'/01_正式交付/创新创业PPT资料合集'
    support=[x for x in before if not x['dir'] and str(Path(x['path']).parent)==oldroot]
    current=scan(t,root,rootpath);byid={x['fid']:x for x in current}
    assert all(x['fid'] in byid and byid[x['fid']]['path']==x['target_path'] and byid[x['fid']]['size']==x['bytes'] for x in plan)
    out=OUT/'买家说明';out.mkdir(exist_ok=True)
    counts=collections.Counter(x['category'] for x in plan);selected=sum(x['selected'] for x in plan)
    note='''创新创业PPT资料选用说明
更新日期：2026年10月13日

一、怎么找资料
先打开与你项目有关的行业：教育、医疗健康、科技、农业、生态环保、文化文旅、商业服务、社会治理。
各行业优先查看“01_精选PPT”；其余按“02_参考模板”“03_参考案例”“04_单页素材”区分，没有对应文件的空目录不保留。
“通用模板”保存没有明确行业内容、可跨行业使用的版式模板；“99_备赛资料”集中保存比赛指南与填写参考。

二、筛选含义
精选PPT来自本次封面与内页抽样筛选，侧重视觉统一、排版层次与图文组织。精选中也包含需要填写的主题模板。
参考模板供借鉴版式；参考案例供借鉴项目结构或内容，不能直接把其中的项目、数据和获奖内容作为自己的材料。
本次只分类、重命名，没有修改任何PPT的文字、图片、布局或原始文件格式。
选用前请在自己的PowerPoint中确认字体显示、替换占位文字和示例数据。抽样筛选不代表逐页完稿验收。

三、名称规则
采用“项目名称_主题或用途_页数”，同主题的不同版本使用颜色或版本号区分。页数按文件结构读取，可能包括隐藏页。
完整路径见“01_分类目录.txt”。“重点样例逐页填写参考”保留已有的内容说明，其旧文件名可按项目名称在新目录中查找。
'''
    note+=f'\n四、资料数量\n演示文件共{len(plan)}份，其中精选{selected}份，其余为参考模板、参考案例或比赛指南等。\n'
    note+='\n'.join(f'{k}：{v}份' for k,v in counts.items())+'\n'
    (out/'00_阅读说明.txt').write_text(note)
    index='创新创业分类目录\n更新日期：2026年10月13日\n共694份演示文件，原PPT内容未修改。\n\n'
    for x in sorted(plan,key=lambda x:x['target_path']):index+=x['target_path'].removeprefix(rootpath+'/')+'\n'
    (out/'01_分类目录.txt').write_text(index)
    for p in sorted(out.glob('*.txt')):
        b=p.read_bytes();row={'source_path':str(p),'bytes':len(b),'mtime_ns':p.stat().st_mtime_ns,'md5':hashlib.md5(b).hexdigest(),'sha1':hashlib.sha1(b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest()}
        result=t.upload(row,rootpath+'/'+p.name,phase='curation_support');print('SUPPORT UPLOADED',p.name,flush=True)
    sample=next(x for x in support if x['file_name'].startswith('02_'))
    target=t.folder(rootpath+'/99_备赛资料/填写参考')
    if byid[sample['fid']]['file_name']!='重点样例逐页填写参考.txt':t.rename(sample['fid'],'重点样例逐页填写参考.txt')
    if byid[sample['fid']]['parent_fid']!=target:t.move([sample['fid']],target,'relocate existing sample instructions')
    stale=[x['fid'] for x in support if x['fid']!=sample['fid'] and x['fid'] in byid]
    if stale:t.delete(stale,'remove superseded usage guide and obsolete path index after replacement upload')
    # Re-list every directory before removing only empty folders, deepest first.
    for x in sorted([x for x in current if x['dir']],key=lambda x:x['path'].count('/'),reverse=True):
        if not t.list_files(x['fid']):
            t.delete([x['fid']],'remove verified empty folder '+x['path'])
            t.folders.pop(x['path'],None)
    atomic_json(t.folder_file,t.folders)
    after=scan(t,root,rootpath);byid={x['fid']:x for x in after};files=[x for x in after if not x['dir']]
    assert len(files)==697
    assert all(byid[x['fid']]['path']==x['target_path'] and byid[x['fid']]['size']==x['bytes'] for x in plan)
    assert not any(x['file_name'] in ('综合主题待核','备赛指南','00_源库备份','01_正式交付') for x in after)
    atomic_json(OUT/'创新创业最终核验.json',{'at':now(),'complete':True,'ppt_count':694,'selected_count':selected,'support_count':3,'all_ppt_fids_and_sizes_preserved':True,'items':after})
    zgpath=ROOT+'/大学生职业规划';zg=scan(t,t.folders[zgpath],zgpath)
    beforezg={x['fid']:x for x in before if x['path'].startswith(ROOT+'/01_正式交付/大学生职业规划PPT资料合集/') and not x['dir']}
    afterzg={x['fid']:x for x in zg if not x['dir']}
    assert set(beforezg)==set(afterzg) and len(afterzg)==787
    assert all(x['file_name']==afterzg[fid]['file_name'] and x['size']==afterzg[fid]['size'] for fid,x in beforezg.items())
    assert {x['file_name'] for x in t.list_files(t.folders[ROOT])}=={'创新创业','大学生职业规划'}
    atomic_json(OUT/'大学生职业规划原样保留核验.json',{'at':now(),'complete':True,'files':len(afterzg),'same_fids_names_sizes':True})
    print('FINAL FILE VERIFICATION COMPLETE',len(files),len(afterzg),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='roots':roots()
    elif sys.argv[1]=='apply':apply_plan()
    elif sys.argv[1]=='finish':finish()
