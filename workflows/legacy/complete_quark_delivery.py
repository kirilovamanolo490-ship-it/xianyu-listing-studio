"""Finish the authorized delivery folders, verify samples, and share only these folders."""
from __future__ import annotations

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import hashlib,json
from pathlib import Path
from dataclasses import asdict
from urllib.parse import urlsplit
import requests
from quark_ppt_transfer import Transfer,RECORD,ROOT,AUTH,now,atomic_json
from xpan_auto.quark_adapter import QuarkItem,NewShare

def main():
 t=Transfer();report=json.loads((RECORD/'delivery_逐文件核验.json').read_text())
 if not report.get('complete') or report.get('expected_files') not in [1482,1484]:raise RuntimeError('Base delivery audit is incomplete')
 path=RECORD/'正式交付上传清单.json';doc=json.loads(path.read_text());rows=doc['files']
 for code,name in [('ZG','大学生职业规划PPT资料合集'),('CS','创新创业PPT资料合集')]:
  p=ROOT/'交付配套'/name/'02_重点样例逐页填写参考.txt';b=p.read_bytes();cloud='/商品发布/PPT资料/01_正式交付/'+name+'/'+p.name
  row={'product':code,'product_name':name,'source_path':str(p),'filename':p.name,'bytes':len(b),'mtime_ns':p.stat().st_mtime_ns,'md5':hashlib.md5(b).hexdigest(),'sha1':hashlib.sha1(b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest(),'delivery_cloud_path':cloud,'delivery_name':p.name,'delivery_relative_path':p.name,'section':'配套说明'}
  known=next((x for x in rows if x['delivery_cloud_path']==cloud),None)
  if not known:rows.append(row)
  elif known['sha256']!=row['sha256']:raise RuntimeError('Guide changed after upload manifest')
  t.upload(row,cloud,phase='delivery')
 atomic_json(path,doc)
 assert len(rows)==1484 and len({x['delivery_cloud_path'] for x in rows})==1484
 report=t.audit(rows,'delivery_cloud_path','delivery')
 if not report['complete']:raise RuntimeError('Final directory audit failed')
 atomic_json(RECORD/'delivery_进度.json',{'phase':'delivery','updated':now(),'complete':True,'total':1484,'uploaded':1484,'verified':1484,'failed':0,'note':'1478 个演示文件和 6 个配套文件'})
 print('Directory verified: 1484 files',flush=True)
 # Use a regular browser session; do not bypass the web client's large-file limit.
 s=requests.Session()
 for c in json.loads(AUTH.read_text())['cookies']:
  if 'quark.cn' in c.get('domain',''):s.cookies.set(c['name'],c['value'],domain=c['domain'],path=c.get('path','/'))
 s.headers.update({'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Referer':'https://pan.quark.cn/','Origin':'https://pan.quark.cn'})
 samples=[]
 for name in ['大学生职业规划PPT资料合集','创新创业PPT资料合集']:
  for suffix in ['.pptx','.ppt']:
   eligible=[x for x in rows if '/'+name+'/' in x['delivery_cloud_path'] and Path(x['source_path']).suffix.lower()==suffix and 2*1024**2<x['bytes']<7*1024**2]
   samples.append(sorted(eligible,key=lambda x:x['sha256'])[0])
 records=[]
 for row in samples:
  fid=t.known[row['delivery_cloud_path']]['fid']
  rr=s.post('https://drive-pc.quark.cn/1/clouddrive/file/download',params={'pr':'ucpro','fr':'pc'},json={'fids':[fid]},timeout=30);data=rr.json()
  if rr.status_code!=200 or data.get('status')!=200:raise RuntimeError('Sample download metadata failed: '+str(data.get('code')))
  url=data['data'][0]['download_url'];host=urlsplit(url).hostname or ''
  if not (host.endswith('quark.cn') or host.endswith('aliyuncs.com')):raise RuntimeError('Unexpected sample download host')
  response=s.get(url,stream=True,timeout=(30,120))
  if response.status_code!=200:raise RuntimeError('Sample readback HTTP '+str(response.status_code))
  h=hashlib.sha256();size=0
  for block in response.iter_content(1024*1024):h.update(block);size+=len(block)
  ok=size==row['bytes'] and h.hexdigest()==row['sha256']
  records.append({'checked_at':now(),'cloud_path':row['delivery_cloud_path'],'fid':fid,'bytes':size,'sha256':h.hexdigest(),'matches_source':ok})
  atomic_json(RECORD/'正式交付全文回读抽查.json',records)
  if not ok:raise RuntimeError('Sample content mismatch')
  print('Readback matched:',name if False else Path(row['delivery_cloud_path']).name,flush=True)
 sharepath=RECORD/'两款正式分享链接.json';shares=json.loads(sharepath.read_text()) if sharepath.exists() else {}
 for code,name in [('ZG','大学生职业规划PPT资料合集'),('CS','创新创业PPT资料合集')]:
  folder='/商品发布/PPT资料/01_正式交付/'+name;fid=t.folders[folder]
  if code in shares:
   prev=shares[code]
   if prev.get('share_url'):share=NewShare(fid=prev['fid'],title=prev['title'],share_url=prev['share_url'],passcode=prev.get('passcode'))
   else:raise RuntimeError('Share attempt needs reconciliation; will not create a duplicate')
  else:
   shares[code]={'fid':fid,'title':name,'cloud_path':folder,'status':'creating','started_at':now()};atomic_json(sharepath,shares)
   share=t.q.create_share(QuarkItem(fid=fid,name=name,is_dir=True),expiry='permanent',password_mode='generated')
   shares[code].update(asdict(share),status='created',created_at=now());atomic_json(sharepath,shares)
  info=t.q.inspect_share(share.share_url)
  if len(info.items)!=1 or info.items[0].name!=name or not info.items[0].is_dir:raise RuntimeError('Share scope mismatch')
  shares[code].update(status='verified',share_root_names=[x.name for x in info.items],checked_at=now(),presentation_files=784 if code=='ZG' else 694,support_files=3)
  atomic_json(sharepath,shares);print('Share scope verified:',name,flush=True)
 atomic_json(ROOT/'完整商品图_v4/分享链接.json',shares)
 print('Complete: samples matched and both shares verified',flush=True)

if __name__=='__main__':main()
