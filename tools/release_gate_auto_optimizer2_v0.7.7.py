#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
checks={}; errors=[]

def ok(name,cond,msg=''):
    checks[name]=bool(cond)
    if not cond: errors.append(name+((': '+msg) if msg else ''))

version='0.7.7-auto-optimizer2'
for rel in ['index.html','js/app.js','js/data-loader.js']:
    txt=(ROOT/rel).read_text(encoding='utf-8')
    ok('cache_'+rel,version in txt)

for rel in ['js/app.js','js/data-loader.js','js/engine.js']:
    r=subprocess.run(['node','--check',str(ROOT/rel)],capture_output=True,text=True)
    ok('syntax_'+rel,r.returncode==0,r.stderr.strip())

json_files={
 'optimizer_unit':'tools/step3b_optimizer_regression_v0.7.7.json',
 'optimizer_e2e':'tools/step3b_optimizer_e2e_v0.7.7.json',
 'parity_e2e':'tools/step3_auto_manual_parity_e2e_v0.7.7.json',
 'calc_audit':'tools/step3_calculation_integrity_audit_v0.7.7.json',
 'complex_audit':'tools/step3_complex_profiles_audit_v0.7.7.json',
 'rank_audit':'tools/hotfix20_auto_rank_audit_v0.7.7.json',
 'backnav':'tools/hotfix15_backnav_e2e_v0.7.7.json',
}
loaded={}
for name,rel in json_files.items():
    p=ROOT/rel
    try:
        obj=json.loads(p.read_text(encoding='utf-8')); loaded[name]=obj; ok(name,p.exists() and obj.get('ok') is True,repr(obj.get('ok')))
    except Exception as e: ok(name,False,str(e))

opt=loaded.get('optimizer_unit',{})
uk=opt.get('ukau',{})
active=set(uk.get('activated',[]))
for skill in ['심안','약점특효','회피성능+3','공격력UP【소】','예리도레벨+1','내진']:
    ok('ukau_'+skill,skill in active)
ok('ukau_remaining_slot',int(uk.get('metrics',{}).get('remainingSlots',-1))>=1)
ok('ukau_compact_deco','통격주【1】' in uk.get('decorations',[]))
ok('ukau_extra_deco','항진주【1】' in uk.get('decorations',[]))

engine=(ROOT/'js/engine.js').read_text(encoding='utf-8')
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
ok('feasibility_beam','generationFeasibility' in engine and 'useFeasibility=targetCount>=4' in engine)
ok('fast_compaction','compactDecorationPlacements' in engine)
ok('residual_optimizer','optimizeResidualDecorations' in engine)
ok('ranking_extra_before_negative',engine.find('extraPositiveSkillCount') < engine.find('negativeSkillCount',engine.find('function compareRankedMetrics')) if 'function compareRankedMetrics' in engine else False)
ok('merged_ranking_updated','extraPositiveSkillCount' in app[app.find('function compareMergedAutoResults'):app.find('function requiredCharmConditionFromNear')])

report={'version':version,'ok':not errors,'checks':checks,'errors':errors}
(ROOT/'tools'/'auto_optimizer2_release_gate_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
