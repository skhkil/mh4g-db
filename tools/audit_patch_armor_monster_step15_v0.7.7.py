#!/usr/bin/env python3
import json, glob, re, unicodedata
from pathlib import Path
from collections import defaultdict, Counter
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,o): Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

armors=load(D/'armors.json'); sets=load(D/'armor_sets.json'); simsets=load(D/'sim_armor_sets.json')
byid={a['id']:a for a in armors}
changes=[]
fixes={
 'armor_98bc5e6dcf0f':{'name':'모노데블암'},
 'armor_b856d3e8f8ea':{'name':'모노데블가드','nameJa':'モノデビルガード','nameEn':'Monodevil Guards'},
}
for aid,patch in fixes.items():
 a=byid[aid]
 before={k:a.get(k) for k in patch}
 a.update(patch)
 changes.append({'id':aid,'before':before,'after':patch})

# Keep every data reference displaying these armor records in sync by id.
for p in D.rglob('*.json'):
    if p.name in {'armors.json','armor_sets.json','sim_armor_sets.json'}: continue
    try:o=load(p)
    except Exception: continue
    touched=[False]
    def rec(v):
        if isinstance(v,dict):
            aid=v.get('id')
            if aid in fixes:
                for k,nv in fixes[aid].items():
                    if k in v and v.get(k)!=nv:
                        v[k]=nv; touched[0]=True
            for z in v.values(): rec(z)
        elif isinstance(v,list):
            for z in v: rec(z)
    rec(o)
    if touched[0]: dump(p,o)

# Sync full armor set pieces and repair the two set display names.
monodevil_sets=[]
for s in sets:
    for p in s.get('pieces',[]):
        if p['id'] in fixes: p['name']=fixes[p['id']]['name']
    piece_ids={p['id'] for p in s.get('pieces',[])}
    if {'armor_98bc5e6dcf0f','armor_94aadbb36d24'} & piece_ids and any(byid[p['id']].get('nameEn','').startswith('Monodevil') for p in s.get('pieces',[]) if p['id'] in byid):
        s['name']='모노데블'; monodevil_sets.append(s['id'])
    if {'armor_b856d3e8f8ea','armor_e7eabc19af79'} & piece_ids and any(byid[p['id']].get('nameEn','').startswith('Monodevil') for p in s.get('pieces',[]) if p['id'] in byid):
        s['name']='모노데블'; monodevil_sets.append(s['id'])

# Build searchable monster aliases from existing monster->armor single-source refs.
monster_meta={m['name']:m for m in load(D/'monster_summary.json')}
monster_armor={}
for p in (D/'monster_refs').glob('*.json'):
    o=load(p); monster=o.get('monster','')
    monster_armor[monster]={u.get('id') for u in o.get('uses',[]) if u.get('type')=='armor' and u.get('id')}
coverage=Counter()
for s in sets:
    ids={p['id'] for p in s.get('pieces',[])}
    linked=[mn for mn,aids in monster_armor.items() if ids and ids.issubset(aids)]
    terms=[]
    for mn in linked:
        m=monster_meta.get(mn,{})
        for t in [mn,m.get('materialName'),m.get('nameEn')]:
            if t and t not in terms: terms.append(t)
    s['monsterSearchTerms']=terms
    coverage[len(linked)]+=1

# sim set names/pieces only need display sync; no search alias payload needed.
for s in simsets:
    for p in s.get('pieces',[]):
        if p['id'] in fixes: p['name']=fixes[p['id']]['name']
    if s['id'] in set(monodevil_sets): s['name']='모노데블'

# Write primary files.
dump(D/'armors.json',armors); dump(D/'armor_sets.json',sets); dump(D/'sim_armor_sets.json',simsets)

# Audit structural integrity + normalized duplicate conceptual sets.
def norm(s): return re.sub(r'[\s·・]','',unicodedata.normalize('NFKC',s or ''))
missing_piece=[]
for s in sets:
    for p in s.get('pieces',[]):
        if p['id'] not in byid: missing_piece.append((s['id'],p['id']))
concept=defaultdict(list)
for s in sets:
    concept[(s['hunterType'],s['rank'],tuple(norm(p['name']) for p in s.get('pieces',[])))].append(s['id'])
concept_dups=[v for v in concept.values() if len(v)>1]
report={
 'version':'0.7.7-final-step1-armor-audit1',
 'scope':'monster-armor reverse tracking and armor-set search audit',
 'counts':{'armors':len(armors),'armorSets':len(sets),'monsterRefs':len(monster_armor),'monsterArmorUseRefs':sum(len(x) for x in monster_armor.values())},
 'fixes':changes,
 'monodevilSetIds':sorted(set(monodevil_sets)),
 'monsterAliasCoverage':{str(k):v for k,v in sorted(coverage.items())},
 'structural':{'missingSetPieceRefs':missing_piece,'normalizedDuplicateSetGroups':concept_dups},
 'notes':['monsterSearchTerms are derived only when all pieces in a set are present in the existing monster reference uses.']
}
dump(ROOT/'tools'/'armor_monster_step15_audit_v0.7.7.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
