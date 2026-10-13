#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
checks={}; errors=[]
def ck(name, cond, detail=''):
    checks[name]=bool(cond)
    if not cond: errors.append(name+(f': {detail}' if detail else ''))
version='0.7.7-relic-guide1'
for rel in ['index.html','js/app.js','js/data-loader.js']:
    txt=(ROOT/rel).read_text(encoding='utf-8'); ck('cache_'+rel,version in txt)
for rel in ['js/app.js','js/data-loader.js','js/engine.js']:
    r=subprocess.run(['node','--check',str(ROOT/rel)],capture_output=True,text=True); ck('syntax_'+rel,r.returncode==0,r.stderr.strip())
for name,rel in {
 'relic_audit':'tools/relic_guide_audit_v0.7.7.json',
 'relic_e2e':'tools/relic_guide_e2e_v0.7.7.json',
 'optimizer_e2e':'tools/step3b_optimizer_e2e_v0.7.7.json',
 'backnav':'tools/hotfix15_backnav_e2e_v0.7.7.json',
}.items():
    p=ROOT/rel
    try:
        obj=json.loads(p.read_text(encoding='utf-8')); ck(name,obj.get('ok') is True,repr(obj.get('ok')))
    except Exception as e: ck(name,False,str(e))
readme=(ROOT/'README.md').read_text(encoding='utf-8')
ck('readme_top',readme.startswith('> **2026-10-13 · 발굴장비 카테고리 추가'))
ck('data_exists',(ROOT/'data/relic_equipment.json').exists())
try:
    d=json.loads((ROOT/'data/relic_equipment.json').read_text(encoding='utf-8'))
    ck('groups_11',len(d.get('sealedGroups',[]))==11)
    ck('weapon_types_14',len(d.get('weaponAppearances',{}))==14)
    ck('armor_groups_11',len(d.get('armorAppearancePools',{}))==11)
except Exception as e: ck('data_json',False,str(e))
report={'version':version,'ok':not errors,'checks':checks,'errors':errors}
(ROOT/'tools/relic_guide_release_gate_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2)); sys.exit(0 if report['ok'] else 1)
