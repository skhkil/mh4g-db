import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.7.7-chat4-auto-job-hotfix14'
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
loader=(ROOT/'js/data-loader.js').read_text(encoding='utf-8')
index=(ROOT/'index.html').read_text(encoding='utf-8')
css=(ROOT/'css/app.css').read_text(encoding='utf-8')
rec=json.load(open(ROOT/'data/recommended_loadouts.json',encoding='utf-8'))
link=json.load(open(ROOT/'tools/recommend_simulator_link_audit_v0.7.7.json',encoding='utf-8'))
# Extract only the handoff function body up to next function.
m=re.search(r'async function openRecommendationInSimulator\(index\)\{(.*?)\n\}\n\nfunction updateHeaderFilterVisibility',app,re.S)
body=m.group(1) if m else ''
checks={
 'versionApp': VERSION in app,
 'versionLoader': VERSION in loader,
 'versionIndex': VERSION in index,
 'cardCount': link.get('cards')==108==sum(len(e.get('variants',[])) for e in rec.get('entries',[])),
 'engineMismatch': link.get('engineMismatch')==0,
 'missingArmor': link.get('missingArmor')==0,
 'missingDeco': link.get('missingDeco')==0,
 'armorOnlyFunctionFound': bool(body),
 'setsFiveArmorSlots': all(token in body for token in ['for(const p of PARTS)uiState.manual[p]=""','uiState.manual[a.part]=a.id']),
 'noRecommendedDecorationInjection': 'decorationPlacements' not in body and 'manualDecorations' not in body and 'distributeRecommendationDecorations' not in app,
 'noCharmInjection': all(token not in body for token in ['charmSkill','charmPoint','charmSlots']),
 'noWeaponInjection': all(token not in body for token in ['manualWeapon','weaponSlots']),
 'buttonLabel': '방어구 5부위 불러오기' in app,
 'nonAutoNotice': '장식주·호석·무기 자동입력 없음' in app,
 'engineBadge': 'recommend-engine-badge' in app and 'recommend-engine-badge' in css,
 'bindHandler': 'data-recommend-sim' in app and 'openRecommendationInSimulator(recSim.dataset.recommendSim)' in app,
}
# JS syntax checks
for js in ['js/app.js','js/engine.js','js/data-loader.js']:
 r=subprocess.run(['node','--check',str(ROOT/js)],capture_output=True,text=True)
 checks['syntax_'+Path(js).stem]=r.returncode==0
errors=[k for k,v in checks.items() if not v]
out={'ok':not errors,'version':VERSION,'checks':checks,'recommendationAudit':{k:link.get(k) for k in ['entries','cards','engineMismatch','missingArmor','missingDeco','finalMatched','finalConditional','autoInjectionPolicy']},'errors':errors}
(ROOT/'tools/hotfix13_integration_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
