#!/usr/bin/env python3
"""Build per-monster reverse references for MH4G DB v0.7.7.

Inputs: monster_summary.json, monster_rewards.json, quests.json, weapons.json,
armors.json, decorations.json. Output: monster_reference_index.json and
monster_refs/*.json. Only monster-specific reward materials are used for gear
reverse references, preventing common ores/bones/etc. from polluting results.
"""
from pathlib import Path
import collections, json, re
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
load=lambda n: json.loads((D/n).read_text(encoding='utf-8'))
mons=load('monster_summary.json'); rewards=load('monster_rewards.json'); quests=load('quests.json')
weapons=load('weapons.json'); armors=load('armors.json'); decos=load('decorations.json'); items=load('items.json')
names=[m['name'] for m in mons]; item_ids={x['name']:str(x['id']) for x in items}
SOURCE_TO_CANONICAL={'오오나즈치':'오나즈치','맹폭 브라키디오스':'임계 브라키디오스','혼돈에 신음하는 고어·마가라':'혼돈의 고어·마가라','밀라보레아스 (흑룡)':'밀라보레아스','밀라보레아스 (선조룡)':'밀라보레아스 (조룡)'}
CANONICAL_TO_SOURCE=collections.defaultdict(list)
for src,canon in SOURCE_TO_CANONICAL.items(): CANONICAL_TO_SOURCE[canon].append(src)
def canonical_monster(name): return SOURCE_TO_CANONICAL.get(str(name or '').strip(),str(name or '').strip())
def clean(s): return re.sub(r'\s*[×x*]\s*\d+\s*$','',str(s or '')).strip()
def norm(s): return re.sub(r'\s+','',clean(s))
def parse(text): return [(m.group(1).strip(),int(m.group(2))) for m in re.finditer(r'([^×*]+?)[×*]\s*(\d+)(?=\s|$)',str(text or ''))]
reward_by=collections.defaultdict(set)
for r in rewards:
    canon=canonical_monster(r.get('monster'))
    if canon in names and clean(r.get('item')): reward_by[canon].add(clean(r['item']))
quests_by=collections.defaultdict(list)
for q in quests:
    hay=' '.join(str(q.get(k,'') or '') for k in ['name','nameJa','objective','subObjective','note'])
    candidates=[]
    for n in names:
        labels=[n]+CANONICAL_TO_SOURCE.get(n,[])
        if any(label and label in hay for label in labels): candidates.append(n)
    hits=[n for n in candidates if not any(n!=m and n in m for m in candidates)]
    for n in hits:
        quests_by[n].append({k:q.get(k) for k in ['id','questType','questTypeLabel','level','name','objective','location']})
gear=[]
for w in weapons:
    for c in w.get('craft') or []:
        mats=parse(c.get('materials'))
        if mats: gear.append({'type':'weapon','id':w.get('id'),'name':w.get('name'),'weaponType':w.get('weaponType'),'method':c.get('method'),'mats':mats})
for a in armors:
    mats=parse(a.get('materials'))
    if mats: gear.append({'type':'armor','id':a.get('id'),'name':a.get('name'),'part':a.get('part'),'hunterType':a.get('hunterType'),'mats':mats})
for d in decos:
    mats=parse(d.get('materials'))
    if mats: gear.append({'type':'decoration','id':d.get('id'),'name':d.get('name'),'slots':d.get('slots'),'mats':mats})
manual={'도스람포스':['람포스'],'도스게네포스':['게네포스'],'도스이오스':['이오스'],'푸루푸루':['알비노','물컹물컹','진주색','푸루푸루'],'푸루푸루 아종':['알비노','물컹물컹','진주색','푸루푸루'],'키린':['환수','키린'],'키린 아종':['환수','키린']}
out=D/'monster_refs'; out.mkdir(exist_ok=True); index={}; fallback={}
for m in mons:
    title=(m.get('materialName') or '').strip(); keywords=[title] if title and title!='-' else manual.get(m['name'],[])
    specific=sorted(i for i in reward_by[m['name']] if any(k and k in i for k in keywords)); wanted={norm(i):i for i in specific}; uses=[]
    for g in gear:
        via=sorted({wanted[norm(mat)] for mat,_ in g['mats'] if norm(mat) in wanted})
        if via:
            u={k:v for k,v in g.items() if k!='mats'}; u['viaItems']=via; uses.append(u)
    src=[{'name':i,'id':item_ids.get(i) or item_ids.get(i.replace(' ','')) or ''} for i in specific]
    payload={'monster':m['name'],'items':src,'quests':quests_by[m['name']],'uses':uses}
    fallback[m['name']]=payload
    fname=re.sub(r'[^a-z0-9_-]+','-',m['id'].lower())+'.json'; (out/fname).write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    index[m['name']]={'file':fname,'quests':len(payload['quests']),'uses':len(uses),'items':len(src)}
(D/'monster_reference_index.json').write_text(json.dumps({'version':'0.7.7-chat4-xrefaudit1','items':index},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(D/'monster_references.json').write_text(json.dumps(fallback,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(f"monster refs: {len(index)}")
