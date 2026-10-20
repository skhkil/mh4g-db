from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/item_references.json').read_text())['items']
counts={};invalid=[];missing=[];malformed=[];first={}
for k,v in d.items():
 shard=root/'data/item_refs'/f'{k}.json'
 if shard.exists():
  ref=json.loads(shard.read_text());
  if ref.get('acquire')!=v.get('acquire'):invalid.append(k)
 for a in v.get('acquire',[]):
  if a.get('type')!='monster':continue
  cat=a.get('acquisitionCategory');counts[cat]=counts.get(cat,0)+1
  first.setdefault(cat,{'item_id':k,'name':v['name'],'method':a['method']})
  if not a.get('verificationStatus'):missing.append(k)
  if a.get('probability') and not re.fullmatch(r'(?:100|\d{1,2})(?:\.\d+)?%',a['probability']):malformed.append((k,a['probability']))
result={'total':sum(counts.values()),'categories':counts,'examples':first,'shardMismatch':invalid,'missingVerification':missing,'malformedProbabilities':malformed}
(root/'tools/item_acquisition_full_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('examples',)},ensure_ascii=False))
assert result['total']==4481 and not invalid and not missing and not malformed
