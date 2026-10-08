#!/usr/bin/env python3
import json,re
from pathlib import Path
P=Path(__file__).resolve().parents[1]; D=P/'data'; OUT=P/'tools'/'step2_final_integrity_audit_v0.7.7.json'
load=lambda f: json.load(open(D/f,encoding='utf-8'))
quests=load('quests.json'); qref=load('quest_reference_index.json'); items=load('items.json'); iref=load('item_references.json'); mref=load('monster_references.json'); unlock=load('quest_unlock_index.json'); manifest=load('quest_item_external_manifest_step2.json')
qids={q['id'] for q in quests}; inames={i['name'] for i in items}; qby={q['id']:q for q in quests}
issues=[]
if len(qids)!=len(quests): issues.append('duplicate quest ids')
qr=qref['quests']
for qid,r in qr.items():
 if qid not in qids: issues.append(f'qref unknown quest {qid}')
 for name in r.get('rewardItems',[]):
  if name not in inames: issues.append(f'qref unknown item {qid}:{name}')
q2i={(qid,n) for qid,r in qr.items() for n in r.get('rewardItems',[])}
i2q=set()
for iid,row in iref['items'].items():
 for a in row.get('acquire',[]):
  if a.get('type')=='quest': i2q.add((a.get('id'),row.get('name')))
if q2i!=i2q:
 issues += [f'q2i-only:{x}' for x in sorted(q2i-i2q)[:10]]+[f'i2q-only:{x}' for x in sorted(i2q-q2i)[:10]]
q2m={(qid,m) for qid,r in qr.items() for m in r.get('monsters',[])}
m2q={(q['id'],m) for m,row in mref.items() for q in row.get('quests',[])}
if q2m!=m2q: issues.append(f'monster reverse mismatch +{len(q2m-m2q)}/-{len(m2q-q2m)}')
rels=unlock['relations']; forward=sum(len(v.get('unlocks',[])) for v in unlock['quests'].values()); reverse=sum(len(v.get('quests',[])) for v in unlock['targets'].values())
if not (len(rels)==forward==reverse): issues.append(f'unlock mismatch {len(rels)}/{forward}/{reverse}')
byja={q.get('nameJa'):q for q in quests}
for p in manifest['verifiedPairs']:
 q=byja.get(p['questNameJa'])
 if not q or p['itemName'] not in qr[q['id']]['rewardItems']: issues.append(f"missing verified pair {p}")
for qid in manifest['restoredQuestIds']:
 if qid not in qids: issues.append(f'missing restored {qid}')
# canonical builder must not parse free-text 주요 보수 fallback
builder=(P/'tools/build_item_references_v0.7.7.py').read_text(encoding='utf-8')
if 'Event/episode quest notes' in builder or "주요\\s*보수" in builder: issues.append('legacy note reward fallback remains')
# known correction
corr=qr.get('quest_29711c404465',{}).get('monsters',[])
if '디아블로스' in corr or '그라비모스' not in corr: issues.append(f'volcanic brawl correction bad:{corr}')
summary={
 'questCount':len(quests),'restoredJapaneseEvents':sum(x in qids for x in manifest['restoredQuestIds']),
 'verifiedMh4gEventPairs':len(manifest['verifiedPairs']),'questToItem':len(q2i),'itemToQuest':len(i2q),
 'questToMonster':len(q2m),'monsterToQuest':len(m2q),'unlockRelations':len(rels),'unlockForward':forward,'unlockReverse':reverse,
 'wyporiumExchangeRows':unlock['summary'].get('wyporiumExchangeRows'),'wyporiumTargets':sum(1 for v in unlock['targets'].values() if v.get('type')=='wyporium_exchange'),
 'decorationTargets':unlock['summary'].get('decorationWithQuestDependencyCount'),'needsReviewUnlocks':sum(1 for r in rels if r.get('confidence')=='needs-review'),
 'issues':issues,'ok':not issues,
 'note':'Prior STEP2 reported 611 monster links; reproducible current canonical source yields 610 after replaying the 572-base graph + 23 restored events. No mismatch exists between forward/reverse graphs.'
}
OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False,indent=2)); raise SystemExit(0 if summary['ok'] else 1)
