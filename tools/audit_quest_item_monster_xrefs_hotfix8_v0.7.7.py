#!/usr/bin/env python3
from pathlib import Path
import json,collections
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
load=lambda n:json.loads((D/n).read_text(encoding='utf-8'))
qs=load('quests.json'); qby={q['id']:q for q in qs}
qref=load('quest_reference_index.json')['quests']; iref=load('item_references.json')['items']; mref=load('monster_references.json')
items=load('items.json'); iby={i['name']:i['id'] for i in items}; mons={m['name'] for m in load('monster_summary.json')}
issues=[]
# Quest -> monster and monster -> quest must be exact reverses.
rev=collections.defaultdict(set)
for qid,row in qref.items():
    if qid not in qby: issues.append({'type':'qref_missing_quest','questId':qid}); continue
    for m in row.get('monsters',[]):
        if m not in mons: issues.append({'type':'qref_missing_monster','questId':qid,'monster':m})
        rev[m].add(qid)
for m in mons:
    got={x.get('id') for x in mref.get(m,{}).get('quests',[])}
    if got!=rev[m]:
        issues.append({'type':'monster_reverse_mismatch','monster':m,'missing':sorted(rev[m]-got),'extra':sorted(got-rev[m])})
# Item -> quest links and quest -> reward items must be bidirectionally consistent.
for iid,row in iref.items():
    for a in row.get('acquire',[]):
        if a.get('type')!='quest': continue
        qid=a.get('id')
        if qid not in qby: issues.append({'type':'item_quest_missing_quest','itemId':iid,'item':row.get('name'),'questId':qid}); continue
        if row.get('name') not in qref.get(qid,{}).get('rewardItems',[]):
            issues.append({'type':'item_quest_not_in_reward_index','itemId':iid,'item':row.get('name'),'questId':qid})
for qid,row in qref.items():
    for name in row.get('rewardItems',[]):
        iid=iby.get(name)
        if not iid:
            issues.append({'type':'quest_reward_missing_item','questId':qid,'item':name}); continue
        if not any(a.get('type')=='quest' and a.get('id')==qid for a in iref.get(iid,{}).get('acquire',[])):
            issues.append({'type':'quest_reward_missing_reverse','questId':qid,'item':name,'itemId':iid})
# Known generic multi-monster quests must have explicit monster lists now.
generic=[q for q in qs if '모든 대형 몬스터' in str(q.get('objective',''))]
for q in generic:
    if not qref.get(q['id'],{}).get('monsters'):
        issues.append({'type':'generic_multi_missing_monsters','questId':q['id'],'name':q['name']})
# All shard files expected by indexes must exist.
mi=load('monster_reference_index.json').get('items',{})
for name,row in mi.items():
    if not (D/'monster_refs'/f"{row['file']}.json").exists(): issues.append({'type':'missing_monster_shard','monster':name,'file':row['file']})
ii=load('item_reference_index.json').get('items',{})
for iid in ii:
    if not (D/'item_refs'/f'{iid}.json').exists(): issues.append({'type':'missing_item_shard','itemId':iid})
report={
 'version':'hotfix8','questCount':len(qs),'monsterCount':len(mons),'indexedItemCount':len(iref),
 'questMonsterLinks':sum(len(r.get('monsters',[])) for r in qref.values()),
 'monsterQuestLinks':sum(len(r.get('quests',[])) for r in mref.values()),
 'questRewardItemLinks':sum(len(r.get('rewardItems',[])) for r in qref.values()),
 'itemQuestAcquireLinks':sum(1 for r in iref.values() for a in r.get('acquire',[]) if a.get('type')=='quest'),
 'genericMultiQuestCount':len(generic),'genericMultiMissing':sum(not qref.get(q['id'],{}).get('monsters') for q in generic),
 'issueCount':len(issues),'issues':issues}
(D/'quest_item_monster_xref_audit_hotfix8_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='issues'},ensure_ascii=False,indent=2))
if issues:
 print(json.dumps(issues[:30],ensure_ascii=False,indent=2)); raise SystemExit(1)
