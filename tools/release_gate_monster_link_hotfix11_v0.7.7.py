#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'; T=ROOT/'tools'; VERSION='0.7.7-chat4-monster-link-hotfix11'
issues=[]; checks={}
def ok(name,cond,detail=None):
 checks[name]={'ok':bool(cond),'detail':detail}
 if not cond: issues.append({'name':name,'detail':detail})
# Syntax.
for f in ['js/app.js','js/data-loader.js','js/engine.js']:
 r=subprocess.run(['node','--check',str(ROOT/f)],capture_output=True,text=True)
 ok('syntax:'+f,r.returncode==0,(r.stderr or r.stdout).strip())
# Cache version must be unified.
for f in ['index.html','js/app.js','js/data-loader.js']:
 s=(ROOT/f).read_text(encoding='utf-8')
 ok('cache:'+f,VERSION in s)
# Core audit + browser result.
a=json.loads((D/'monster_link_audit_hotfix11_v0.7.7.json').read_text(encoding='utf-8'))
e=json.loads((T/'monster_links_hotfix11_e2e_v0.7.7.json').read_text(encoding='utf-8'))
ok('audit_issue_zero',a.get('issueCount')==0,a.get('issueCount'))
ok('audit_76_monsters',a.get('monsterCount')==76,a.get('monsterCount'))
ok('audit_forward_reverse',a.get('forwardLinks')==a.get('reverseLinks')==585,{'forward':a.get('forwardLinks'),'reverse':a.get('reverseLinks')})
ok('e2e_ok',e.get('ok') is True,e.get('errors'))
ok('e2e_all_76_counts',e.get('facts',{}).get('all_monster_ui_mismatch_count')==0,e.get('facts',{}).get('all_monster_ui_mismatches'))
ok('silver_g_event_visible','이벤트 G★3 · 은빛 왕의 잠' in e.get('facts',{}).get('silver_rathalos',''))
ok('furious_only',e.get('facts',{}).get('all_the_rage_monsters')==['격앙 라잔'],e.get('facts',{}).get('all_the_rage_monsters'))
# Docs must visibly record this hotfix at the top.
readme=(ROOT/'README.md').read_text(encoding='utf-8'); ws=(ROOT/'WORK_STATUS_v0.7.7.md').read_text(encoding='utf-8')
ok('readme_top',readme.startswith('> **2026-10-06 · 몬스터 등장퀘스트 단일 원천화 / 이벤트 연결 전수검사 hotfix11'))
ok('work_status_top',ws.startswith('## 2026-10-06 - 몬스터 등장퀘스트 단일 원천화 / 이벤트 연결 전수검사 hotfix11'))
report={'version':VERSION,'ok':not issues,'checks':checks,'issueCount':len(issues),'issues':issues}
(T/'monster_link_hotfix11_release_gate_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':report['ok'],'checkCount':len(checks),'issueCount':len(issues),'issues':issues},ensure_ascii=False,indent=2))
sys.exit(0 if report['ok'] else 1)
