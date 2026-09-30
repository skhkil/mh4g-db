#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
STEPS=[
 ('app_module_syntax',['node','--experimental-default-type=module','--check','js/app.js']),
 ('loader_module_syntax',['node','--experimental-default-type=module','--check','js/data-loader.js']),
 ('engine_module_syntax',['node','--experimental-default-type=module','--check','js/engine.js']),
 ('hotfix21_structure',['python','tools/audit_hotfix21_runtime_v0.7.7.py']),
 ('complex_search_logic',['node','--experimental-default-type=module','tools/audit_hotfix21_complex_search_v0.7.7.mjs']),
 ('auto_rank_logic_baseline',['node','--experimental-default-type=module','tools/audit_hotfix20_auto_rank_v0.7.7.mjs']),
 ('armor_progression_all',['python','tools/audit_hotfix16_armor_progression_v0.7.7.py']),
 ('cross_references',['python','tools/audit_cross_references_v0.7.7.py']),
 ('recommended_loadouts',['python','tools/audit_recommended_loadouts_v0.7.7.py']),
 ('armor_search_benchmark',['node','tools/benchmark_armor_search_v0.7.7.mjs']),
]
BROWSER_REPORTS=[
 'hotfix21_complex_search_e2e_v0.7.7.json',
 'hotfix20_auto_rank_e2e_v0.7.7.json',
 'hotfix19_planner_e2e_v0.7.7.json',
 'hotfix19_planner_mobile_e2e_v0.7.7.json',
 'hotfix18_mobile_progression_e2e_v0.7.7.json',
 'hotfix17_stability_e2e_v0.7.7.json',
]
code_mtime=max((ROOT/p).stat().st_mtime for p in ['index.html','js/app.js','js/engine.js','css/app.css'])
results=[]
for name,cmd in STEPS:
    t=time.perf_counter()
    try:r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=180)
    except subprocess.TimeoutExpired:
        row={'name':name,'ok':False,'elapsedSec':round(time.perf_counter()-t,2),'stderr':'timeout'}
    else:
        row={'name':name,'ok':r.returncode==0,'elapsedSec':round(time.perf_counter()-t,2),'stdout':r.stdout[-4000:],'stderr':r.stderr[-2000:]}
    results.append(row);print(f"{name}: {'OK' if row['ok'] else 'FAIL'} ({row['elapsedSec']}s)",flush=True)
    if not row['ok']:break
if all(x['ok'] for x in results) and len(results)==len(STEPS):
    for fn in BROWSER_REPORTS:
        p=TOOLS/fn;t=time.perf_counter();ok=False;detail=''
        try:
            obj=json.loads(p.read_text(encoding='utf-8'));fresh=p.stat().st_mtime>=code_mtime;ok=bool(obj.get('ok')) and fresh;detail=f"report_ok={bool(obj.get('ok'))}, fresh={fresh}"
        except Exception as e:detail=str(e)
        results.append({'name':'browser_report:'+fn,'ok':ok,'elapsedSec':round(time.perf_counter()-t,3),'detail':detail})
        print(f"browser_report:{fn}: {'OK' if ok else 'FAIL'} ({detail})",flush=True)
        if not ok:break
ok=len(results)==len(STEPS)+len(BROWSER_REPORTS) and all(x['ok'] for x in results)
out={'ok':ok,'version':'0.7.7-chat4-research2-hotfix21','codeMtime':code_mtime,'steps':results}
(TOOLS/'hotfix21_release_gate_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':ok,'steps':[{'name':x['name'],'ok':x['ok'],'elapsedSec':x['elapsedSec']} for x in results]},ensure_ascii=False,indent=2))
raise SystemExit(0 if ok else 1)
