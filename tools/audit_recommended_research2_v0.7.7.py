import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.load(open(ROOT/'data/recommended_loadouts.json',encoding='utf-8'))
issues=[]; counts={}; evidence={}
for e in d['entries']:
 key=f"{e['weaponType']}/{e['rank']}"; counts[key]=len(e.get('variants',[]))
 for v in e.get('variants',[]):
  prefix=f"{key}/{v.get('label')}"
  for fld in ('recommendedDecorations','talismanGuide','talismanSocketGuide','decorationPlacementExample','finalSkillsExample','usageGuide','exampleEvidence'):
   if not v.get(fld): issues.append(f'{prefix}: {fld} 누락')
  evidence[v.get('exampleEvidence','')]=evidence.get(v.get('exampleEvidence',''),0)+1
  # explicit decoration placements fit their container capacities
  b=v.get('build',{}); caps={a['part']:int(a.get('slots',0)) for a in b.get('armors',[])}
  used={k:0 for k in caps}
  decos={x['id']:x for x in json.load(open(ROOT/'data/decorations.json',encoding='utf-8'))}
  for x in b.get('decorationPlacements',[]):
   if x.get('container') in caps and x.get('id') in decos: used[x['container']]+=int(decos[x['id']]['slots'])
  for k,n in used.items():
   if n>caps[k]: issues.append(f'{prefix}: {k} 장식주 슬롯 초과 {n}>{caps[k]}')
# direct-source correction
for e in d['entries']:
 if e['rank']=='low' and e['hunterType']=='blade' and any(v.get('label')=='람포스 세트' for v in e.get('variants',[])):
  issues.append(f"{e['weaponType']}/low: 국내 하위 원문 직접 근거 없는 람포스 잔존")
out={'entries':len(d['entries']),'cards':sum(counts.values()),'counts':counts,'evidenceCounts':evidence,'issues':issues,'allRequiredGuidesPresent':not issues}
(ROOT/'tools/recommended_loadouts_research2_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
