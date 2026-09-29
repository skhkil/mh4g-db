#!/usr/bin/env python3
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[1]
steps=[
 ('app_module_syntax',['node','--experimental-default-type=module','--check','js/app.js']),
 ('loader_module_syntax',['node','--experimental-default-type=module','--check','js/data-loader.js']),
 ('engine_module_syntax',['node','--experimental-default-type=module','--check','js/engine.js']),
 ('runtime_structure',['python','tools/audit_hotfix18_runtime_v0.7.7.py']),
 ('mobile_progression_structure',['python','tools/audit_hotfix18_mobile_ui_v0.7.7.py']),
 ('mobile_progression_e2e',['python','tools/e2e_hotfix18_mobile_progression_v0.7.7.py']),
 ('browser_repeat_e2e_baseline',['python','tools/e2e_hotfix17_stability_v0.7.7.py']),
 ('armor_progression_all',['python','tools/audit_hotfix16_armor_progression_v0.7.7.py']),
 ('cross_references',['python','tools/audit_cross_references_v0.7.7.py']),
 ('recommended_loadouts',['python','tools/audit_recommended_loadouts_v0.7.7.py']),
 ('armor_search_benchmark',['node','tools/benchmark_armor_search_v0.7.7.mjs']),
]
results=[];ok=True
for name,cmd in steps:
    r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=300)
    results.append({'name':name,'ok':r.returncode==0,'returncode':r.returncode,'stdout':r.stdout[-6000:],'stderr':r.stderr[-3000:]})
    if r.returncode!=0:ok=False
out={'ok':ok,'version':'0.7.7-chat4-research2-hotfix18','steps':results}
(ROOT/'tools/hotfix18_release_gate_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':ok,'steps':[{'name':x['name'],'ok':x['ok']} for x in results]},ensure_ascii=False,indent=2))
if not ok:
    for x in results:
        if not x['ok']:
            print('\nFAILED',x['name']);print(x['stdout']);print(x['stderr'])
raise SystemExit(0 if ok else 1)
