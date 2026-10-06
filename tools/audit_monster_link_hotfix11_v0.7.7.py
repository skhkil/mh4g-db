#!/usr/bin/env python3
from pathlib import Path
import json,re,collections,sys
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
load=lambda n:json.loads((D/n).read_text(encoding='utf-8'))
qs=load('quests.json'); qby={q['id']:q for q in qs}; mons=load('monster_summary.json'); names={m['name'] for m in mons}
qidx=load('quest_reference_index.json')['quests']; mref=load('monster_references.json')
issues=[]; checks=[]
def check(cond,name,detail=None):
 checks.append({'name':name,'ok':bool(cond),'detail':detail})
 if not cond: issues.append({'name':name,'detail':detail})
# Structural reverse identity.
fwd={(qid,m) for qid,row in qidx.items() for m in row.get('monsters',[])}
rev={(q.get('id'),m) for m,row in mref.items() for q in row.get('quests',[])}
check(fwd==rev,'forward_reverse_exact_inverse',{'forward':len(fwd),'reverse':len(rev),'missingReverse':list(fwd-rev)[:20],'extraReverse':list(rev-fwd)[:20]})
check(not [(qid,m) for qid,m in fwd if m not in names],'all_linked_monsters_are_canonical')
check(not [m for m in names if not mref.get(m,{}).get('quests')],'all_76_monsters_have_quest_links')
# Project event corpus coverage.
event_ids=[q['id'] for q in qs if q.get('questType')=='event']
check(len(event_ids)==97,'event_quest_count_97',len(event_ids))
# Known external corrections from bd4/monster-hunter-scripts db/delta/quest-monsters.csv.
known={
 'event-high-029':['리오레우스 희소종'],   # Tower of Trouble: missing Silver Rathalos in upstream DB
 'event-high-030':['리오레이아 희소종'],   # Royal Restoration: missing Gold Rathian in upstream DB
 'event-episodic-081':['셀레기오스'],       # Bonus: A Bigger Boat: Gold Rathian should not be there
}
for qid,want in known.items():
 got=qidx.get(qid,{}).get('monsters',[])
 check(got==want,f'known_external_correction_{qid}',{'quest':qby.get(qid,{}).get('name'),'expected':want,'actual':got})
# Silver Rathalos G-event regression reported by user.
check('event-g-062' in {q['id'] for q in mref['리오레우스 희소종']['quests']},'silver_rathalos_has_g_event', [q['name'] for q in mref['리오레우스 희소종']['quests']])
check(qidx['event-g-062']['monsters']==['리오레우스 희소종'],'silver_g_event_targets_only_silver_rathalos',qidx['event-g-062']['monsters'])
# Sub-target base-name leakage regression: All The Rage is Furious Rajang only.
check(qidx['event-high-026']['monsters']==['격앙 라잔'],'furious_rajang_subtarget_does_not_add_base_rajang',qidx['event-high-026']['monsters'])
# Ensure no shard/index mismatch.
mi=load('monster_reference_index.json').get('items',{})
missing=[]; badcounts=[]
for m in names:
 meta=mi.get(m)
 if not meta: missing.append((m,'index')); continue
 f=D/'monster_refs'/f"{meta['file']}.json"
 if not f.exists(): missing.append((m,str(f))); continue
 row=json.loads(f.read_text(encoding='utf-8'))
 if len(row.get('quests',[]))!=len(mref[m].get('quests',[])): badcounts.append((m,len(row.get('quests',[])),len(mref[m].get('quests',[]))))
check(not missing,'all_monster_shards_exist',missing[:20])
check(not badcounts,'monster_shards_match_monolithic_counts',badcounts[:20])
# Rank/type coverage stats for visibility audit.
bytype=collections.Counter()
for m,row in mref.items():
 for q in row.get('quests',[]): bytype[q.get('questType')]+=1
report={'version':'0.7.7-chat4-monster-link-hotfix11','questCount':len(qs),'monsterCount':len(names),'forwardLinks':len(fwd),'reverseLinks':len(rev),'eventQuestCount':len(event_ids),'monsterQuestLinksByType':dict(bytype),'checkCount':len(checks),'issueCount':len(issues),'checks':checks,'issues':issues}
(D/'monster_link_audit_hotfix11_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['questCount','monsterCount','forwardLinks','reverseLinks','eventQuestCount','monsterQuestLinksByType','checkCount','issueCount']},ensure_ascii=False,indent=2))
if issues: sys.exit(1)
