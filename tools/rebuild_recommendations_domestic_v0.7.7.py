import json, math, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
load=lambda n: json.loads((ROOT/'data'/n).read_text())
skills=load('skills.json'); sets=load('armor_sets.json'); armors=load('armors.json'); rec=load('recommended_loadouts.json')
skill_by_id={s['id']:s for s in skills}; armor_by_id={a['id']:a for a in armors}
RANGED={'라이트보우건','헤비보우건','활'}
DOM_LOW={'type':'국내 진행 참고','title':'몬헌4 장비 선택 조언','url':'https://www.inven.co.kr/board/mhf/1755/8390','note':''}
DOM_G={'type':'국내 4G 참고','title':'[4G] G급 추천 방어구','url':'https://www.inven.co.kr/board/mhf/3746/393','note':''}
DOM_IG={'type':'국내 4G 참고','title':'[4G] 조충곤 엽충 육성','url':'https://www.inven.co.kr/board/mhf/3746/314','note':''}
DOM_WEAPON={'type':'국내 무기 참고','title':'초보의 무기 선택시 팁','url':'https://www.inven.co.kr/board/mhf/3746/159','note':''}
DOM_GUNNER={'type':'국내 무기 참고','title':'초보의 무기 선택시 팁','url':'https://www.inven.co.kr/board/mhf/3746/166','note':''}

def activated(points):
    out=[]
    for sid,val in (points or {}).items():
        s=skill_by_id.get(sid)
        if not s: continue
        ok=[a for a in s.get('activations',[]) if int(a.get('points',0))>0 and int(a.get('points',0))<=int(val or 0)]
        if ok:
            a=max(ok,key=lambda x:int(x['points']))
            out.append({'skillId':sid,'name':a['name'],'points':int(val or 0)})
    return sorted(out,key=lambda x:x['name'])

def set_score(st, targets, mode):
    score=0.0
    for t in targets:
        req=max(1,int(t.get('points',10) or 10)); p=max(0,int(st.get('skills',{}).get(t.get('skillId'),0) or 0))
        score += min(1.0,p/req)*85
    score += len(activated(st.get('skills',{})))*10
    score += int(st.get('slots',0) or 0)*(2 if mode=='balance' else 1)
    defense=int(st.get('defense',0) or 0)
    if mode=='defense':
        score += defense*.45 + sum(max(0,int(v or 0)) for v in st.get('resistances',{}).values())*.8
    elif mode=='attack': score += defense*.08
    else: score += defense*.20
    score -= sum(1 for v in st.get('skills',{}).values() if int(v or 0)<=-10)*20
    return score

def set_build(st):
    pieces=[]
    for p in st.get('pieces',[]):
        a=armor_by_id.get(p['id'])
        if not a: continue
        pieces.append({k:a.get(k) for k in ['id','name','part','defense','slots','rank','rare','materials']})
    return {'armors':pieces,'decorations':[],'defense':int(st.get('defense',0) or 0),'resist':st.get('resistances',{}),'activated':activated(st.get('skills',{})),'score':0,'craftPenalty':0}

def pick_set(weapon,stage,targets,mode,used):
    hunter='gunner' if weapon in RANGED else 'blade'
    pool=[s for s in sets if s.get('rank')==stage and s.get('hunterType') in ('both',hunter) and len(s.get('pieces',[]))==5]
    ranked=sorted(pool,key=lambda s:set_score(s,targets,mode),reverse=True)
    # keep three cards distinct if possible
    for s in ranked:
        if s['id'] not in used: return s
    return ranked[0] if ranked else None

def domestic_g_source(weapon, oldcat):
    if oldcat and ('커뮤니티' not in oldcat): return {'type':'프로젝트 커스텀','title':'','url':'','note':''}
    if weapon=='조충곤': return DOM_IG.copy()
    if weapon in RANGED: return (DOM_G if weapon=='헤비보우건' else DOM_GUNNER).copy()
    if weapon in {'대검','랜스','건랜스'}: return DOM_G.copy()
    return DOM_G.copy()

for e in rec['entries']:
    weapon=e['weaponType']; stage=e['rank']
    if stage in ('low','high'):
        original=e.get('variants',[])[:3]
        used=set(); setvars=[]; custom=[]
        modes=['attack','defense','balance']
        labels=['공격형','방어형','균형형']
        for i,(v,mode,label) in enumerate(zip(original,modes,labels)):
            st=pick_set(weapon,stage,v.get('targets',[]),mode,used)
            if st:
                used.add(st['id'])
                setvars.append({'label':f'{label} 세트','group':'set','category':mode,'description':'','targets':v.get('targets',[]),'build':set_build(st),'source':DOM_LOW.copy(),'relaxed':[],'setName':st['name']})
            cv=dict(v); cv['label']=f'{label} 커스텀'; cv['group']='custom'; cv['category']=mode; cv['description']=''; cv['source']={'type':'프로젝트 커스텀','title':'','url':'','note':''}
            custom.append(cv)
        e['variants']=setvars+custom
    else:
        for v in e.get('variants',[]):
            v['group']='g'; v['description']=''
            v['source']=domestic_g_source(weapon,v.get('category',''))

rec['method']='국내 MH4/4G 커뮤니티 자료와 프로젝트 DB를 기준으로 구성.'
rec['progressionNote']=''
rec['sources']={
  'domestic_progression':DOM_LOW,
  'domestic_g':DOM_G,
  'domestic_weapon_blade':DOM_WEAPON,
  'domestic_weapon_gunner':DOM_GUNNER,
  'domestic_ig':DOM_IG,
}
rec['generatedAt']='2026-09-18T00:00:00+09:00'
(ROOT/'data'/'recommended_loadouts.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2))
# audit
summary={'entries':len(rec['entries']),'variants':sum(len(e.get('variants',[])) for e in rec['entries']),'lowHigh':{},'g':{}}
for e in rec['entries']:
    if e['rank'] in ('low','high'):
        summary['lowHigh'][f"{e['weaponType']}:{e['rank']}"]={'set':sum(v.get('group')=='set' for v in e['variants']),'custom':sum(v.get('group')=='custom' for v in e['variants'])}
    else: summary['g'][e['weaponType']]=len(e['variants'])
(ROOT/'tools'/'recommended_loadouts_domestic_redesign_audit_v0.7.7.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({'entries':summary['entries'],'variants':summary['variants'],'badLowHigh':[k for k,v in summary['lowHigh'].items() if v!={'set':3,'custom':3}],'gCounts':sorted(set(summary['g'].values()))},ensure_ascii=False))
