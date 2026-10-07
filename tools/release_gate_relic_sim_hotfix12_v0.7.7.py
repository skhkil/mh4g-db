#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'tools'; D=ROOT/'data'; VERSION='0.7.7-chat4-relic-sim-hotfix12'
issues=[]; checks={}
def ok(name,cond,detail=None):
    checks[name]={'ok':bool(cond),'detail':detail}
    if not cond: issues.append({'name':name,'detail':detail})
for f in ['js/app.js','js/data-loader.js','js/engine.js']:
    r=subprocess.run(['node','--check',str(ROOT/f)],capture_output=True,text=True)
    ok('syntax:'+f,r.returncode==0,(r.stderr or r.stdout).strip())
for f in ['index.html','js/app.js','js/data-loader.js']:
    s=(ROOT/f).read_text(encoding='utf-8');ok('cache:'+f,VERSION in s)
# current feature audits
for name,path in [
 ('feature_audit',T/'relic_sim_hotfix12_audit_v0.7.7.json'),
 ('feature_e2e',T/'relic_sim_hotfix12_e2e_v0.7.7.json'),
 ('quest_ime_e2e',T/'quest_search_ime_hotfix12_e2e_v0.7.7.json'),
 ('monster_e2e',T/'monster_links_hotfix11_e2e_v0.7.7.json'),
 ('weapon_slot_e2e',T/'auto_weapon_slot_hotfix9_e2e_v0.7.7.json'),
 ('armor_resist_e2e',T/'armor_set_resist_hotfix10_e2e_v0.7.7.json'),
 ('backnav_e2e',T/'hotfix15_backnav_e2e_v0.7.7.json'),
 ('complex_e2e',T/'hotfix21_complex_search_e2e_v0.7.7.json'),
 ('autorank_smoke',T/'hotfix20_auto_rank_smoke_e2e_v0.7.7.json'),
]:
    try: x=json.loads(path.read_text(encoding='utf-8')); ok(name,x.get('ok') is True,x.get('errors'))
    except Exception as e: ok(name,False,str(e))
readme=(ROOT/'README.md').read_text(encoding='utf-8'); ws=(ROOT/'WORK_STATUS_v0.7.7.md').read_text(encoding='utf-8')
ok('readme_top',readme.startswith('> **2026-10-07 · 퀘스트 검색 최적화 / 발굴무기 복합스킬 시뮬레이션 hotfix12'))
ok('work_status_top',ws.startswith('## 2026-10-07 - 퀘스트 검색 최적화 / 발굴무기 복합스킬 시뮬레이션 hotfix12'))
# data sanity
relic=json.loads((D/'relic_weapon_decorations.json').read_text(encoding='utf-8'))
ok('relic_data_nonempty',len(relic)==52,len(relic))
ok('relic_exact_slots',set(int(x['slots']) for x in relic)=={1,2,3},sorted(set(int(x['slots']) for x in relic)))
report={'version':VERSION,'ok':not issues,'checkCount':len(checks),'issueCount':len(issues),'checks':checks,'issues':issues}
(T/'relic_sim_hotfix12_release_gate_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':report['ok'],'checkCount':report['checkCount'],'issueCount':report['issueCount'],'issues':issues},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
