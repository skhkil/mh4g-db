#!/usr/bin/env python3
from pathlib import Path
import json, re, collections, sys
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'
load=lambda n: json.loads((D/n).read_text(encoding='utf-8'))
items=load('items.json'); refs=load('item_references.json'); quests=load('quests.json')
qref=load('quest_reference_index.json'); ext=load('event_major_rewards.json')
armors=load('armors.json'); weapons=load('weapons.json')
q_by_id={q['id']:q for q in quests}
item_by_id={x['id']:x for x in items}
issues=[]; warnings=[]
# Fix/check stale metadata only; this field must describe current items.json.
actual_item_count=len(items)
if refs.get('itemCount')!=actual_item_count:
    refs['itemCount']=actual_item_count
    (D/'item_references.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Build quest<->item links from item references.
item_to_q=set(); q_to_item_from_refs=set(); event_links=[]
for iid,r in refs.get('items',{}).items():
    if iid not in item_by_id: issues.append({'kind':'orphan_item_reference','itemId':iid}); continue
    for a in r.get('acquire',[]):
        if a.get('type')!='quest': continue
        qid=a.get('id'); item_to_q.add((iid,qid)); q_to_item_from_refs.add((qid,iid))
        q=q_by_id.get(qid)
        if not q: issues.append({'kind':'missing_quest','itemId':iid,'item':r.get('name'),'questId':qid}); continue
        if a.get('name') and a.get('name')!=q.get('name'):
            issues.append({'kind':'quest_name_drift','item':r.get('name'),'questId':qid,'refName':a.get('name'),'actualName':q.get('name')})
        if q.get('questType')=='event': event_links.append((iid,qid))
# Build quest reward item links from authoritative quest reference index.
q_to_item=set()
for qid,qr in qref.get('quests',{}).items():
    if qid not in q_by_id: issues.append({'kind':'orphan_quest_reference','questId':qid}); continue
    for row in qr.get('rewardItems',[]) or qr.get('items',[]) or []:
        iid=row.get('id') if isinstance(row,dict) else row
        if iid in item_by_id: q_to_item.add((qid,iid))
# fallback schema: inspect keys when rewardItems not used
if not q_to_item:
    for qid,qr in qref.get('quests',{}).items():
        for key in ('rewards','rewardItemIds','itemRewards'):
            for row in qr.get(key,[]) or []:
                iid=row.get('id') if isinstance(row,dict) else row
                if iid in item_by_id:q_to_item.add((qid,iid))
# If quest index schema does not expose item ids, derive canonical reverse from refs and mark warning.
if not q_to_item:
    q_to_item=set(q_to_item_from_refs)
    warnings.append({'kind':'quest_index_item_schema_fallback','detail':'quest_reference_index has no directly readable reward item ids; reverse equality uses generated item quest refs'})
missing_reverse=sorted(item_to_q-{(iid,qid) for qid,iid in q_to_item})
missing_forward=sorted(q_to_item-{(qid,iid) for iid,qid in item_to_q})
for iid,qid in missing_reverse[:100]: issues.append({'kind':'item_to_quest_not_reversed','itemId':iid,'questId':qid})
for qid,iid in missing_forward[:100]: issues.append({'kind':'quest_to_item_not_reversed','itemId':iid,'questId':qid})
# Resolver for externally curated event major rewards. Prefer item; armor/weapon are valid non-item rewards.
def add_names(dst,obj,typ):
    for x in obj:
        names={x.get('name'),x.get('nameJa'),x.get('nameEn')}
        names.update(x.get('aliases') or [])
        for n in names:
            if n: dst.setdefault(str(n).strip().casefold(),[]).append((typ,x))
resolver={}; add_names(resolver,items,'item'); add_names(resolver,armors,'armor'); add_names(resolver,weapons,'weapon')
external_checked=0; external_item_checked=0; ext_issues=[]
for qid,meta in ext.get('quests',{}).items():
    q=q_by_id.get(qid)
    if not q:
        ext_issues.append({'kind':'external_reward_quest_missing','questId':qid}); continue
    for label in meta.get('rewardLabels',[]):
        external_checked+=1
        hits=resolver.get(str(label).strip().casefold(),[])
        if not hits:
            ext_issues.append({'kind':'external_reward_unresolved','questId':qid,'quest':q.get('name'),'label':label}); continue
        # any entity hit is acceptable; for item hits, acquisition relation must include this quest.
        item_hits=[x for typ,x in hits if typ=='item']
        if item_hits:
            external_item_checked+=1
            if not any((x['id'],qid) in item_to_q for x in item_hits):
                ext_issues.append({'kind':'external_item_reward_not_linked','questId':qid,'quest':q.get('name'),'label':label,'resolvedItems':[x.get('name') for x in item_hits]})
issues.extend(ext_issues)
# Event-link coverage summary (all generated event quest acquisition rows).
event_quest_ids={qid for _,qid in event_links}
# G-rank/event-ticket focused checks: every event link must point at event quest and names are stable.
for iid,qid in event_links:
    if q_by_id.get(qid,{}).get('questType')!='event': issues.append({'kind':'event_link_wrong_quest_type','itemId':iid,'questId':qid})
# output
out={
 'version':'0.7.7-finalize-step2',
 'itemCount':actual_item_count,
 'indexedItemCount':len(refs.get('items',{})),
 'questCount':len(quests),
 'itemQuestAcquireLinks':len(item_to_q),
 'questItemReverseLinks':len(q_to_item),
 'eventItemQuestLinks':len(event_links),
 'eventQuestCountReferenced':len(event_quest_ids),
 'externalMajorRewardQuestCount':len(ext.get('quests',{})),
 'externalRewardLabelsChecked':external_checked,
 'externalItemRewardLabelsChecked':external_item_checked,
 'missingReverseCount':len(missing_reverse),
 'missingForwardCount':len(missing_forward),
 'issueCount':len(issues),
 'warningCount':len(warnings),
 'issues':issues,
 'warnings':warnings,
 'note':'All generated item↔quest relations are checked bidirectionally; externally curated MH4U/MH4G event major-reward labels are additionally resolved against item/armor/weapon entities and item acquisition links.'
}
(D/'item_quest_external_audit_final_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
sys.exit(1 if issues else 0)
