#!/usr/bin/env python3
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
armors=json.loads((DATA/'armors.json').read_text(encoding='utf-8'))
idx=json.loads((DATA/'armor_progression_index.json').read_text(encoding='utf-8'))
prog_dir=DATA/'armor_progressions'
errors=[]; unknown=[]; exchange_count=0; mats=0
if len(armors)!=3119: errors.append(f'armor count {len(armors)} != 3119')
if idx.get('count')!=len(armors): errors.append(f"progression index {idx.get('count')} != armor {len(armors)}")
if any('progression' in a for a in armors): errors.append('main armors.json still embeds progression')
for a in armors:
    f=prog_dir/f"{a['id']}.json"
    if not f.exists(): errors.append(f"missing progression file {a['id']} {a['name']}"); continue
    p=json.loads(f.read_text(encoding='utf-8'))
    if not p.get('materials'): errors.append(f"no materials {a['name']}"); continue
    for m in p['materials']:
        mats+=1
        if not m.get('sources'): errors.append(f"no sources {a['name']} / {m.get('name')}")
        for s in m.get('sources') or []:
            if s.get('type')=='unknown': unknown.append((a['name'],m.get('name')))
            if s.get('type')=='exchange':
                exchange_count+=1
                if not s.get('required'): errors.append(f"exchange missing required {a['name']} / {m.get('name')}")
# Explicit regression checks requested by user.
def armor(name): return next((a for a in armors if a.get('name')==name),None)
for name,required,result,unlock in [
    ('엠프러스메일','창화룡 날개','염비룡 갈기','고난도: 광기 어린 흑굉룡'),
    ('엠프러스X메일','염왕룡 중갑각','염비룡 중갑각','고난도: 지옥에서 온 숙적들'),
]:
    a=armor(name)
    if not a: errors.append(f'missing armor {name}'); continue
    p=json.loads((prog_dir/f"{a['id']}.json").read_text(encoding='utf-8'))
    found=False
    for m in p['materials']:
        for s in m.get('sources') or []:
            if m.get('name')==result and s.get('type')=='exchange' and s.get('required')==required and unlock in s.get('unlockQuest',''):
                found=True
    if not found: errors.append(f'bad empress exchange route {name}')
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
css=(ROOT/'css/app.css').read_text(encoding='utf-8')
checks={
    'all_progressions_split': idx.get('count')==3119 and len(list(prog_dir.glob('*.json')))==3119,
    'no_unknown_sources': not unknown,
    'main_armor_db_light': (DATA/'armors.json').stat().st_size < 4_000_000,
    'row_click_toggle': 'data-armor-id' in app and 'toggleArmorProgressRow' in app,
    'lazy_progression_fetch': 'loadArmorProgression' in app and 'armor-detail-host' in app,
    'full_width_detail': 'armor-detail-row' in css and 'armor-progress-material-grid' in css,
    'exchange_route_visible': '교환 재료' in app and '획득' in app,
}
for k,v in checks.items():
    if not v: errors.append('check failed: '+k)
out={
    'ok':not errors,
    'version':'0.7.7-chat4-research2-hotfix16',
    'counts':{'armors':len(armors),'progressions':idx.get('count'),'materials':mats,'exchangeSources':exchange_count,'unknownSources':len(unknown)},
    'checks':checks,'errors':errors[:100]
}
(ROOT/'tools/hotfix16_armor_progression_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
