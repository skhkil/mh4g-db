#!/usr/bin/env python3
from pathlib import Path
import json, re, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'js/app.js'; LOADER=ROOT/'js/data-loader.js'; ENGINE=ROOT/'js/engine.js'; INDEX=ROOT/'index.html'
app=APP.read_text(encoding='utf-8'); loader=LOADER.read_text(encoding='utf-8'); engine=ENGINE.read_text(encoding='utf-8'); index=INDEX.read_text(encoding='utf-8')
version='0.7.7-step4-final-release'
checks={}
# Browser-equivalent ES module syntax, not CommonJS node --check.
syntax={}
for f in (APP,LOADER,ENGINE):
    r=subprocess.run(['node','--experimental-default-type=module','--check',str(f)],capture_output=True,text=True)
    syntax[f.name]={'ok':r.returncode==0,'stderr':r.stderr.strip()}
checks['es_module_syntax_all']=all(v['ok'] for v in syntax.values())
checks['cache_version_consistent']=all(version in x for x in (app,loader,index)) and 'hotfix14' not in index
checks['bind_one_shot_guard']='let appEventsBound=false;' in app and 'if(appEventsBound)return true;' in app and 'appEventsBound=results.every(Boolean);' in app
# bind() may only be invoked once, during startup.
bind_calls=[m.start() for m in re.finditer(r'(?<!function )\bbind\(\)',app)]
checks['bind_called_bootstrap_and_retry']=len(bind_calls)==2
# Back/forward lifecycle must never rebind/rerender the app.
pop=app[app.find('window.addEventListener("popstate"'):app.find('window.addEventListener("pageshow"')]
page_start=app.find('window.addEventListener("pageshow"')
page_end=app.find('  }));',page_start)+6
page=app[page_start:page_end]
checks['popstate_restore_only']='restoreAppHistoryState(e.state)' in pop and 'bind()' not in pop and 'pushState' not in pop and 'replaceState' not in pop
checks['pageshow_no_rebind_or_rerender']='bind()' not in page and 'renderPageData(' not in page and 'renderAll(' not in page
checks['no_pagehide_history_mutation']='window.addEventListener("pagehide"' not in app
checks['manual_scroll_restoration']='history.scrollRestoration="manual"' in app
checks['history_restore_token']='historyRestoreToken' in app and 'restoreToken===historyRestoreToken' in app
# All top-level navigation and recommendation->simulator must use the shared navigation path.
rec=app[app.find('async function openRecommendationInSimulator'):app.find('function updateHeaderFilterVisibility')]
checks['recommend_sim_uses_shared_navigation']='navigatePage("simulator"' in rec and 'await openPage("simulator")' not in rec
nav=app[app.find("$$('.nav-main[data-page]')"):app.find("$$('[data-route]')")]
checks['main_nav_uses_shared_navigation']='navigatePage(targetPage' in nav and 'openPage(targetPage).then(pushCurrentHistoryState)' not in nav
checks['shared_navigation_saves_before_push']='replaceCurrentHistoryState();' in app[app.find('async function navigatePage'):app.find('async function restoreAppHistoryState')] and 'pushCurrentHistoryState();' in app[app.find('async function navigatePage'):app.find('async function restoreAppHistoryState')]
checks['recommend_state_in_history']='recommendWeaponType,recommendRank' in app[app.find('function captureAppHistoryState'):app.find('function replaceCurrentHistoryState')]
# Guard against the exact parser regression that escaped prior validation.
click_start=app.find("document.addEventListener('click',safeUiHandler('document.click',e=>{")
click_block=app[click_start:app.find('document.addEventListener("keydown"',click_start)]
checks['no_sync_handler_await_bug']="document.addEventListener('click',safeUiHandler('document.click',e=>{" in click_block and 'await openPage("decoration")' not in click_block
# Core data counts / regressions.
def load(name): return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))
arm=load('armors.json'); sim=load('sim_armors.json'); recdata=load('recommended_loadouts.json')
cards=sum(len(e.get('variants',[])) for e in recdata.get('entries',[]))
checks['armor_count']=len(arm)==3119
checks['sim_armor_count']=len(sim)==3119
checks['recommend_cards']=cards==108
out={'ok':all(checks.values()),'version':version,'checks':checks,'syntax':syntax,'counts':{'armors':len(arm),'simArmors':len(sim),'recommendCards':cards},'bindCallCount':len(bind_calls)}
(ROOT/'tools/hotfix15_navigation_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
