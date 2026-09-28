from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
loader=(ROOT/'js/data-loader.js').read_text(encoding='utf-8')
index=(ROOT/'index.html').read_text(encoding='utf-8')
version='0.7.7-chat4-research2-hotfix14'
checks={
 'version_app': version in app,
 'version_loader': version in loader,
 'version_index': version in index,
 'bind_idempotent_guard': 'let delegatedEventsBound=false;' in app and 'if(!delegatedEventsBound){' in app and 'delegatedEventsBound=true;' in app,
 'popstate_rebind': 'restoreAppHistoryState(e.state).finally' in app and 'bind();' in app[app.find('window.addEventListener("popstate"'):app.find('window.addEventListener("pageshow"')],
 'pageshow_bfcache': 'window.addEventListener("pageshow"' in app and 'navEntry?.type==="back_forward"' in app and 'e.persisted' in app,
 'pagehide_snapshot': 'window.addEventListener("pagehide",()=>replaceCurrentHistoryState())' in app,
 'nav_history_push': 'void openPage(targetPage).then(pushCurrentHistoryState)' in app,
 'route_history_push': 'void handleRoute(b).then(pushCurrentHistoryState)' in app,
 'route_async': 'async function handleRoute(btn)' in app,
 'no_double_await': 'await await' not in app,
}
syntax={}
for f in ['js/app.js','js/engine.js','js/data-loader.js']:
    p=subprocess.run(['node','--check',str(ROOT/f)],capture_output=True,text=True)
    syntax[f]=p.returncode==0
checks['syntax_all']=all(syntax.values())
# retain core data sanity
armors=json.loads((ROOT/'data/armors.json').read_text(encoding='utf-8'))
sim=json.loads((ROOT/'data/sim_armors.json').read_text(encoding='utf-8'))
rec=json.loads((ROOT/'data/recommended_loadouts.json').read_text(encoding='utf-8'))
checks['armor_count']=len(armors)==3119
checks['sim_armor_count']=len(sim)==3119
cards=sum(len(e.get('variants',[])) for e in rec.get('entries',[]))
checks['recommend_cards']=cards==108
out={'ok':all(checks.values()),'version':version,'checks':checks,'syntax':syntax,'counts':{'armors':len(armors),'simArmors':len(sim),'recommendCards':cards}}
(ROOT/'tools/hotfix14_history_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
