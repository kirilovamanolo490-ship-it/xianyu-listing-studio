
# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")
import os

from pathlib import Path
import sys,json,shutil,subprocess,hashlib
from PIL import Image
base=Path(os.environ.get('XIANYU_LEGACY_PATH_SAVE_GENERATED_PRODUCT_IMAGE_1', '/path/to/configure'))
key,src=sys.argv[1:3];src=Path(src);p=next(x for x in json.loads((base/'生图任务.json').read_text())['images'] if x['id']==key)
with Image.open(src) as im:w,h=im.size
target=p.get('target_size',[1800,2400]);tw,th=target
if abs(w/h-tw/th)>.003:
 print(json.dumps({'id':key,'status':'ratio_rejected','width':w,'height':h}));sys.exit(3)
raw=base/'生成原图'/f'{key}.png';raw.parent.mkdir(exist_ok=True);shutil.copy2(src,raw)
out=Path(p['output_file']);out.parent.mkdir(exist_ok=True)
subprocess.run(['sips','-z',str(th),str(tw),str(raw),'--out',str(out)],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['sips','-s','format','jpeg','-s','formatOptions','90',str(out),'--out',str(out.with_suffix('.jpg'))],check=True,stdout=subprocess.DEVNULL)
for f in [out,out.with_suffix('.jpg')]:
 with Image.open(f) as im:assert im.size==(tw,th)
r={'id':key,'generated_path':str(src),'raw_path':str(raw),'output_path':str(out),'native_size':[w,h],'export_size':target,'export_operation':'等比例尺寸规范化及JPG编码，未以代码重排或覆盖图文','sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
with (base/'生成记录.jsonl').open('a') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
print(json.dumps({'id':key,'status':'saved','size':target}))
