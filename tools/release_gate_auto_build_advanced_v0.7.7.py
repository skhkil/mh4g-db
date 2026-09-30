#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parents[1];TOOLS=ROOT/'tools'
steps=[
 ('stage1_threshold',['node','tools/auto_build_stage1_threshold_audit_v0.7.7.mjs']),
 ('stage2_resources',['node','tools/auto_build_stage2_resource_audit_v0.7.7.mjs']),
 ('stage3_5_browser',['python','tools/e2e_auto_build_stage3_5_v0.7.7.py']),
 ('stage4_6_alignment',['node','tools/audit_auto_build_stage4_6_v0.7.7.mjs']),
]
rows=[]
for name,cmd in steps:
 t=time.perf_counter()
 try:r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=240)
 except subprocess.TimeoutExpired as e: row={'name':name,'ok':False,'elapsedSec':round(time.perf_counter()-t,2),'stderr':'timeout'}
 else: row={'name':name,'ok':r.returncode==0,'elapsedSec':round(time.perf_counter()-t,2),'stdout':r.stdout[-5000:],'stderr':r.stderr[-2000:]}
 rows.append(row);print(f"{name}: {'OK' if row['ok'] else 'FAIL'} ({row['elapsedSec']}s)",flush=True)
 if not row['ok']:break
code_mtime=max((ROOT/p).stat().st_mtime for p in ['index.html','js/app.js','js/engine.js','js/data-loader.js','css/app.css','data/weapon_skill_priorities.json'])
reports=['auto_build_stage1_threshold_audit_v0.7.7.json','auto_build_stage2_resource_audit_v0.7.7.json','auto_build_stage3_5_e2e_v0.7.7.json','auto_build_stage4_6_audit_v0.7.7.json','hotfix21_release_gate_v0.7.7.json']
if all(x['ok'] for x in rows) and len(rows)==len(steps):
 for fn in reports:
  p=TOOLS/fn
  try:o=json.loads(p.read_text(encoding='utf-8'));fresh=p.stat().st_mtime>=code_mtime;ok=bool(o.get('ok')) and fresh;detail=f"report_ok={bool(o.get('ok'))}, fresh={fresh}"
  except Exception as e:ok=False;detail=str(e)
  rows.append({'name':'fresh:'+fn,'ok':ok,'elapsedSec':0,'detail':detail});print(f"fresh:{fn}: {'OK' if ok else 'FAIL'} ({detail})",flush=True)
  if not ok:break
ok=len(rows)==len(steps)+len(reports) and all(x['ok'] for x in rows)
out={'ok':ok,'version':'0.7.7-chat4-auto-build-advanced-final','codeMtime':code_mtime,'steps':rows}
(TOOLS/'auto_build_advanced_release_gate_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':ok,'steps':[{'name':x['name'],'ok':x['ok'],'elapsedSec':x.get('elapsedSec',0)} for x in rows]},ensure_ascii=False,indent=2));raise SystemExit(0 if ok else 1)
