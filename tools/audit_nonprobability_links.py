import json,collections,pathlib
P=pathlib.Path(__file__).resolve().parent.parent; D=P/'data'
load=lambda n:json.loads((D/n).read_text())
items=load('items.json'); it=load('item_references.json')['items']; mr=load('monster_references.json'); qi=load('quest_reference_index.json')['quests']; quests=load('quests.json'); rewards=load('monster_rewards.json')
iid={x['id'] for x in items}; qid={x['id'] for x in quests}; names={x['name'] for x in items}; mn=set(mr)
issues=collections.defaultdict(list); counts=collections.Counter()
for id,ref in it.items():
 counts['item_references']+=1
 if id not in iid:issues['item_ref_unknown_id'].append(id)
 for ac in ref.get('acquire',[]):
  counts['acquire_'+str(ac.get('type'))]+=1
  if ac.get('type')=='monster' and ac.get('monster') not in mn:issues['acquire_unknown_monster'].append([id,ac.get('monster')])
  if ac.get('type')=='quest' and ac.get('questId') and ac['questId'] not in qid:issues['acquire_unknown_quest'].append([id,ac['questId']])
 for use in ref.get('uses',[]):counts['use_'+str(use.get('type'))]+=1
for m,ref in mr.items():
 counts['monster_references']+=1
 for j in ref.get('items',[]):
  counts['monster_item_links']+=1
  if j.get('id') not in iid:issues['monster_item_unknown_id'].append([m,j])
  elif not any(a.get('type')=='monster' and a.get('monster')==m for a in it.get(j['id'],{}).get('acquire',[])):
   issues['monster_item_missing_reverse'].append([m,j])
 for q in ref.get('quests',[]):
  counts['monster_quest_links']+=1
  if q.get('id') not in qid:issues['monster_quest_unknown_id'].append([m,q.get('id')])
  elif m not in [x.get('name',x) if isinstance(x,dict) else x for x in qi[q['id']].get('monsters',[])]:
   issues['monster_quest_reverse_mismatch'].append([m,q.get('id')])
for q,ref in qi.items():
 counts['quest_references']+=1
 if q not in qid:issues['quest_ref_unknown_id'].append(q)
 for r in ref.get('rewardItems',[]):
  counts['quest_reward_links']+=1
  if isinstance(r,dict):
   if r.get('id') and r['id'] not in iid:issues['quest_reward_unknown_item_id'].append([q,r])
for r in rewards:
 counts['monster_reward_source_rows']+=1
 if r['monster'] not in mn:issues['reward_unknown_monster'].append(r['monster'])
 if r['item'] not in names:issues['reward_unknown_item_name'].append([r['monster'],r['item']])
report={'scope':'non-probability internal relationship/identity checks; not independent MH4G completeness certification','counts':counts,'issueCounts':{k:len(v) for k,v in issues.items()},'issuesSample':{k:v[:30] for k,v in issues.items()}}
(P/'tools'/'nonprobability_link_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'counts':counts,'issues':report['issueCounts']},ensure_ascii=False,indent=2))
