"""Render disposable copies for screening; never save changes to source decks."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")
import os

import json, shutil, subprocess, tempfile, time, sys,os,concurrent.futures,threading
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageOps

ROOT=Path(__file__).resolve().parents[1]/'发布记录/2026-10-13_分类整理'
OUT=ROOT/'内页筛选'; OUT.mkdir(exist_ok=True)
SOFFICE=os.environ.get('XIANYU_LEGACY_PATH_CURATE_PPT_VISUALS_1', '/path/to/configure')
NUMBERS=[1,11,20,22,26,30,31,36,37,38,42,43,44,93,159,162,165,168,170,171,172,181,187,188,190,195,222,228,229,231,233,234,235,239,242,244,246,251,255,256,257,259,260,261,262,263,271,273,281,282,284,285,286,288,290,291,296,297,298,299,300,301,303,304,308,309,310,311,313,315,319,326,327,328,331,333,334,335,337,338,339,340,342,343,344,347,348,349,350,351,355,399,400,401,403,404,405,406,408,410,412,413,414,415,416,417,418,419,420,421]

def main():
    decks=json.loads((ROOT/'ooxml_dossier.json').read_text())
    records=[]
    if (ROOT/'内页渲染记录.json').exists():records=json.loads((ROOT/'内页渲染记录.json').read_text())
    limit=int(sys.argv[1]) if len(sys.argv)>1 else len(NUMBERS)
    lock=threading.Lock();render_lock=threading.Lock()
    def render_one(num):
        d=decks[num-1]; fid=d['id']; pdf=OUT/(fid+'.pdf');start=time.monotonic()
        if not pdf.exists():
            temp=Path(tempfile.mkdtemp(prefix='curation-'+fid+'-')); token=temp.name
            copy=temp/(fid+'.pptx');shutil.copy2(d['source_path'],copy)
            try:
                r=subprocess.run([SOFFICE,'--headless','--convert-to','pdf','--outdir',str(OUT),str(copy)],capture_output=True,text=True,timeout=90,env={**os.environ,'FONTCONFIG_FILE':str(ROOT/'screening-fonts.conf')})
                if r.returncode or not pdf.exists():
                    print('FAILED',num,fid,r.stderr[-300:],flush=True);return
            except subprocess.TimeoutExpired:
                print('TIMEOUT',num,fid,flush=True);return
        with render_lock:
            doc=pdfium.PdfDocument(str(pdf)); count=len(doc)
            pages=sorted(set([0,min(2,count-1),min(5,count-1),count//2,max(0,count-4),count-1]))
            sheet=Image.new('RGB',(1440,600),'white'); draw=ImageDraw.Draw(sheet)
            for i,p in enumerate(pages):
                page=doc[p];im=page.render(scale=1.1).to_pil().convert('RGB');im=ImageOps.contain(im,(474,264))
                xx=(i%3)*480;yy=(i//3)*300;sheet.paste(im,(xx,yy));draw.text((xx+4,yy+270),f'{num} {fid} PAGE {p+1}/{count}',fill='black')
                page.close()
            doc.close();sheet.save(OUT/(fid+'.jpg'))
        with lock:
            records[:]=[r for r in records if r['id']!=fid]+[{'n':num,'id':fid,'source_path':d['source_path'],'pdf':str(pdf),'sheet':str(OUT/(fid+'.jpg')),'pages': [p+1 for p in pages],'total_pages':count,'seconds':round(time.monotonic()-start,1),'renderer':'LibreOffice headless; screening preview, not native layout certification'}]
            (ROOT/'内页渲染记录.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
            print('RENDERED',len(records),num,fid,round(time.monotonic()-start,1),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(render_one,NUMBERS[:limit]))

if __name__=='__main__': main()
