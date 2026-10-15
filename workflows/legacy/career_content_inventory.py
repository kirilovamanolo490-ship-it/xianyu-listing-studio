"""Read-only career deck content dossier and embedded cover thumbnails."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")
import os

import json,zipfile,io,re
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'发布记录/2026-10-13_二次整理';OUT.mkdir(exist_ok=True)
IX=Path(os.environ.get('XIANYU_LEGACY_PATH_CAREER_CONTENT_INVENTORY_1', '/path/to/configure'))

def main():
    source=json.loads((BASE/'发布记录/2026-10-11_夸克首次入库/正式交付上传清单.json').read_text())['files']
    taxonomy={x['sha256']:x for x in map(json.loads,(IX/'SOURCE-TAXONOMY.jsonl').read_text().splitlines())}
    manifests={x['sha256']:x for x in map(json.loads,(IX/'SOURCE-MANIFEST.jsonl').read_text().splitlines())}
    details={f.stem:f for folder in ['逐份结构','legacy-近似结构/逐份结构'] for f in (IX/folder).glob('*.json')}
    covers=OUT/'职业规划封面';covers.mkdir(exist_ok=True);rows=[]
    for r in source:
        if r['product']!='ZG' or Path(r['source_path']).suffix.lower() not in ('.ppt','.pptx','.pptm','.ppsx'):continue
        sha=r['sha256'];d=json.loads(details[sha].read_text()) if sha in details else {}
        sampled={s['slide']:s['text'] for s in manifests.get(sha,{}).get('page_samples',[])}
        slides=[{'n':s.get('order',s.get('slide',i+1)),'hidden':s.get('hidden',False),'text':(' / '.join(s.get('content_sequence',[])) or sampled.get(s.get('slide',i+1),'') or s.get('title',''))[:3000],'title':s.get('title','')} for i,s in enumerate(d.get('slides',[]))]
        if not slides:slides=[{'n':s['slide'],'text':s['text'],'title':'','hidden':False} for s in manifests.get(sha,{}).get('page_samples',[])]
        thumb=None
        if Path(r['source_path']).suffix.lower()!='.ppt':
            try:
                with zipfile.ZipFile(r['source_path']) as z:
                    n=next(n for n in z.namelist() if n.startswith('docProps/thumbnail.'))
                    im=Image.open(io.BytesIO(z.read(n))).convert('RGB');thumb=str(covers/(sha[:12]+'.jpg'));im.save(thumb)
            except Exception:pass
        rows.append({'n':len(rows)+1,'id':sha[:12],'sha256':sha,'source_path':r['source_path'],'current_path':r['delivery_cloud_path'].replace('/01_正式交付/大学生职业规划PPT资料合集','/大学生职业规划'),'current_name':r['delivery_name'],'section':r.get('section'),'subsection':r.get('subsection'),'pages':d.get('slide_count') or r.get('slide_count') or manifests.get(sha,{}).get('slide_count'),'slides':slides,'thumbnail':thumb,'taxonomy':taxonomy.get(sha,{}).get('refined_taxonomy',{})})
    (OUT/'职业规划内容盘点.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    for tag,sections in [('专业案例',{'职业规划案例','职业规划参考'}),('模板',{'职业规划模板'}),('指南访谈',{'人物访谈','备赛指南','图片化案例参考'})]:
        part=[x for x in rows if x['section'] in sections];(OUT/(tag+'_dossier.json')).write_text(json.dumps(part,ensure_ascii=False,indent=2))
    templates=[x for x in rows if x['section']=='职业规划模板']
    for start in range(0,len(templates),30):
        im=Image.new('RGB',(1500,900),'white');draw=ImageDraw.Draw(im)
        for i,x in enumerate(templates[start:start+30]):
            xx=i%5*300;yy=i//5*150
            if x['thumbnail']:
                pic=ImageOps.contain(Image.open(x['thumbnail']),(294,123));im.paste(pic,(xx,yy))
            draw.text((xx+4,yy+126),f"{x['n']}  {x['id']}",fill='black')
        im.save(covers/f'templates-{start//30+1:02}.jpg')
    print('CAREER DOSSIER',len(rows),'covers',sum(bool(x['thumbnail']) for x in rows),'detail texts',sum(bool(x['slides']) for x in rows),flush=True)

if __name__=='__main__':main()
