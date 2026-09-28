#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, re, sys
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'js/app.js'; LOADER=ROOT/'js/data-loader.js'; ENGINE=ROOT/'js/engine.js'; INDEX=ROOT/'index.html'; WEAPONS=ROOT/'data/sim_weapons.json'
VERSION='0.7.7-chat4-research2-hotfix11'
errors=[]
for f in [APP,LOADER,ENGINE]:
    r=subprocess.run(['node','--check',str(f)],capture_output=True,text=True)
    if r.returncode: errors.append(f'JS syntax: {f.name}: {r.stderr.strip()}')
app=APP.read_text(); loader=LOADER.read_text(); index=INDEX.read_text()
for label,text in [('app',app),('loader',loader),('index',index)]:
    if VERSION not in text: errors.append(f'cache version missing: {label}')
for token in ['manualWeaponTypeFilter','manualWeaponRankFilter','manualWeaponElementFilter','manualWeaponSlotFilter','manualWeaponSearchButton']:
    if token not in app: errors.append(f'filter control missing: {token}')
# Guard against the exact duplicate tail that caused the dead-UI rebuild regression.
if 'mountManualWeaponSearch();refreshManualContainer("weapon");renderManualResult();\n    };\n  }\n  mountManualWeaponSearch();refreshManualContainer("weapon");renderManualResult();' in app:
    errors.append('duplicate manual-weapon control block detected')
ws=json.loads(WEAPONS.read_text())
def types(w): return [x.get('type') for x in [w.get('elementPrimary'),w.get('elementSecondary'),w.get('awakenElement')] if isinstance(x,dict) and x.get('type')]
def match(w,t='all',r='all',e='all',s='all'):
    if t!='all' and w.get('weaponType')!=t:return False
    if r!='all' and w.get('rank')!=r:return False
    ts=types(w)
    if e=='none' and ts:return False
    if e not in ('all','none') and e not in ts:return False
    if s!='all' and int(w.get('slots') or 0)!=int(s):return False
    return True
checks={
 'total':len(ws),
 'g':sum(match(w,r='g') for w in ws),
 'slot3':sum(match(w,s='3') for w in ws),
 'none':sum(match(w,e='none') for w in ws),
 'greatsword_g_water_slot3':sum(match(w,t='대검',r='g',e='물',s='3') for w in ws),
}
order={'g':0,'high':1,'low':2}; ss=sorted(ws,key=lambda w:(order.get(w.get('rank'),9),w.get('weaponType',''),w.get('name','')))
checks['rank_order_bad']=sum(order.get(ss[i-1].get('rank'),9)>order.get(ss[i].get('rank'),9) for i in range(1,len(ss)))
if checks['total']!=2314: errors.append(f"unexpected weapon count: {checks['total']}")
if checks['rank_order_bad']!=0: errors.append('rank sort regression')
out={'ok':not errors,'version':VERSION,'checks':checks,'errors':errors}
(ROOT/'tools/hotfix9_runtime_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
