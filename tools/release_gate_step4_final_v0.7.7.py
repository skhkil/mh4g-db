#!/usr/bin/env python3
from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
checks={}; details={}; errors=[]

def mark(name, ok, detail=None):
    checks[name]=bool(ok)
    if detail is not None: details[name]=detail
    if not ok: errors.append(name)

def load(name):
    return json.loads((TOOLS/name).read_text(encoding='utf-8'))

for f in ['js/app.js','js/data-loader.js','js/engine.js']:
    r=subprocess.run(['node','--check',f],cwd=ROOT,capture_output=True,text=True)
    mark('syntax_'+Path(f).stem, r.returncode==0, r.stderr.strip())

idx=(ROOT/'index.html').read_text(encoding='utf-8')
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
loader=(ROOT/'js/data-loader.js').read_text(encoding='utf-8')
key='0.7.7-step4-final-release'
mark('cache_key_index', key in idx)
mark('cache_key_app', key in app)
mark('cache_key_loader', key in loader)
mark('no_step3_probe_tmp', not (TOOLS/'step3_probe_tmp.mjs').exists())

reports={
 'step2_integrity':'step2_final_integrity_audit_v0.7.7.json',
 'step1_e2e':'step1_skill_notes_e2e_v0.7.7.json',
 'step15_e2e':'armor_monster_search_step15_e2e_v0.7.7.json',
 'step2_merge_e2e':'step2_final_merge_e2e_v0.7.7.json',
 'step2_unlock_e2e':'step2_unlock_xref_e2e_v0.7.7.json',
 'owned_rows_e2e':'owned_asset_rows_hotfix15_e2e_v0.7.7.json',
 'backnav_e2e':'hotfix15_backnav_e2e_v0.7.7.json',
 'step3_calc':'step3_calculation_integrity_audit_v0.7.7.json',
 'step3_complex':'step3_complex_profiles_audit_v0.7.7.json',
 'step3_parity':'step3_auto_manual_parity_e2e_v0.7.7.json',
 'hotfix21_runtime':'hotfix21_runtime_audit_v0.7.7.json',
 'hotfix21_complex_e2e':'hotfix21_complex_search_e2e_v0.7.7.json',
 'hotfix20_smoke':'hotfix20_auto_rank_smoke_e2e_v0.7.7.json',
 'hotfix15_navigation':'hotfix15_navigation_audit_v0.7.7.json',
}
for label,fn in reports.items():
    try:
        o=load(fn); mark(label, bool(o.get('ok')), {'file':fn,'version':o.get('version')})
    except Exception as e:
        mark(label,False,{'file':fn,'error':str(e)})

try:
    x=load('step2_final_integrity_audit_v0.7.7.json')
    invariants=(x.get('questCount')==595 and x.get('questToItem')==5539 and x.get('itemToQuest')==5539 and x.get('questToMonster')==610 and x.get('monsterToQuest')==610 and x.get('unlockForward')==232 and x.get('unlockReverse')==232 and x.get('wyporiumExchangeRows')==139 and x.get('wyporiumTargets')==139 and x.get('decorationTargets')==42 and not x.get('issues'))
    mark('step2_invariants',invariants,x)
except Exception as e: mark('step2_invariants',False,str(e))

out={'ok':not errors,'version':key,'checks':checks,'errors':errors,'details':details}
(TOOLS/'step4_final_release_gate_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
