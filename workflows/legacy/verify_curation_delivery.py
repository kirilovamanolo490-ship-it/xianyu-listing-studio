"""Final public-link and support-file readback checks, then synchronize local documentation."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import json,hashlib,collections
from pathlib import Path
from urllib.parse import urlsplit
import requests
from reorganize_quark_ppt import Reorganizer,BASE,OUT,ROOT
from quark_ppt_transfer import QuarkAdapter,AUTH,now,atomic_json

def main():
    cs=json.loads((OUT/'创新创业最终核验.json').read_text());zg=json.loads((OUT/'大学生职业规划原样保留核验.json').read_text())
    assert cs['complete'] and zg['complete']
    plan=json.loads((OUT/'创新创业整理计划.json').read_text());shares=json.loads((BASE/'发布记录/2026-10-11_夸克首次入库/两款正式分享链接.json').read_text())
    public=requests.Session();public.trust_env=False
    def request(method,url,headers,params,payload,timeout):
        r=public.request(method,url,headers=headers,params=params,json=payload,timeout=timeout);r.raise_for_status();return r.json()
    anon=QuarkAdapter(cookie_header='',request_fn=request,timeout=25)
    share_checks=[]
    for code,s in shares.items():
        name='创新创业' if code=='CS' else '大学生职业规划'
        info=anon.inspect_share(s['share_url'])
        assert len(info.items)==1 and info.items[0].fid==s['fid'] and info.items[0].name==name
        if code=='CS':
            token=anon._get_stoken(info.pwd_id,anon._passcode(s['share_url']))
            _,contents=anon._share_detail(info.pwd_id,token,pdir_fid=s['fid'])
            names={x.name for x in contents}
            expected={'教育','医疗健康','科技','农业','生态环保','文化文旅','商业服务','社会治理','通用模板','99_备赛资料','00_阅读说明.txt','01_分类目录.txt'}
            assert names==expected,names
        else:names={x.name for x in info.items}
        share_checks.append({'code':code,'at':now(),'without_account_cookies':True,'same_root_fid':True,'root_name':name,'visible_names':sorted(names)})
        s.update(title=name,cloud_path=ROOT+'/'+name,status='verified',checked_at=now(),share_root_names=[name])
    atomic_json(OUT/'最终分享链接核验.json',share_checks)
    atomic_json(OUT/'当前两款分享链接.json',shares)
    t=Reorganizer();session=requests.Session();session.trust_env=False
    session.headers.update({k:v for k,v in t.q.headers.items() if k.lower()!='cookie'})
    session.headers['user-agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    for c in json.loads(AUTH.read_text())['cookies']:
        if c.get('domain','').endswith('quark.cn'):session.cookies.set(c['name'],c['value'],domain=c['domain'],path=c.get('path','/'))
    readbacks=[]
    for p in sorted((OUT/'买家说明').glob('*.txt')):
        obj=next(x for x in cs['items'] if x['path']==ROOT+'/创新创业/'+p.name)
        response=session.post('https://drive-pc.quark.cn/1/clouddrive/file/download',params={'pr':'ucpro','fr':'pc'},json={'fids':[obj['fid']]},timeout=30)
        metadata=response.json();assert response.status_code==200 and metadata.get('status')==200
        meta=metadata['data'][0]
        url=meta['download_url'];host=urlsplit(url).hostname or ''
        assert host=='quark.cn' or host.endswith('.quark.cn') or host.endswith('.aliyuncs.com')
        r=session.get(url,timeout=45)
        if r.status_code!=200:raise RuntimeError('Support readback HTTP '+str(r.status_code)+'; signed download URL omitted')
        h=hashlib.sha256(r.content).hexdigest()
        assert r.content==p.read_bytes()
        readbacks.append({'name':p.name,'fid':obj['fid'],'bytes':len(r.content),'sha256':h,'matches_local':True})
    atomic_json(OUT/'配套文件全文回读核验.json',readbacks)
    counts=collections.Counter('精选PPT' if x['selected'] else x['material_kind'] for x in plan)
    bycategory={cat:{'total':sum(x['category']==cat for x in plan),'selected':sum(x['category']==cat and x['selected'] for x in plan)} for cat in dict.fromkeys(x['category'] for x in plan)}
    summary={'at':now(),'complete':True,'root_categories':['创新创业','大学生职业规划'],'source_backup_removed':True,'delivery_wrapper_removed':True,'innovation_counts':dict(counts),'by_category':bycategory,'presentation_files_preserved':694,'support_files':3,'career_files_preserved':787,'source_ppt_contents_modified':False,'public_links_verified':True,'support_readbacks_verified':True}
    atomic_json(OUT/'整理完成报告.json',summary)
    atomic_json(BASE/'完整商品图_v4/分享链接.json',shares)
    cslink=shares['CS']['share_url'];zglink=shares['ZG']['share_url']
    readme=f'''# PPT 商品发布工作区

更新：2026-10-13。夸克目录已按本轮要求整理。尚未发布闲鱼商品。

## 当前夸克目录

- `/商品发布/PPT资料/创新创业`
- `/商品发布/PPT资料/大学生职业规划`

云端 `00_源库备份` 已删除，`01_正式交付` 层级已移除。两款原分享文件夹的文件 ID 保持不变，原链接已重新核验。

| 商品 | 演示文件 | 配套文件 | 链接 |
| --- | ---: | ---: | --- |
| 创新创业 | 694 | 3 | [打开合集]({cslink}) |
| 大学生职业规划 | 784 | 3 | [打开合集]({zglink}) |

创新创业以教育、医疗健康、科技、农业、生态环保、文化文旅、商业服务、社会治理为行业入口，另设通用模板和备赛资料。各行业区分精选PPT、参考模板、参考案例；没有内容的空目录已清理。

本轮筛选结果：精选PPT 56份、参考模板152份、参考案例479份、单页素材3份、备赛指南4份。精选依据封面与内页抽样查看，部分为需要填写的主题模板，不代表全库逐页完稿验收。只改变云端文件名和位置，没有修改任何PPT页内内容或本地源库。

大学生职业规划这轮仅移到顶层并简化合集名称，内部787个文件的ID、名称和大小保持一致。

最新记录见 [本轮完成报告](发布记录/2026-10-13_分类整理/整理完成报告.json) 和 [分类目录](发布记录/2026-10-13_分类整理/买家说明/01_分类目录.txt)。本轮云端核验覆盖全部694份创新创业演示文件，说明与目录已全文下载回读，原分享链接经过无账号Cookie核验。

## 其他工作区内容

- `完整商品图_v4`：此前制作的两款18张商品图、下载包和预览。图片生成于2026-10-11。
- `交付配套`：首次交付时的旧版配套；当前说明和目录以本轮记录及夸克文件为准。
- `商品`：选样与来源记录。
- `GitHub`：参考项目与许可证记录。
- `发布记录/2026-10-11_夸克首次入库`：历史上传、原目录和分享核验记录，保留用于追溯，不再代表当前目录。
- `视觉优化_v2`、`完整生图_v3`：历史草稿。
'''
    (BASE/'README.md').write_text(readme)
    scope=f'''# 两款 PPT 资料的当前交付范围

更新：2026-10-13。

```text
商品发布/PPT资料/
├── 创新创业/
│   ├── 教育、医疗健康、科技、农业
│   ├── 生态环保、文化文旅、商业服务、社会治理
│   ├── 通用模板
│   ├── 99_备赛资料
│   ├── 00_阅读说明.txt
│   └── 01_分类目录.txt
└── 大学生职业规划/
```

创新创业各行业下按实际内容设置 `01_精选PPT`、`02_参考模板`、`03_参考案例`，商业服务另有单页素材；只保留有文件的目录。备赛资料集中保存4份比赛指南和原重点样例填写参考。

创新创业694个演示文件全部保留原文件ID和大小。筛选为56份精选、152份参考模板、479份参考案例、3份单页素材、4份比赛指南，另有3份配套文件。大学生职业规划保留784个演示文件和3份配套文件。

本轮只筛选、分类、重命名，没有修改PPT内页。精选是封面与内页抽样筛选结果，包含主题模板，不等同于已填完、可直接提交的参赛作品。

云端源库备份和正式交付外层目录已删除。本地来源仍保留：`aippt/模板库/创赛` 与 `aippt/模板库/BB0086 大学生职业生涯规划大赛 PPT`。

- [创新创业]({cslink})
- [大学生职业规划]({zglink})

两条原分享链接已重新以无账号Cookie方式核验。当前目录、逐文件ID核验、配套文件回读与操作日志见 [2026-10-13分类整理记录](发布记录/2026-10-13_分类整理/整理完成报告.json)。历史首次入库记录保持原样，不能用于推断当前云端路径。
'''
    (BASE/'交付范围与分享目录.md').write_text(scope)
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
