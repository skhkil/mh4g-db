#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys,datetime,re
ROOT=Path(__file__).resolve().parents[1]
errs=[];facts={}
# JS syntax
for f in ['js/app.js','js/engine.js','js/data-loader.js']:
 r=subprocess.run(['node','--check',str(ROOT/f)],capture_output=True,text=True)
 if r.returncode: errs.append(f'{f} syntax: {r.stderr.strip()}')
facts['jsSyntax']='ok' if not errs else 'fail'
# Fresh audit/e2e reports
for fn in ['material_event_quest_link_audit_hotfix5_v0.7.7.json','material_event_quest_links_hotfix5_e2e_v0.7.7.json','hotfix3_quest_links_near_skill_e2e_v0.7.7.json','hotfix21_complex_search_e2e_v0.7.7.json','hotfix15_backnav_e2e_v0.7.7.json']:
 p=ROOT/'tools'/fn
 if not p.exists(): errs.append('missing report:'+fn);continue
 try:d=json.load(open(p,encoding='utf-8'))
 except Exception as e: errs.append(f'bad report {fn}: {e}');continue
 if not d.get('ok'): errs.append('report failed:'+fn)
 facts[fn]=d.get('ok')
# Data invariants
qs=json.load(open(ROOT/'data/quests.json',encoding='utf-8'))
j=[q for q in qs if q.get('nameJa')=='JUMP・灼熱燃闘！']
if len(j)!=1: errs.append(f'JUMP quest count {len(j)}')
else:
 q=j[0]
 facts['jumpQuest']={'id':q['id'],'name':q['name'],'level':q['level'],'objective':q['objective']}
 if q.get('name')!='JUMP·작열연투!' or q.get('level')!='G★3': errs.append('JUMP canonical mismatch')
idx=json.load(open(ROOT/'data/quest_reference_index.json',encoding='utf-8')).get('quests',{})
if j and j[0]['id'] not in idx: errs.append('JUMP qref missing')
# Cache key
html=(ROOT/'index.html').read_text(encoding='utf-8')
if '0.7.7-chat4-ui-reward-hotfix5' not in html: errs.append('cache key not hotfix5')
# No temp backups
bad=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and (p.suffix in {'.bak','.pyc'} or '__pycache__' in p.parts)]
if bad: errs.append('temp files:'+','.join(bad[:20]))
facts['tempFiles']=bad
rep={'version':'0.7.7-hotfix5','generated':datetime.datetime.now().isoformat(timespec='seconds'),'ok':not errs,'facts':facts,'errors':errs}
out=ROOT/'tools'/'ui_rewards_hotfix5_release_gate_v0.7.7.json';out.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rep,ensure_ascii=False,indent=2));raise SystemExit(0 if rep['ok'] else 1)
