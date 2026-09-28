#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
steps=[
    ('navigation_static',['python','tools/audit_hotfix15_navigation_v0.7.7.py']),
    ('backnav_browser_e2e',['python','tools/e2e_back_navigation_v0.7.7.py']),
    ('cross_references',['python','tools/audit_cross_references_v0.7.7.py']),
    ('armor_progression',['python','tools/audit_armor_progression_v0.7.7.py']),
    ('recommendation_engine',['node','tools/audit_recommend_simulator_link_v0.7.7.mjs']),
    ('armor_search_benchmark',['node','tools/benchmark_armor_search_v0.7.7.mjs']),
]
results=[]; ok=True
for name,cmd in steps:
    t=time.perf_counter()
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=300)
    results.append({'name':name,'ok':r.returncode==0,'ms':round((time.perf_counter()-t)*1000,2),'stdout':r.stdout[-4000:],'stderr':r.stderr[-2000:]})
    if r.returncode!=0:
        ok=False; break
out={'ok':ok,'version':'0.7.7-chat4-research2-hotfix15','steps':results}
(ROOT/'tools/hotfix15_release_gate_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':ok,'steps':[{'name':x['name'],'ok':x['ok'],'ms':x['ms']} for x in results]},ensure_ascii=False,indent=2))
raise SystemExit(0 if ok else 1)
