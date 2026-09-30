#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
steps=[
 ('app_module_syntax',['node','--experimental-default-type=module','--check','js/app.js']),
 ('loader_module_syntax',['node','--experimental-default-type=module','--check','js/data-loader.js']),
 ('engine_module_syntax',['node','--experimental-default-type=module','--check','js/engine.js']),
 ('planner_structure',['python','tools/audit_hotfix19_planner_v0.7.7.py']),
 ('planner_e2e_repeat',['python','tools/e2e_hotfix19_planner_v0.7.7.py']),
 ('planner_mobile_e2e',['python','tools/e2e_hotfix19_planner_mobile_v0.7.7.py']),
 ('mobile_progression_e2e_baseline',['python','tools/e2e_hotfix18_mobile_progression_v0.7.7.py']),
 ('browser_stability_baseline',['python','tools/e2e_hotfix17_stability_v0.7.7.py']),
 ('armor_progression_all',['python','tools/audit_hotfix16_armor_progression_v0.7.7.py']),
 ('cross_references',['python','tools/audit_cross_references_v0.7.7.py']),
 ('recommended_loadouts',['python','tools/audit_recommended_loadouts_v0.7.7.py']),
 ('armor_search_benchmark',['node','tools/benchmark_armor_search_v0.7.7.mjs']),
]
results=[];ok=True
for name,cmd in steps:
    t=time.perf_counter()
    try:r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=210)
    except subprocess.TimeoutExpired as e:
        results.append({'name':name,'ok':False,'returncode':124,'elapsedSec':round(time.perf_counter()-t,2),'stdout':(e.stdout or '')[-6000:] if isinstance(e.stdout,str) else '', 'stderr':'timeout'});ok=False;continue
    row={'name':name,'ok':r.returncode==0,'returncode':r.returncode,'elapsedSec':round(time.perf_counter()-t,2),'stdout':r.stdout[-6000:],'stderr':r.stderr[-3000:]};results.append(row);ok=ok and row['ok']
out={'ok':ok,'version':'0.7.7-chat4-research2-hotfix19','steps':results}
(ROOT/'tools/hotfix19_release_gate_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':ok,'steps':[{'name':x['name'],'ok':x['ok'],'elapsedSec':x['elapsedSec']} for x in results]},ensure_ascii=False,indent=2))
if not ok:
    for x in results:
        if not x['ok']:
            print('\nFAILED',x['name']);print(x.get('stdout',''));print(x.get('stderr',''))
raise SystemExit(0 if ok else 1)
