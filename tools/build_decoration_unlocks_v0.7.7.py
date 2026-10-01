#!/usr/bin/env python3
import json,re,glob,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
items=json.load(open(ROOT/'data/items.json',encoding='utf-8'))
decos=json.load(open(ROOT/'data/decorations.json',encoding='utf-8'))
name_to_id={x.get('name'):x.get('id') for x in items if x.get('name') and x.get('id')}
refs={}
for f in glob.glob(str(ROOT/'data/item_refs/*.json')):
    try: refs[Path(f).stem]=json.load(open(f,encoding='utf-8'))
    except Exception: pass
pat=re.compile(r'(.+?)[×*](\d+)')

def quest_key(q):
    qt=q.get('questType','')
    group={'village':0,'hub':1,'g':2,'event':3,'challenge':4}.get(qt,9)
    lv=q.get('level','')
    nums=re.findall(r'\d+',lv)
    n=int(nums[0]) if nums else 99
    return (group,n,q.get('name',''))

out={}
for d in decos:
    mats=[]
    for name,count in pat.findall(d.get('materials','')):
        name=name.strip(); iid=name_to_id.get(name); ref=refs.get(iid,{})
        acq=ref.get('acquire',[]) or []
        unlocks=[]
        quests=[]
        for a in acq:
            if a.get('unlock'):
                unlocks.append(str(a['unlock']).strip())
            if a.get('type')=='quest' and a.get('name'):
                quests.append({k:a.get(k,'') for k in ('id','name','questType','level','location','objective')})
        # stable unique
        unlocks=list(dict.fromkeys(x for x in unlocks if x))
        qseen=set(); quniq=[]
        for q in sorted(quests,key=quest_key):
            key=(q['name'],q['level'],q['questType'])
            if key in qseen: continue
            qseen.add(key); quniq.append(q)
        mats.append({'name':name,'count':int(count),'itemId':iid or '', 'unlocks':unlocks[:3], 'quests':quniq[:3]})
    out[d['id']]={'materials':mats,'hasExplicitUnlock':any(m['unlocks'] for m in mats)}
payload={
 'version':'0.7.7-chat4-decoration-unlock1',
 'generated':'2026-10-01',
 'note':'Decoration records do not contain a direct recipe-unlock field. This index connects each production material to explicit unlock notes and representative acquisition quests already verified in item references; it must not be interpreted as an invented direct recipe unlock.',
 'decorations':out
}
json.dump(payload,open(ROOT/'data/decoration_unlocks.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print('decorations',len(out),'explicit',sum(v['hasExplicitUnlock'] for v in out.values()),'with quest source',sum(any(m['quests'] for m in v['materials']) for v in out.values()))
