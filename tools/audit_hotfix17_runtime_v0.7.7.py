#!/usr/bin/env python3
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
loader=(ROOT/'js/data-loader.js').read_text(encoding='utf-8')
index=(ROOT/'index.html').read_text(encoding='utf-8')
css=(ROOT/'css/app.css').read_text(encoding='utf-8')
checks={
 'version_index':'hotfix17' in index,
 'version_app_imports':'hotfix17' in app.splitlines()[0] and 'hotfix17' in app.splitlines()[1],
 'version_loader':'hotfix17' in loader.splitlines()[0],
 'events_flag_after_groups':'appEventsBound=results.every(Boolean)' in app and 'appEventsBound=true;' not in app,
 'bind_groups':all(x in app for x in ['document-delegates','navigation','simulator-controls','database-filters','recommendation','json-import','history-lifecycle']),
 'binding_isolation':'function bindEventGroup' in app and 'boundEventGroups' in app,
 'runtime_handler_isolation':'function safeUiHandler' in app and 'document.click' in app and 'history.popstate' in app,
 'visible_runtime_error':'appRuntimeStatus' in app and '.app-runtime-status' in css,
 'bind_before_data_load':app.find('bind();',app.find('async function bootstrapApp')) < app.find('await loadSimulatorData()',app.find('async function bootstrapApp')),
 'no_top_level_data_await':'Object.assign(data,await loadSimulatorData())' not in app,
 'navigation_survives_data_failure':'메뉴와 정상 로드된 기능은 계속 사용할 수 있습니다.' in app,
 'progression_failure_isolated':'try{' in app[app.find('async function toggleArmorProgressRow'):app.find('function renderArmorTable')] and '방어구 제작 진행' in app,
 'no_pageshow_rebind':'bind(' not in app[app.find('history.pageshow'):app.find('}));',app.find('history.pageshow'))],
 'no_popstate_rebind':'bind(' not in app[app.find('history.popstate'):app.find('}));',app.find('history.popstate'))],
 'armor_dom_batch':'ARMOR_RENDER_BATCH=180' in app and 'armorLoadMore' in app,
 'history_restore_only':'restoreAppHistoryState(e.state)' in app,
}
# hotfix16-risk additions: lazy progression load must not be able to reject into document event loop.
segment=app[app.find('async function toggleArmorProgressRow'):app.find('function renderArmorTable')]
checks['lazy_progression_has_catch']='loadArmorProgression' in segment and 'catch(err)' in segment and 'finally{' in segment
out={'ok':all(checks.values()),'version':'0.7.7-chat4-research2-hotfix17','checks':checks}
(ROOT/'tools/hotfix17_runtime_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
