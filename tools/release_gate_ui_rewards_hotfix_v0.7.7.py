#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parents[1];TOOLS=ROOT/'tools'
checks=[]
def add(name,ok,detail=''): checks.append({'name':name,'ok':bool(ok),'detail':detail})
# syntax
for name,path in [('app_syntax','js/app.js'),('loader_syntax','js/data-loader.js'),('engine_syntax','js/engine.js')]:
 r=subprocess.run(['node','--check',path],cwd=ROOT,text=True,capture_output=True);add(name,r.returncode==0,(r.stderr or '')[-1000:])
# static/data audits
idx=(ROOT/'index.html').read_text(encoding='utf-8');app=(ROOT/'js/app.js').read_text(encoding='utf-8')
quests=json.loads((ROOT/'data/quests.json').read_text(encoding='utf-8'));qref=json.loads((ROOT/'data/quest_reference_index.json').read_text(encoding='utf-8')).get('quests',{});emaj=json.loads((ROOT/'data/event_major_rewards.json').read_text(encoding='utf-8')).get('quests',{})
events=[q for q in quests if q.get('questType')=='event'];missing=[q['id'] for q in events if not (emaj.get(q['id'],{}).get('rewardLabels') or qref.get(q['id'],{}).get('rewardItems'))]
add('event_rewards_complete',len(events)==96 and not missing,f'events={len(events)}, missing={len(missing)} {missing[:10]}')
decos=json.loads((ROOT/'data/decorations.json').read_text(encoding='utf-8'));dunlock=json.loads((ROOT/'data/decoration_unlocks.json').read_text(encoding='utf-8')).get('decorations',{})
add('decoration_unlock_index',len(decos)==199 and len(dunlock)==199,f'decos={len(decos)}, unlockRecords={len(dunlock)}')
add('owned_charm_ui_moved','owned-charm-panel' not in idx and 'data-save-owned-charm' in app,'old panel absent / inline save present')
add('auto_weapon_type_independent','id="autoWeaponType"' in idx and 'autoSearchWeaponSlots' in app and 'attachAutoWeapons' in app,'separate weapon type + actual weapon attach')
add('compact_result_cleanup','완성 커스텀 구성' not in app and '<th>스킬 계통</th><th>포인트</th><th>발동 스킬</th>' in app,'duplicate box absent / compact 3 columns')
add('event_notes_column_removed','["구분","레벨","퀘스트","클리어 조건","몬스터","주요 보상","장소","계약금","보수금","HRP","시간","서브퀘스트","서브 보수","서브 HRP","특수조건"]' in app,'event header without notes')
add('docs_updated',idx.find('0.7.7-chat4-ui-reward-hotfix1')>=0 and (ROOT/'README.md').read_text(encoding='utf-8').lstrip().startswith('> **2026-10-01') and (ROOT/'WORK_STATUS_v0.7.7.md').read_text(encoding='utf-8').lstrip().startswith('## 2026-10-01'),'cache/docs current')
code_mtime=max((ROOT/p).stat().st_mtime for p in ['index.html','js/app.js','js/data-loader.js','js/engine.js','css/app.css','data/event_major_rewards.json','data/decoration_unlocks.json'])
for fn in ['ui_rewards_hotfix_e2e_v0.7.7.json','auto_build_advanced_release_gate_v0.7.7.json','hotfix17_stability_e2e_v0.7.7.json','hotfix15_backnav_e2e_v0.7.7.json']:
 p=TOOLS/fn
 try:o=json.loads(p.read_text(encoding='utf-8'));fresh=p.stat().st_mtime>=code_mtime;ok=bool(o.get('ok')) and fresh;detail=f'report_ok={bool(o.get("ok"))}, fresh={fresh}'
 except Exception as e:ok=False;detail=str(e)
 add('fresh:'+fn,ok,detail)
ok=all(x['ok'] for x in checks)
out={'ok':ok,'version':'0.7.7-chat4-ui-reward-hotfix1','codeMtime':code_mtime,'checks':checks}
(TOOLS/'ui_rewards_hotfix_release_gate_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2));raise SystemExit(0 if ok else 1)
