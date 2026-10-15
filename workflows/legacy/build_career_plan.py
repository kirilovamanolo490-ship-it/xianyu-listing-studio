"""Build the second-pass career library plan from inspected content and covers."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import json,re,collections,colorsys
from pathlib import Path
from second_pass_reorganize import OUT,ZG

CASES='01_职业规划案例与参考（按专业）'
TEMPLATES='02_优选比赛展示模板'
INTERVIEWS='03_人物访谈PPT'
AWARDS='04_真实获奖成品参考（不可编辑）'
GUIDES='05_职业规划方法与PPT制作教程'
OLD='06_基础旧版模板与补充素材'

PREFERRED={
378:('就业赛道','梦想蓝图_职引未来_蓝色展示模板'),
411:('通用展示','职业规划展示_红金版_含数据分析师示例'),
412:('通用展示','职绘未来_逐梦青春_校园展示模板'),
419:('通用展示','青春领航_职引未来_蓝色展示模板'),
446:('通用展示','职业规划展示_橙色版_含规划与简历示例'),
456:('通用展示','职业规划展示_红色版_含规划与简历示例'),
459:('通用展示','墨韵滋心灵_文脉铸辉煌_红色展示模板'),
463:('通用展示','筑梦青春_勇毅前行_绿色展示模板'),
774:('通用展示','职业规划展示_青蓝版_含规划与简历示例'),
}

def clean(text):
    text=re.sub(r'(?i)\.pptx?|\.ppsx|\.pptm','',text)
    text=re.sub(r'^\d+页|最新|最新版|\(恢复\)|（恢复）|自行安装字体包再打开-?\d*','',text)
    text=re.sub(r'(?i)[-_]{1,2}[0-9a-f]{6,64}(?=$|[_-])','',text)
    text=re.sub(r'[\\/:*?"<>|]','_',text)
    text=re.sub(r'(?i)x{2,}|PPT','',text)
    return re.sub(r'[_\s]{2,}','_',text).strip(' _-【】')

def major_name(name):
    name=clean(name).removesuffix('专业')
    name=name.replace('大学生职业生涯规划','').replace('大学','').removeprefix('有关')
    aliases={'幼师':'学前教育','人力资源':'人力资源管理','计算机':'计算机与软件','计算机应用':'计算机与软件','软件与计算机':'计算机与软件','IT':'计算机与软件','IT、软件技术':'计算机与软件','信息管理':'信息管理与信息系统','机电工程':'机电一体化','乡村教育':'教育学','艺术教育':'美术教育','大学自动化':'自动化','机电一体化技术':'机电一体化','酒店管理与数字化运营':'酒店管理','酒店管理和数字化运营':'酒店管理'}
    return aliases.get(name,name)

def color(x):
    m=re.search(r'主题色([0-9A-Fa-f]{6})|配色线索#([0-9A-Fa-f]{6})',x['source_path'])
    if not m:return '通用版式'
    h=m.group(1) or m.group(2);rgb=[int(h[i:i+2],16)/255 for i in (0,2,4)];hu,s,v=colorsys.rgb_to_hsv(*rgb)
    if v<.2:return '深色'
    if s<.16:return '灰白'
    deg=hu*360
    return '红色' if deg<20 or deg>=340 else '橙色' if deg<45 else '黄色' if deg<75 else '绿色' if deg<165 else '青色' if deg<200 else '蓝色' if deg<260 else '紫色'

def main():
    d=json.loads((OUT/'职业规划内容盘点.json').read_text())
    professions={x['id']:x for x in json.loads((OUT/'专业案例归类.json').read_text())}
    specials={x['id']:x for x in json.loads((OUT/'模板专业内容归类.json').read_text())}
    misc={x['id']:x for x in json.loads((OUT/'指南访谈归类.json').read_text())}
    live={x['path']:x for x in json.loads((OUT/'大学生职业规划整理前清单.json').read_text())['items']}
    explicit={x['n']:x for x in d}
    review={x['id']:x for x in json.loads((OUT/'内页渲染记录.json').read_text())}
    extra_cases={382:('会计学','会聚英才_会计职业成长参考'),148:('音乐学','音乐创业职业规划案例'),171:('音乐表演','音乐表演职业生涯规划'),173:('人力资源管理','人力资源管理职业生涯规划'),158:('插画设计','插画师职业规划案例'),341:('自动化','自动化_综合职业方向探索参考')}
    award_names={12:'董振杰_新农科创业者_江苏省第17届职规赛特等奖_不可编辑',13:'普月_电气学科教师_江苏省第17届职规赛特等奖_不可编辑',444:'封赋_人工智能机器学习_江苏省第17届职规赛特等奖_不可编辑'}
    interview_names={1:'会计与银行客户经理_人物访谈',2:'视觉传达与绘画教学_人物访谈',3:'机械制造与自动化_人物访谈',4:'新闻编辑_人物访谈报告',5:'环境工程与景观设计_人物访谈',6:'绘画教师_人物访谈',7:'机械制造与自动化设计师_人物访谈',8:'机械电子与通信工程师_人物访谈',9:'生物技术_人物访谈',10:'舞蹈演员与舞蹈教师_人物访谈',11:'软件工程_人物访谈'}
    single_names={72:'金融服务管理_职业规划单页参考',441:'书法字效_标题文字素材',447:'个人简历单页_橙色',457:'个人简历单页_红色',775:'个人简历单页_蓝色'}
    output=[];count=collections.Counter()
    for x in d:
        n=x['n'];id=x['id'];major=None;reason='按内容与版式分类';kind='基础旧版模板'
        p=professions.get(id);sp=specials.get(id)
        if n in award_names:
            kind='真实获奖不可编辑成品';folder=ZG+'/'+AWARDS;title=award_names[n];reason='图片化结构与高校官方获奖记录交叉核验'
        elif x['pages']==1:
            kind='单页素材';folder=ZG+'/'+OLD+'/单页素材（简历、字效、规划页）';title=single_names.get(n,clean(x['current_name'])+'_单页素材')
        elif n in interview_names:
            kind='人物访谈';folder=ZG+'/'+INTERVIEWS;title=interview_names[n];reason=misc[id]['rationale']
        elif n in (14,149,166):
            kind='方法与制作教程';folder=ZG+'/'+GUIDES
            title={14:'PPT制作与编辑教程_字体图片母版动画',149:'职业规划方法讲座_目标选择与行动方案',166:'职业生涯规划课程_认知目标与实施调整'}[n]
        elif n in PREFERRED:
            track,title=PREFERRED[n];kind='优选比赛展示模板';folder=ZG+'/'+TEMPLATES+'/'+track;reason='已查看封面及内页抽样，色彩与内容版式较统一；含示例与占位内容'
            assert id in review
        elif n in extra_cases or sp or (p and p['major']!='跨专业通用'):
            if n in extra_cases:major,title=extra_cases[n]
            elif sp:major,title=sp['major'],clean(sp['title'])
            else:major,title=p['major'],p['title']
            major=major_name(major);kind='按专业案例与参考';folder=ZG+'/'+CASES+'/'+major;reason=(sp or p or {}).get('rationale','主代理根据实际页文确认专业')
        elif n not in (360,361,362,363,364) and x['section']=='职业规划模板' and x['subsection'] not in ('通用与待核','成长赛道','就业赛道','通用参考','根据专业',None,''):
            major=major_name(x['subsection']);kind='按专业案例与参考';folder=ZG+'/'+CASES+'/'+major;title=major+'_职业规划填写参考';reason='原专业文件夹与文件名明确专业，保留为该专业的填写参考'
        else:
            body=' '.join(s['text'] for s in x['slides'])
            if n==458 or '奖学金' in x['current_name']:
                subtype='奖学金与其他答辩版式';title=f'奖学金答辩参考_{color(x)}_编号{n:03}'
            elif n in (15,16,17,18,19,20,21) or (n>=632 and not re.search(r'自我认知|职业目标|职业探索|职业定位|生涯规划',body)):
                subtype='通用商务与其他场景版式'
                topics={15:'绿色环保商务模板',16:'电影众筹案例展示',17:'通用汇报版式',18:'通用演示版式',19:'商务展示版式',20:'年度工作总结模板',21:'毕业论文答辩模板',782:'锋芒毕露_年度总结模板'}
                title=topics.get(n,f'基础通用演示模板_{color(x)}_编号{n:03}')
            elif x['subsection'] in ('成长赛道','就业赛道') or n in (373,375,376,377,380,383,465):
                subtype='其他比赛版式参考';title=f'{x["subsection"] if x["subsection"] in ("成长赛道","就业赛道") else "职业规划"}_展示版式参考_{color(x)}_编号{n:03}'
            else:
                subtype='旧版基础职业规划模板';title=f'基础职业规划模板_{color(x)}_编号{n:03}'
            folder=ZG+'/'+OLD+'/'+subtype
        title=clean(title)
        title=title.replace('(优秀作品)','').replace('（优秀作品）','')
        if kind=='按专业案例与参考' and major not in title:title=major+'_'+title
        # Award labels are retained only for the three individually verified image-only cases.
        if n not in award_names:title=title.replace('获奖作品','作品').replace('获奖','')
        pages=f'_{x["pages"]}页' if x['pages'] else ''
        base=title+pages;count[(folder,base)]+=1
        if count[(folder,base)]>1:base+=f'_版本{count[(folder,base)]}'
        name=base+Path(x['source_path']).suffix.lower();obj=live[x['current_path']]
        output.append({'id':id,'n':n,'sha256':x['sha256'],'fid':obj['fid'],'bytes':obj['size'],'source_path':x['source_path'],'old_path':x['current_path'],'old_name':x['current_name'],'kind':kind,'major':major,'title':title,'folder':folder,'name':name,'target_path':folder+'/'+name,'rationale':reason})
    assert len(output)==784 and len({x['fid'] for x in output})==784 and len({x['target_path'] for x in output})==784
    (OUT/'职业规划整理计划.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    stats={'count':len(output),'by_kind':dict(collections.Counter(x['kind'] for x in output)),'major_count':len({x['major'] for x in output if x['major']}),'by_major':dict(collections.Counter(x['major'] for x in output if x['major'])),'preferred_numbers':list(PREFERRED),'source_content_modified':False}
    (OUT/'职业规划整理统计.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2));print(json.dumps(stats,ensure_ascii=False))

if __name__=='__main__':main()
