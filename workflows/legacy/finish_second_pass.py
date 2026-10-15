"""Synchronize buyer notes, remove verified empty old trees, and verify both shares."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import json,hashlib,collections,requests
from pathlib import Path
from urllib.parse import urlsplit
from second_pass_reorganize import SecondPass,OUT,CS,ZG,CS_GROUP,CS_GENERIC,CS_GUIDES,scan,verify_preserved,BASE,ROOT
from build_career_plan import CASES,TEMPLATES,INTERVIEWS,AWARDS,GUIDES,OLD
from quark_ppt_transfer import atomic_json,now,QuarkAdapter,AUTH

def replace_text(t,parentpath,name,path,allowed_old):
    b=path.read_bytes();row={'source_path':str(path),'bytes':len(b),'mtime_ns':path.stat().st_mtime_ns,'md5':hashlib.md5(b).hexdigest(),'sha1':hashlib.sha1(b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest()}
    result=t.upload(row,parentpath+'/__整理中_'+name,phase='second_pass_notes');fid=result['fid'];parent=t.folder(parentpath)
    existing=t.list_files(parent)
    for x in existing:
        if x['file_name']==name and x['fid']!=fid:
            assert x['fid'] in allowed_old,'Unexpected existing support file'
            t.delete([x['fid']],'replace outdated support file '+name)
    current=next(x for x in t.list_files(parent) if x['fid']==fid)
    if current['file_name']!=name:t.rename(fid,name)
    assert any(x['fid']==fid and x['file_name']==name and x['size']==len(b) for x in t.list_files(parent))
    return {'fid':fid,'name':name,'path':parentpath+'/'+name,'local_path':str(path),'sha256':row['sha256'],'bytes':len(b)}

def main():
    t=SecondPass();plan=json.loads((OUT/'职业规划整理计划.json').read_text());stats=json.loads((OUT/'职业规划整理统计.json').read_text())
    csbefore=json.loads((OUT/'创新创业整理前清单.json').read_text());zgbefore=json.loads((OUT/'大学生职业规划整理前清单.json').read_text())
    cscurrent=scan(t,t.folders[CS],CS);zgcurrent=scan(t,t.folders[ZG],ZG);byid={x['fid']:x for x in zgcurrent}
    assert all(byid[x['fid']]['path']==x['target_path'] and byid[x['fid']]['size']==x['bytes'] for x in plan)
    assert verify_preserved(csbefore['items'],cscurrent)==694 and verify_preserved(zgbefore['items'],zgcurrent)==784
    csold=[x for x in csbefore['items'] if not x['dir'] and x['parent_fid']==csbefore['root_fid']]
    zgold=[x for x in zgbefore['items'] if not x['dir'] and x['parent_fid']==zgbefore['root_fid']]
    allowed={x['fid'] for x in csold+zgold}
    docroot=OUT/'买家说明';docroot.mkdir(exist_ok=True)
    docs=[]
    csnote=f'''创新创业PPT资料阅读说明
更新：2026年10月13日（二次整理）

一、目录入口
{CS_GROUP}：先选教育、医疗健康、科技、农业、生态环保、文化文旅、商业服务或社会治理，再区分精选PPT、参考模板与参考案例。
{CS_GENERIC}：没有明确行业内容的通用版式，直接按文件名选取，共72份。
{CS_GUIDES}：商业计划书写法、财务分析、挑战杯申报评审等资料与既有样例填写说明。资料内容按原件保留，具体年份与适用赛事以正文为准。

二、数量与选用
共694份演示文件：56份精选PPT、152份参考模板、479份参考案例、3份单页素材和4份指南。
精选侧重封面与内页抽样查看的视觉组织；包含需要填写的主题模板。参考区保留普通案例、结构与版式素材。
完整路径见01_分类目录.txt。文件名按项目主题、用途和页数说明；版本或配色用于区分不同文件。
本轮只移动、分类、重命名；没有修改任何PPT内页。使用前替换示例人名、数据和占位内容。
'''
    zgnote=f'''大学生职业规划PPT资料阅读说明
更新：2026年10月13日（二次整理）

先按使用目的选择入口：
{CASES}
  原“职业规划案例”和“职业规划参考”已合并，同一个专业只保留一个入口。共{stats['by_kind']['按专业案例与参考']}份，按{stats['major_count']}个专业或职业方向分组，也收纳从原模板区找出的专业填写参考。它们用于借鉴专业内容与规划结构，完成度和版式各有不同。
{TEMPLATES}
  共9份，按就业赛道或通用展示用途归档。已检查封面和内页抽样，优先保留视觉统一、版式较清楚的候选。模板仍可能含操作说明、示例人物和占位文案，需自行替换。
{INTERVIEWS}
  共11份，供人物访谈展示、访谈问答和心得写法参考。文件名已按实际访谈对象或领域改写。
{AWARDS}
  共3份，对应董振杰、普月、封赋的获奖案例。具体赛事、奖项与官方来源见该目录中的00_获奖与不可编辑说明.txt。
  这些PPT的可见页面是整张图片，不能直接修改图内文字、图表和排版；适合观看、学习结构和展示节奏，不应当作可编辑文字模板。
{GUIDES}
  讲职业规划思路、目标与行动方案、PPT字体图片母版动画操作，以及原有样例填写参考。这里不是某届比赛官方规则包，已把原“备赛指南”里无关的通用模板移走。
{OLD}
  407份普通、基础或旧版模板，以及5份单页素材。按旧版职业规划版式、通用商务与其他场景、其他比赛版式、奖学金答辩、单页用途分别放置。用于借鉴或补充，优先级低于前面的专业案例和优选展示模板。
  单页素材包括3份简历、1份标题字效、1份金融服务管理规划页，均不是完整参赛PPT。

数量：784份演示文件全部保留。部分文件含示例内容，部分普通版式只适合参考。本轮不修改PPT文字、图片、布局、动画或文件格式。
页数依据文件结构读取，可能包含隐藏页。完整路径见01_分类目录.txt。同名不同内容用版本号区分。
“重点样例逐页填写参考”保留原配套说明；其中旧文件名可按项目主题在新目录查找。
'''
    awardnote='''真实获奖成品参考与不可编辑说明

1. 董振杰｜新农科创业者｜35页
对应赛事：“武进人才杯”江苏省第十七届大学生职业规划大赛。
奖项：特等奖。扬州大学官方事迹材料在省级荣誉中明确列出该奖项（2023年1月）。
官方依据：https://www.yzu.edu.cn/docs/fujian1dongzhenjietongxueshijicailiao.pdf

2. 普月｜电气学科教师｜29页
对应赛事：“武进人才杯”江苏省第十七届大学生职业规划大赛。
奖项：研究生赛道特等奖。河海大学官方新闻同时描述高校电气学科教师职业目标和“薪火相传，让电达四方”主题。
官方依据：https://ceee.hhu.edu.cn/2023/0222/c12555a257122/page.htm

3. 封赋｜人工智能机器学习｜37页
对应赛事：“武进人才杯”江苏省第十七届大学生职业规划大赛。
奖项：特等奖。东南大学官方新闻明确列出吴健雄学院封赋获奖。
官方依据：https://news.seu.edu.cn/2023/0113/c5495a433725/page.htm

不可编辑是什么意思：
可见页面已经合成为图片，不能像普通PPT那样选择并修改图片里面的标题、正文、图表或排版。可以观看、播放、学习结构；图片对象本身仍可移动缩放或删除，这不等于能够编辑图片内部文字。
前两份每页各一张整页图片。第三份有35张图片页和2张空白页；本轮没有补页或修改原稿。
官方资料核验的是对应选手和比赛获奖结果。本文件是现有资料库中的图片化参考副本，不宣称它是赛事官方发布的可编辑源稿；也不将省级特等奖称为国赛奖项。
'''
    for product,root,body,rows in [('创新创业',CS,csnote,cscurrent),('大学生职业规划',ZG,zgnote,zgcurrent)]:
        folder=docroot/product;folder.mkdir(exist_ok=True)
        paths=sorted(x['path'].removeprefix(root+'/') for x in rows if not x['dir'] and Path(x['file_name']).suffix.lower() in ('.ppt','.pptx','.pptm','.ppsx'))
        (folder/'00_阅读说明.txt').write_text(body)
        (folder/'01_分类目录.txt').write_text(product+'分类目录\n更新：2026年10月13日（二次整理）\n演示文件'+str(len(paths))+'份\n\n'+'\n'.join(paths)+'\n')
        for name in ['00_阅读说明.txt','01_分类目录.txt']:docs.append(replace_text(t,root,name,folder/name,allowed));print('NOTES',product,name,flush=True)
    ap=docroot/'大学生职业规划'/'00_获奖与不可编辑说明.txt';ap.write_text(awardnote);docs.append(replace_text(t,ZG+'/'+AWARDS,ap.name,ap,set()))
    # Keep the pre-existing sample-writing note and clarify its location.
    sample=next(x for x in zgold if x['file_name'].startswith('02_'))
    current=scan(t,t.folders[ZG],ZG);byid={x['fid']:x for x in current};target=t.folder(ZG+'/'+GUIDES)
    obj=byid[sample['fid']]
    if obj['file_name']!='重点样例逐页填写参考（原配套）.txt':t.rename(obj['fid'],'重点样例逐页填写参考（原配套）.txt')
    if obj['parent_fid']!=target:t.move([obj['fid']],target,'move existing career sample guidance into tutorial folder')
    obsolete=[x['fid'] for x in zgold if x['fid']!=sample['fid'] and x['fid'] in byid]
    if obsolete:t.delete(obsolete,'remove replaced career notes and obsolete index after new documents verified')
    current=scan(t,t.folders[ZG],ZG);byid={x['fid']:x for x in current}
    oldtops=[x for x in zgbefore['items'] if x['dir'] and x['parent_fid']==zgbefore['root_fid']]
    removing=[]
    for old in oldtops:
        obj=byid.get(old['fid'])
        if not obj:continue
        assert not any(not x['dir'] and x['path'].startswith(obj['path']+'/') for x in current),obj['path']
        removing.append(obj['fid'])
    if removing:t.delete(removing,'remove seven verified empty legacy career directory trees')
    final={}
    for product,root,before,expected in [('创新创业',CS,csbefore,697),('大学生职业规划',ZG,zgbefore,788)]:
        rows=scan(t,t.folders[root],root);count=verify_preserved(before['items'],rows);files=[x for x in rows if not x['dir']]
        assert len(files)==expected,(product,len(files))
        if product=='大学生职业规划':
            byid={x['fid']:x for x in rows};assert all(byid[x['fid']]['path']==x['target_path'] for x in plan)
        expected_names={CS_GROUP,CS_GENERIC,CS_GUIDES,'00_阅读说明.txt','01_分类目录.txt'} if product=='创新创业' else {CASES,TEMPLATES,INTERVIEWS,AWARDS,GUIDES,OLD,'00_阅读说明.txt','01_分类目录.txt'}
        assert {x['file_name'] for x in rows if x['parent_fid']==t.folders[root]}==expected_names
        final[product]={'at':now(),'complete':True,'presentation_count':count,'file_count':len(files),'items':rows}
        atomic_json(OUT/(product+'最终核验.json'),final[product]);t.refresh_map(rows)
    atomic_json(OUT/'新配套文件.json',docs)
    valid={CS,ZG}
    for item in final.values():valid.update(x['path'] for x in item['items'] if x['dir'])
    t.folders={p:fid for p,fid in t.folders.items() if not (p.startswith(CS+'/') or p.startswith(ZG+'/')) or p in valid}
    atomic_json(t.folder_file,t.folders)
    atomic_json(OUT/'目录整理结果.json',{'at':now(),'complete':True,'ppt_preserved':1478,'career_statistics':stats,'removed_empty_legacy_roots':len(removing),'source_ppt_contents_modified':False})
    print('STRUCTURE AND FILES VERIFIED',flush=True)

if __name__=='__main__':main()
