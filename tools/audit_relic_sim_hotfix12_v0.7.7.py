#!/usr/bin/env python3
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
version='0.7.7-chat4-relic-sim-hotfix12'
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
loader=(ROOT/'js/data-loader.js').read_text(encoding='utf-8')
index=(ROOT/'index.html').read_text(encoding='utf-8')
relic=json.loads((ROOT/'data/relic_weapon_decorations.json').read_text(encoding='utf-8'))
skillref=json.loads((ROOT/'data/skill_reference_index.json').read_text(encoding='utf-8'))['items']
normal=json.loads((ROOT/'data/decorations.json').read_text(encoding='utf-8'))
errs=[]
for d in relic:
    if not d.get('relicOnly') or not d.get('fixedDecoration'): errs.append('non-relic flag:'+d.get('id',''))
    if len(d.get('skills',{}))!=1: errs.append('relic skill count:'+d.get('id',''))
    for sid in d.get('skills',{}):
        if not skillref.get(sid,{}).get('composite'): errs.append('non-composite relic skill:'+sid)
    if int(d.get('slots',0)) not in (1,2,3): errs.append('bad relic slots:'+d.get('id',''))
normal_ids={d.get('id') for d in normal}; relic_ids={d.get('id') for d in relic}
if normal_ids & relic_ids: errs.append('relic id collision')
checks={
 'relicDecorationCount':len(relic),
 'relicSkillFamilies':len({next(iter(d['skills'])) for d in relic}),
 'slotCounts':{str(s):sum(1 for d in relic if d.get('slots')==s) for s in (1,2,3)},
 'versionApp':version in app,'versionLoader':version in loader,'versionIndex':version in index,
 'simLoadsSkillReference':bool(re.search(r'const SIMULATOR_FILES = \{[\s\S]*?skillReferenceIndex:"\.\/data\/skill_reference_index\.json"',loader)),
 'simLoadsRelicDecorations':'relicWeaponDecorations:"./data/relic_weapon_decorations.json"' in loader,
 'targetCompositeFilter':'id="targetSkillTypeFilter"' in index and 'value="composite"' in index,
 'targetRelicSlotFilter':'id="targetRelicSlotFilter"' in index and all(f'value="{s}"' in index for s in (1,2,3)),
 'manualModeFilter':'manualWeaponModeFilter' in app and 'value="relic"' in app,
 'relicWeaponFixed':'__relic_weapon__' in app and 'name:"발굴무기"' in app,
 'relicExactSlotPicker':'relicWeaponMode?Number(d.slots||0)===relicSlots' in app,
 'questCorpusCache':'questSearchCorpusCache' in app and 'function questSearchCorpus(q)' in app,
 'questIMEGuard':'oncompositionstart' in app and 'oncompositionend' in app and 'e.isComposing' in app,
 'questDebounce90':'scheduleQuestRender(90)' in app,
}
for k,v in checks.items():
    if isinstance(v,bool) and not v: errs.append(k)
out={'ok':not errs,'version':version,'checks':checks,'errors':errs}
(ROOT/'tools/relic_sim_hotfix12_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
