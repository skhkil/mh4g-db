from pathlib import Path
import json, collections
root=Path(__file__).resolve().parents[1]
items=json.loads((root/'data/item_references.json').read_text())['items']
original=json.loads((root/'tools/item_acquisition_mh4g_crosscheck.json').read_text())
counts=collections.Counter(); records=[]
for item_id, entry in items.items():
 for idx, a in enumerate(entry.get('acquire',[])):
  if a.get('type') != 'monster': continue
  status=a.get('verificationStatus') or 'unspecified'
  counts[status]+=1
  records.append({'item_id':item_id,'item':entry.get('name'),'index':idx,'monster':a.get('monster'), 'rank':a.get('rank'), 'method':a.get('method'), 'probability':a.get('probability'), 'existing_status':status})
result={'total_monster_records':len(records),'existing_statuses':dict(counts),'mh4g_dara_subspecies_claimed_crosscheck':original.get('mh4gCrosscheckedDalamadurSubspeciesRecords'),'warning':'Status method_explicit and mh4u_correlated are NOT MH4G independent source verification. Existing MH4G 18-item claim needs unique row-by-row source anchoring.','remaining_without_proven_MH4G_full_comparison_at_least':len(records)-original.get('mh4gCrosscheckedDalamadurSubspeciesRecords',0), 'records':records}
out=root/'tools/mh4g_source_evidence_coverage_pending.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='records'},ensure_ascii=False,indent=2))
