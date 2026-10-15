"""Read-only live inventory and content dossier for the authorized PPT reorganization."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")
import os

import concurrent.futures, json, sys, zipfile, re
from pathlib import Path
from xml.etree import ElementTree as ET
from quark_ppt_transfer import Transfer, atomic_json, now

BASE = Path(__file__).resolve().parents[1]
OUT = BASE/'发布记录/2026-10-13_分类整理'
OUT.mkdir(parents=True, exist_ok=True)

def inventory():
    t = Transfer()
    root = '/商品发布/PPT资料'
    pending = [(root,t.folders[root])]
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        while pending:
            batch = pending; pending=[]
            for (parent,pfid), rows in zip(batch,pool.map(lambda v:t.list_files(v[1]),batch)):
                for x in rows:
                    row = {k:x.get(k) for k in ['fid','file_name','dir','size','md5','sha1']}
                    row.update(path=parent+'/'+x['file_name'],parent_fid=pfid)
                    found.append(row)
                    if x.get('dir') and x['file_name']!='00_源库备份':pending.append((row['path'],row['fid']))
            atomic_json(OUT/'云端整理前清单.json',{'at':now(),'root_fid':t.folders[root],'items':found,'complete':not pending})
            print('Inventoried',len(found),'pending folders',len(pending),flush=True)

def dossiers():
    rows=json.loads((BASE/'发布记录/2026-10-11_夸克首次入库/正式交付上传清单.json').read_text())['files']
    ix=Path(os.environ.get('XIANYU_LEGACY_PATH_INVENTORY_QUARK_REORGANIZATION_1', '/path/to/configure'))
    legacy={x['source_sha256']:x for x in map(json.loads,(ix/'LEGACY-STYLE-CATALOG.jsonl').read_text().splitlines())}
    out=[]
    for r in rows:
        if r['product']!='CS' or Path(r['source_path']).suffix.lower() not in ('.ppt','.pptx','.pptm','.ppsx'):continue
        p=ix/'逐份结构'/f"{r['sha256']}.json"
        d=json.loads(p.read_text()) if p.exists() else {}
        slides=[{'n':s['order'],'title':s.get('title',''),'text':' / '.join(s.get('content_sequence',[]))[:2000]} for s in d.get('slides',[])]
        if not slides and r['sha256'] in legacy:
            l=legacy[r['sha256']]
            obs=Path(os.environ.get('XIANYU_LEGACY_PATH_INVENTORY_QUARK_REORGANIZATION_2', '/path/to/configure'))/l['converted_observation_path']
            if obs.exists():
                with zipfile.ZipFile(obs) as z:
                    names=sorted([s for s in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+.xml',s)],key=lambda x:int(re.search(r'slide(\d+)',x).group(1)))
                    for i,n in enumerate(names,1):
                        ts=[v.text for v in ET.fromstring(z.read(n)).iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t') if v.text]
                        slides.append({'n':i,'title':next((s.get('title','') for s in l['pages'] if s['slide']==i),''),'text':' / '.join(ts)[:2000]})
        out.append({'id':r['sha256'][:12],'sha256':r['sha256'],'source_path':r['source_path'],'old_path':r['delivery_cloud_path'],'old_name':r['delivery_name'],'section':r.get('section'),'subsection':r.get('subsection'),'type':r.get('catalog_type'),'slide_count':len(slides) or r.get('slide_count'),'slides':slides})
    atomic_json(OUT/'创新创业内容盘点.json',out)
    for tag,subset in [('ooxml',[x for x in out if Path(x['source_path']).suffix.lower()!='.ppt']),('legacy',[x for x in out if Path(x['source_path']).suffix.lower()=='.ppt'])]:
        atomic_json(OUT/f'{tag}_dossier.json',subset)
    print('Dossiers',len(out),'no text',sum(not x['slides'] for x in out),flush=True)

if __name__=='__main__':
    if 'dossiers' in sys.argv:dossiers()
    else:inventory()
