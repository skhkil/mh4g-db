#!/usr/bin/env python3
import json,re,pathlib,collections
ROOT=pathlib.Path(__file__).resolve().parents[1]
D=ROOT/'data'; OUT=D/'skill_refs'; OUT.mkdir(exist_ok=True)
skills=json.load(open(D/'skills.json',encoding='utf-8'))
decos=json.load(open(D/'decorations.json',encoding='utf-8'))
armors=json.load(open(D/'armors.json',encoding='utf-8'))

ATTACK={'KO','공격','달인','통격','투혼','중격','차지단축','검술','장인','예리도','발도기절','발도치명타','저력','잠재력','역경','도공','강격','강완','결벽','분노','참격술','북진낫토류','특수치명타','속성치명타','멸기공격','포술','폭탄강화','직공','베기','연린'}
DEFENSE={'방어','가드강화','가드성능','가호','근성','체력','회복량','회복속도','회피거리','회피성능','회피술','요지부동','완강','실드','기절','독','마비','수면','열상','풍압','청각보호','내진','내니내설','내점','내서','내한','세균학','광격내성','상태내성','속성내성','항방어DOWN','불내성','물내성','번개내성','얼음내성','용내성'}
RANGED={'관통탄강화','관통탄추가','산탄강화','산탄추가','통상탄강화','통상탄추가','유탄추가','참렬탄추가','확산탄추가','폭파탄추가','반동','장전속도','장전수','속사','정밀사격','사격법','사수','강격병추가','독병추가','마비병추가','수면병추가','멸기병추가','접격병추가','폭파병추가'}
ELEMENT={'불속성공격','물속성공격','번개속공격','얼음속공격','용속성공격','속성공격','특수공격','속성해방','증폭'}
GATHER={'채집','채취','고속수집','운수','재물운','포획','관찰안','천리안','호석수집','호석왕','벌꿀','변덕','조합성공률','조합수','헌터','육식'}
PALICO={'지시','지휘','호령'}
UTILITY={'납도','고속설치','스태미나','기력회복','체술','효과지속','광역','식사','식욕','먹보','버섯섭취','피리','탑승','운반','연마사','절식','기척','강탈무효','완강','자동방어','기원','비밀공작','비전'}

def category(name):
    if name in RANGED: return '원거리'
    if name in ELEMENT: return '속성·상태'
    if name in PALICO: return '동반자'
    if name in GATHER: return '채집·보수'
    if name in DEFENSE: return '방어·생존'
    if name in ATTACK: return '공격'
    return '유틸·행동'

def composite_components(skill):
    vals=[]
    for a in skill.get('activations',[]):
        if int(a.get('points',0))<=0: continue
        desc=a.get('description') or ''
        # 복합스킬 설명은 「...」＋「...」 형태로 정리되어 있음.
        quoted=re.findall(r'「([^」]+)」',desc)
        if len(quoted)>=2:
            vals.extend(quoted)
    # 순서 보존 중복 제거
    return list(dict.fromkeys(vals))

deco_by=collections.defaultdict(list); armor_by=collections.defaultdict(list)
for d in decos:
    for sid,p in (d.get('skills') or {}).items():
        p=int(p or 0)
        if p>0:
            deco_by[sid].append({'id':d['id'],'name':d['name'],'nameJa':d.get('nameJa',''),'nameEn':d.get('nameEn',''),'slots':d.get('slots',0),'rank':d.get('rank',''),'points':p,'materials':d.get('materials','')})
for a in armors:
    for sid,p in (a.get('skills') or {}).items():
        p=int(p or 0)
        if p>0:
            armor_by[sid].append({'id':a['id'],'name':a['name'],'nameJa':a.get('nameJa',''),'nameEn':a.get('nameEn',''),'part':a.get('part',''),'hunterType':a.get('hunterType',''),'rank':a.get('rank',''),'rare':a.get('rare',0),'points':p,'materials':a.get('materials','')})

idx={'version':'0.7.7','categories':['공격','방어·생존','원거리','속성·상태','유틸·행동','채집·보수','동반자'],'items':{}}
audit=[]
for s in skills:
    sid=s['id']; comps=composite_components(s); ds=sorted(deco_by[sid],key=lambda x:(x['slots'],-x['points'],x['name'])); ars=sorted(armor_by[sid],key=lambda x:(-x['points'],x['rare'],x['name']))
    meta={'name':s['name'],'category':category(s['name']),'composite':len(comps)>=2,'components':comps if len(comps)>=2 else [],'hasDecoration':bool(ds),'decorationCount':len(ds),'armorCount':len(ars),'file':f'{sid}.json'}
    idx['items'][sid]=meta
    payload={'id':sid,**meta,'decorations':ds,'armors':ars}
    json.dump(payload,open(OUT/f'{sid}.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    audit.append({'id':sid,**meta})
json.dump(idx,open(D/'skill_reference_index.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
json.dump(audit,open(D/'skill_reference_audit.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print('skills',len(skills),'composite',sum(x['composite'] for x in audit),'no_deco',sum(not x['hasDecoration'] for x in audit))
