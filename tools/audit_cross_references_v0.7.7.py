#!/usr/bin/env python3
from pathlib import Path
import json, os, collections, re
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'
load=lambda name: json.loads((D/name).read_text(encoding='utf-8'))
items=load('items.json'); weapons=load('weapons.json'); armors=load('armors.json'); armor_sets=load('armor_sets.json')
decos=load('decorations.json'); skills=load('skills.json'); quests=load('quests.json'); monsters=load('monster_summary.json')
details=load('monster_details.json'); rewards=load('monster_rewards.json'); compositions=load('compositions.json')
item_index=load('item_reference_index.json'); monster_index=load('monster_reference_index.json'); skill_index=load('skill_reference_index.json')
name_sets={
 'item':({n for x in items for n in ([x.get('name')] + list(x.get('aliases') or [])) if n}),'weapon':{x['name'] for x in weapons},'armor':{x['name'] for x in armors},
 'decoration':{x['name'] for x in decos},'quest':{x['name'] for x in quests},'monster':{x['name'] for x in monsters},
 'composition_result':{x['result'] for x in compositions}
}
skill_ids={x['id'] for x in skills}
issues=[]; warnings=[]; stats=collections.Counter()

def issue(kind,*args): issues.append({'kind':kind,'detail':list(args)})
def warning(kind,*args): warnings.append({'kind':kind,'detail':list(args)})

# Skill-ID integrity in equipment / decoration source data.
for a in armors:
 for sid in (a.get('skills') or {}):
  if sid not in skill_ids: issue('armor_missing_skill',a.get('name'),sid)
for d in decos:
 for sid in (d.get('skills') or {}):
  if sid not in skill_ids: issue('decoration_missing_skill',d.get('name'),sid)
for s in armor_sets:
 for sid in (s.get('skills') or {}):
  if sid not in skill_ids: issue('armor_set_missing_skill',s.get('name'),sid)

# Item reverse-reference shards.
for iid,meta in item_index.get('items',{}).items():
 f=D/'item_refs'/f'{iid}.json'
 if not f.exists(): issue('missing_item_ref_file',iid); continue
 r=json.loads(f.read_text(encoding='utf-8'))
 for x in r.get('acquire',[]):
  t=x.get('type'); stats[f'item.acquire.{t}']+=1
  if t=='monster' and x.get('monster') not in name_sets['monster']: issue('item_ref_bad_monster',iid,x.get('monster'))
  elif t=='quest' and x.get('name') not in name_sets['quest']: issue('item_ref_bad_quest',iid,x.get('name'))
 for x in r.get('uses',[]):
  t=x.get('type'); stats[f'item.use.{t}']+=1
  if t in ('weapon','armor','decoration') and x.get('name') not in name_sets[t]: issue(f'item_ref_bad_{t}',iid,x.get('name'))
  elif t=='compose' and x.get('result') not in name_sets['composition_result']: issue('item_ref_bad_compose',iid,x.get('result'))

# Monster reverse-reference shards.
missing_monster_materials=0; affected_monsters=0
for name,meta in monster_index.get('items',{}).items():
 f=D/'monster_refs'/meta.get('file','')
 if not f.exists(): issue('missing_monster_ref_file',name,meta.get('file')); continue
 r=json.loads(f.read_text(encoding='utf-8'))
 for q in r.get('quests',[]):
  if q.get('name') not in name_sets['quest']: issue('monster_ref_bad_quest',name,q.get('name'))
 for u in r.get('uses',[]):
  t=u.get('type')
  if t in ('weapon','armor','decoration') and u.get('name') not in name_sets[t]: issue(f'monster_ref_bad_{t}',name,u.get('name'))
 missing=[x.get('name') for x in r.get('items',[]) if re.sub(r'\s*[×xX*]\s*\d+\s*$','',str(x.get('name') or '')).strip() not in name_sets['item']]
 if missing:
  affected_monsters+=1; missing_monster_materials+=len(missing)
  warning('monster_material_not_in_item_db',name,len(missing),missing[:12])

# Skill reverse-reference shards.
for sid,meta in skill_index.get('items',{}).items():
 f=D/'skill_refs'/meta.get('file','')
 if not f.exists(): issue('missing_skill_ref_file',sid,meta.get('file')); continue
 r=json.loads(f.read_text(encoding='utf-8'))
 for d in r.get('decorations',[]):
  if d.get('name') not in name_sets['decoration']: issue('skill_ref_bad_decoration',sid,d.get('name'))
 for a in r.get('armors',[]):
  if a.get('name') not in name_sets['armor']: issue('skill_ref_bad_armor',sid,a.get('name'))

# Known cross-source naming aliases that are intentionally resolved at runtime/build time.
detail_alias={'임계 브라키디오스':'맹폭 브라키디오스','혼돈의 고어·마가라':'혼돈에 신음하는 고어·마가라','밀라보레아스':'밀라보레아스 (흑룡)','밀라보레아스 (조룡)':'밀라보레아스 (선조룡)'}
reward_alias={'오나즈치':'오오나즈치','임계 브라키디오스':'맹폭 브라키디오스','혼돈의 고어·마가라':'혼돈에 신음하는 고어·마가라'}
detail_names={x['name'] for x in details}; reward_names={x['monster'] for x in rewards}
no_reward=[]
for m in sorted(name_sets['monster']):
 dn=detail_alias.get(m,m)
 if dn not in detail_names: issue('monster_missing_hitzone_detail',m,dn)
 rn=reward_alias.get(m,m)
 if rn not in reward_names: no_reward.append(m)
if no_reward: warning('monsters_without_reward_rows',len(no_reward),no_reward)

summary={
 'version':'0.7.7-chat4-itemdb1',
 'hardIssueCount':len(issues),
 'warningCount':len(warnings),
 'itemCount':len(items),'itemIndexedCount':len(item_index.get('items',{})),
 'monsterCount':len(monsters),'monsterIndexedCount':len(monster_index.get('items',{})),
 'skillCount':len(skills),'skillIndexedCount':len(skill_index.get('items',{})),
 'monsterMaterialsMissingFromItemDb':missing_monster_materials,
 'monstersAffectedByItemCoverage':affected_monsters,
 'stats':dict(sorted(stats.items())),
 'issues':issues,'warnings':warnings,
}
(D/'xref_audit_v0.7.7.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
md=[]
md.append('# Cross-reference audit v0.7.7')
md.append('')
md.append(f'- Hard issues: **{len(issues)}**')
md.append(f'- Warnings: **{len(warnings)}**')
md.append(f'- Item refs: **{len(item_index.get("items",{}))}/{len(items)} items**')
md.append(f'- Monster refs: **{len(monster_index.get("items",{}))}/{len(monsters)} monsters**')
md.append(f'- Skill refs: **{len(skill_index.get("items",{}))}/{len(skills)} skills**')
md.append(f'- Monster materials absent from current item DB: **{missing_monster_materials} names across {affected_monsters} monsters**')
md.append('')
md.append('## Remaining data-coverage warnings')
md.append('')
md.append('- Missing monster-material item rows are kept as plain text; no fake item record/link is generated.')
md.append('- Monsters with no reward rows in the current source DB are reported but not fabricated.')
md.append('')
md.append('## Hard issues')
md.append('')
md.append('None.' if not issues else '\n'.join(f'- `{x["kind"]}`: {x["detail"]}' for x in issues))
(ROOT/'tools'/'xref_audit_v0.7.7.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['hardIssueCount','warningCount','itemIndexedCount','monsterIndexedCount','skillIndexedCount','monsterMaterialsMissingFromItemDb','monstersAffectedByItemCoverage']},ensure_ascii=False))
if issues: raise SystemExit(2)
