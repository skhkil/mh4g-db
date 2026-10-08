#!/usr/bin/env python3
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]; D=P/'data'
load=lambda p: json.load(open(p,encoding='utf-8'))
def dump(o,p,compact=False):
 with open(p,'w',encoding='utf-8') as f: json.dump(o,f,ensure_ascii=False,indent=None if compact else 2,separators=(',',':') if compact else None)
quests=load(D/'quests.json'); qby={q['id']:q for q in quests}
qref=load(D/'quest_reference_index.json')
# STEP2 verified correction: this all-large-monster quest is Tetsucabra subspecies + Rathalos + Gravios, not Diablos.
fix='quest_29711c404465'
if fix in qref['quests']:
 qref['quests'][fix]['monsters']=['테츠카브라 아종','리오레우스','그라비모스']
dump(qref,D/'quest_reference_index.json')
mr=load(D/'monster_references.json')
# replace only reverse quest lists; preserve item/use relations.
for m,row in mr.items(): row['quests']=[]
for qid,r in qref['quests'].items():
 q=qby[qid]
 rec={k:q.get(k,'') for k in ['id','questType','questTypeLabel','level','name','objective','location']}
 for m in r.get('monsters',[]):
  if m not in mr: raise SystemExit(f'unknown monster {m} in {qid}')
  mr[m]['quests'].append(rec)
for row in mr.values(): row['quests'].sort(key=lambda x:(x.get('questType',''),x.get('level',''),x.get('name','')))
dump(mr,D/'monster_references.json')
idx=load(D/'monster_reference_index.json')
idx['version']='0.7.7-step2-final-xref'
for m,row in mr.items():
 meta=idx['items'][m]; meta['quests']=len(row['quests'])
 fn=meta['file']; dump(row,D/'monster_refs'/f'{fn}.json',compact=True)
dump(idx,D/'monster_reference_index.json',compact=True)
print('q->monster',sum(len(r.get('monsters',[])) for r in qref['quests'].values()))
print('monster->q',sum(len(r.get('quests',[])) for r in mr.values()))
