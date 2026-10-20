#!/usr/bin/env python3
"""Source-coverage ledger; never mistake schema checks or MH4U correlations for MH4G verification."""
from pathlib import Path
import json,csv,collections,re
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/item_references.json').read_text(encoding='utf8'))['items']
rows=[]
for itemid,item in d.items():
 for ordinal,a in enumerate(item.get('acquire',[])):
  if a.get('type')!='monster':continue
  src=a.get('sourceUrl') or a.get('source') or ''
  is_mh4g=bool(re.search(r'(3dsmh4g|mh4info\.com|spwiki\.net/mh4g|game-cap\.com/mh4g)',src,re.I))
  # A URL alone is not evidence that all fields have actually been compared.
  rows.append({'item_id':itemid,'item_name':item['name'],'entry_index':ordinal,'monster':a.get('monster',''),'rank':a.get('rank',''),'method':a.get('method',''),'probability':a.get('probability',''),'quantity':a.get('count',''),'old_status':a.get('verificationStatus',''),'mh4g_source_url':src if is_mh4g else '', 'source_comparison':'PENDING_MANUAL_ROW_COMPARISON', 'comment':'Source attached; value-level match not yet independently reproduced' if is_mh4g else 'No item-level MH4G source attached'})
out=root/'tools/mh4g_acquisition_source_coverage.csv'
with out.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
c=collections.Counter(r['old_status'] for r in rows)
summary={'total':len(rows),'mh4g_source_attached':sum(bool(r['mh4g_source_url']) for r in rows),'independently_verified_at_row_level':0,'pending_value_level_verification':len(rows),'legacy_status_counts':dict(c),'note':'Previous status does not establish per-row MH4G verification. This audit intentionally makes no claims of game-value correctness.'}
(root/'tools/mh4g_acquisition_source_coverage.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(summary)
assert len(rows)==4481
