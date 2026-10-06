#!/usr/bin/env python3
from pathlib import Path
import json,re,time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools'/'armor_set_resist_hotfix10_release_audit_v0.7.7.json'
issues=[]
sets=json.loads((ROOT/'data'/'armor_sets.json').read_text(encoding='utf-8'))
sim=json.loads((ROOT/'data'/'sim_armor_sets.json').read_text(encoding='utf-8'))
by={x['id']:x for x in sets}
if len(sets)!=len(sim): issues.append(f'armor set count mismatch {len(sets)} != {len(sim)}')
for x in sim:
    y=by.get(x.get('id'))
    if not y: issues.append('missing full '+str(x.get('id'))); continue
    for k in ('defense','maxDefense','resistances'):
        if x.get(k)!=y.get(k): issues.append(f'{x.get("name")}:{k} mismatch')
app=(ROOT/'js'/'app.js').read_text(encoding='utf-8')
idx=(ROOT/'index.html').read_text(encoding='utf-8')
dl=(ROOT/'js'/'data-loader.js').read_text(encoding='utf-8')
ver='0.7.7-chat4-armor-set-resist-hotfix10'
for name,text in [('index',idx),('app',app),('data-loader',dl)]:
    if ver not in text: issues.append(f'{name}:cache version missing')
for needle in ('id="armorSetSort"','화내성 높은순','용내성 높은순'):
    if needle not in idx: issues.append('index missing '+needle)
for needle in ('방어 ${Number(s.defense||0)}/${Number(s.maxDefense||s.defense||0)}','ARMOR_SET_RESIST_LABELS'):
    if needle not in app: issues.append('app missing '+needle)
e2ep=ROOT/'tools'/'armor_set_resist_hotfix10_e2e_v0.7.7.json'
try:
    e2e=json.loads(e2ep.read_text(encoding='utf-8'))
    if not e2e.get('ok'): issues.append('e2e failed')
    if e2ep.stat().st_mtime < max((ROOT/'js'/'app.js').stat().st_mtime,(ROOT/'index.html').stat().st_mtime): issues.append('e2e stale')
except Exception as e: issues.append('e2e missing '+str(e))
report={'ok':not issues,'version':ver,'armorSetCount':len(sim),'checks':{'simFieldsSynced':not any('mismatch' in x for x in issues),'cacheVersionUnified':not any('cache version' in x for x in issues),'e2e':not any(x.startswith('e2e') for x in issues)},'issues':issues}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
