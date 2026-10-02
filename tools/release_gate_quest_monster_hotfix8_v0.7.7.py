#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys, re, datetime
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'; T=ROOT/'tools'
checks=[]
def add(name,ok,detail=''):
 checks.append({'name':name,'ok':bool(ok),'detail':detail})
# Syntax
for f in ['js/app.js','js/data-loader.js','js/engine.js']:
 r=subprocess.run(['node','--check',str(ROOT/f)],capture_output=True,text=True)
 add('syntax_'+f,r.returncode==0,(r.stderr or r.stdout).strip())
# Runtime cache version must be unified.
ver='0.7.7-chat4-quest-monster-hotfix8'
for f in ['index.html','js/app.js','js/data-loader.js']:
 s=(ROOT/f).read_text(encoding='utf-8'); add('cache_'+f,ver in s and '0.7.7-chat4-xref-hotfix7' not in s)
# Audits and E2E fresh outputs.
for f in ['quest_monster_semantic_audit_hotfix8_v0.7.7.json','quest_item_monster_xref_audit_hotfix8_v0.7.7.json']:
 p=D/f; obj=json.loads(p.read_text(encoding='utf-8')); add(f,obj.get('issueCount')==0,obj.get('issueCount'))
for f in ['quest_monster_semantics_hotfix8_e2e_v0.7.7.json','xref_hotfix7_e2e_v0.7.7.json','hotfix3_quest_links_near_skill_e2e_v0.7.7.json','hotfix21_complex_search_e2e_v0.7.7.json','hotfix17_stability_e2e_v0.7.7.json','hotfix20_auto_rank_smoke_e2e_v0.7.7.json']:
 p=T/f; obj=json.loads(p.read_text(encoding='utf-8')); add(f,obj.get('ok') is True,obj.get('errors') or obj.get('runs'))
# README/WORK status must be user-visible and current.
rd=(ROOT/'README.md').read_text(encoding='utf-8'); ws=(ROOT/'WORK_STATUS_v0.7.7.md').read_text(encoding='utf-8')
add('readme_hotfix8_top',rd.startswith('> **2026-10-02 · 퀘스트↔몬스터 의미 전수검사 hotfix8**'))
add('work_status_hotfix8','## 2026-10-02 hotfix8 — 퀘스트 ↔ 몬스터 의미 전수검사' in ws)
# Core facts.
qs=json.loads((D/'quests.json').read_text(encoding='utf-8')); qi=json.loads((D/'quest_reference_index.json').read_text(encoding='utf-8'))['quests']
add('quest_count',len(qs)==572,len(qs)); add('caravan_193',sum(q.get('questType')=='village' for q in qs)==193); add('guild_258',sum(q.get('questType') in ('hub','g') for q in qs)==258)
spot={'quest_c83c67f7419a':['녹슨크샬다오라'],'quest_h8_g3_operation_rust_remover':['녹슨크샬다오라'],'quest_5f701615a1a9':['진오우거 아종','혼돈의 고어·마가라'],'quest_6cae3017e9a4':['임계 브라키디오스']}
for qid,want in spot.items(): add('spot_'+qid,qi[qid]['monsters']==want,qi[qid]['monsters'])
report={'version':ver,'generated':datetime.datetime.now().isoformat(timespec='seconds'),'ok':all(c['ok'] for c in checks),'checks':checks}
(T/'quest_monster_hotfix8_release_gate_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':report['ok'],'passed':sum(c['ok'] for c in checks),'total':len(checks),'failed':[c for c in checks if not c['ok']]},ensure_ascii=False,indent=2))
raise SystemExit(0 if report['ok'] else 1)
