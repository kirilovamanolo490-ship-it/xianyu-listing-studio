"""Verify public browsing and byte-for-byte notes, then update workspace pointers."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import json,hashlib,requests
from pathlib import Path
from urllib.parse import urlsplit
from second_pass_reorganize import OUT,BASE,CS,ZG,CS_GROUP,CS_GENERIC,CS_GUIDES,ROOT
from build_career_plan import CASES,TEMPLATES,INTERVIEWS,AWARDS,GUIDES,OLD
from quark_ppt_transfer import QuarkAdapter,AUTH,atomic_json,now

def main():
    report=json.loads((OUT/'目录整理结果.json').read_text());assert report['complete']
    cs=json.loads((OUT/'创新创业最终核验.json').read_text());zg=json.loads((OUT/'大学生职业规划最终核验.json').read_text());stats=report['career_statistics']
    shares=json.loads((BASE/'发布记录/2026-10-13_分类整理/当前两款分享链接.json').read_text())
    public=requests.Session();public.trust_env=False
    def req(method,url,headers,params,payload,timeout):
        r=public.request(method,url,headers=headers,params=params,json=payload,timeout=timeout)
        if r.status_code!=200:raise RuntimeError('Anonymous share HTTP '+str(r.status_code))
        return r.json()
    anon=QuarkAdapter(cookie_header='',request_fn=req,timeout=30);checks=[]
    for code,share in shares.items():
        name='创新创业' if code=='CS' else '大学生职业规划';info=anon.inspect_share(share['share_url'])
        assert len(info.items)==1 and info.items[0].fid==share['fid'] and info.items[0].name==name
        token=anon._get_stoken(info.pwd_id,anon._passcode(share['share_url']))
        _,items=anon._share_detail(info.pwd_id,token,pdir_fid=share['fid'])
        expected={CS_GROUP,CS_GENERIC,CS_GUIDES,'00_阅读说明.txt','01_分类目录.txt'} if code=='CS' else {CASES,TEMPLATES,INTERVIEWS,AWARDS,GUIDES,OLD,'00_阅读说明.txt','01_分类目录.txt'}
        assert {x.name for x in items}==expected
        entry={'product':name,'without_account_cookies':True,'same_shared_root_fid':True,'visible_root_items':sorted(expected)}
        if code=='ZG':
            fid=next(x.fid for x in items if x.name==CASES);_,majors=anon._share_detail(info.pwd_id,token,pdir_fid=fid)
            assert {x.name for x in majors}==set(stats['by_major']) and len(majors)==stats['major_count']
            entry['visible_major_folders']=len(majors)
        share.update(cloud_path=ROOT+'/'+name,title=name,checked_at=now(),status='verified',support_files=3 if code=='CS' else 4)
        checks.append(entry)
    atomic_json(OUT/'匿名分享访问核验.json',checks)
    s=requests.Session();s.trust_env=False;s.headers.update({'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Referer':'https://pan.quark.cn/','Origin':'https://pan.quark.cn'})
    for c in json.loads(AUTH.read_text())['cookies']:
        if c.get('domain','').endswith('quark.cn'):s.cookies.set(c['name'],c['value'],domain=c['domain'],path=c.get('path','/'))
    readbacks=[]
    for item in json.loads((OUT/'新配套文件.json').read_text()):
        response=s.post('https://drive-pc.quark.cn/1/clouddrive/file/download',params={'pr':'ucpro','fr':'pc'},json={'fids':[item['fid']]},timeout=30);j=response.json()
        assert response.status_code==200 and j.get('status')==200
        url=j['data'][0]['download_url'];host=urlsplit(url).hostname or ''
        assert host.endswith('.quark.cn') or host.endswith('.aliyuncs.com')
        r=s.get(url,timeout=45)
        if r.status_code!=200:raise RuntimeError('Support readback HTTP '+str(r.status_code)+'; signed URL omitted')
        assert hashlib.sha256(r.content).hexdigest()==item['sha256']
        readbacks.append({'path':item['path'],'fid':item['fid'],'bytes':len(r.content),'sha256':item['sha256'],'matched':True})
    atomic_json(OUT/'配套文件全文回读核验.json',readbacks)
    report.update(verified_at=now(),public_shares_verified=True,notes_readback_verified=True,career_files=zg['file_count'],innovation_files=cs['file_count'])
    atomic_json(OUT/'整理完成报告.json',report);atomic_json(OUT/'当前分享链接.json',shares);atomic_json(BASE/'完整商品图_v4/分享链接.json',shares)
    intro=f'''# PPT 商品发布工作区

更新：2026-10-13（二次整理）。本轮修改已落实到夸克，两款原分享链接继续使用。PPT内页与本地源库未修改。

## 当前入口

| 合集 | 演示文件 | 配套文件 | 分享 |
| --- | ---: | ---: | --- |
| 创新创业 | 694 | 3 | [打开合集]({shares['CS']['share_url']}) |
| 大学生职业规划 | 784 | 4 | [打开合集]({shares['ZG']['share_url']}) |

创新创业根目录仅保留：`{CS_GROUP}`、`{CS_GENERIC}`、`{CS_GUIDES}`、阅读说明和分类目录。8个行业方向全部收进第一个入口，通用模板取消了重复套层。

大学生职业规划根目录为：

- `{CASES}`：346份，109个专业或职业方向；原案例与参考合并。
- `{TEMPLATES}`：9份，经封面及内页抽样筛选，含需替换的示例内容。
- `{INTERVIEWS}`：11份。
- `{AWARDS}`：3份图片化成品，对应获奖结果经高校官方资料核验。
- `{GUIDES}`：3份方法或制作教程及原样例填写参考。
- `{OLD}`：407份普通、基础或旧版模板和5份单页素材，分用途放置。
- `00_阅读说明.txt` 与 `01_分类目录.txt`。

784份职业规划及694份创新创业演示文件的ID与大小已逐份核对，未删除演示文件。旧目录在确认没有文件后清理。两条分享链接及新根目录通过无账号Cookie访问核验，职业规划109个专业入口也已从分享端核验。5份新配套文字文件已下载并比对SHA256。

当前操作、改名映射、视觉抽样和核验记录见 [二次整理完成报告](发布记录/2026-10-13_二次整理/整理完成报告.json)。[职业规划分类目录](发布记录/2026-10-13_二次整理/买家说明/大学生职业规划/01_分类目录.txt) 与 [创新创业分类目录](发布记录/2026-10-13_二次整理/买家说明/创新创业/01_分类目录.txt) 可直接查看。

## 历史材料

`完整商品图_v4` 为2026-10-11制作的商品图片；`交付配套` 是首次交付配套的历史版本。当前说明以夸克及二次整理记录为准。

`发布记录/2026-10-11_夸克首次入库`、`发布记录/2026-10-13_分类整理` 保留为历史证据，不能代表本轮最新路径。历史批次脚本需要按最新目录核对后再使用。`商品`保存选样与来源，`GitHub`保存参考项目；其余视觉优化目录为历史草稿。尚未发布闲鱼商品。
'''
    (BASE/'README.md').write_text(intro)
    (BASE/'交付范围与分享目录.md').write_text('# 当前夸克交付范围\n\n更新：2026-10-13（二次整理）。\n\n'+intro[intro.index('## 当前入口'):intro.index('## 历史材料')]+'\n云端源库备份与正式交付外层已在上一轮删除，本轮只调整两款合集内部分类。原始本地模板库保留，本轮没有改动任何PPT内页。\n')
    print(json.dumps({'complete':True,'innovation_ppt':694,'career_ppt':784,'career_categories':stats['by_kind'],'major_folders':stats['major_count'],'new_notes_readback':len(readbacks),'public_shares_verified':True},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
