#!/usr/bin/env python3
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'js/app.js').read_text(encoding='utf-8')
idx=(ROOT/'index.html').read_text(encoding='utf-8')
css=(ROOT/'css/app.css').read_text(encoding='utf-8')
armors=json.loads((ROOT/'data/armors.json').read_text(encoding='utf-8'))
weapons=json.loads((ROOT/'data/weapons.json').read_text(encoding='utf-8'))
quests=json.loads((ROOT/'data/quests.json').read_text(encoding='utf-8'))
checks={
 'version_index':'hotfix19' in idx and 'hotfix18' not in idx.split('<script type="module"')[-1],
 'version_app_imports':'hotfix19' in app.splitlines()[0] and 'hotfix19' in app.splitlines()[1],
 'planner_nav':'data-page="planner"' in idx,
 'planner_page':'id="page-planner"' in idx and all(x in idx for x in ['plannerFavorites','plannerCraftList','plannerMaterials']),
 'favorite_kinds':all(f'plannerIconButton("{k}"' in app for k in ['weapon','armor','recommend','quest']),
 'craft_add':all(x in app for x in ['data-planner-craft-kind','addPlannerCraft','plannerCraftEntries']),
 'material_aggregation':all(x in app for x in ['plannerMaterialTotals','need-owned','m.count*entry.qty']),
 'inventory_input':'data-planner-inventory' in app and 'plannerState.inventory' in app,
 'material_navigation':'${itemLink(m.name)}' in app,
 'multi_qty':all(x in app for x in ['data-planner-craft-qty','data-planner-craft-delta','entry.qty']),
 'localstorage':all(x in app for x in ['mh4g-planner-v1','localStorage.getItem','localStorage.setItem']),
 'storage_fallback':'plannerMemoryStorage' in app,
 'planner_nav_links':'#page-planner [data-item-nav]' in app,
 'responsive_css':'@media (max-width:820px)' in css and '.planner-material-row' in css,
 'source_counts':len(armors)==3119 and len(weapons)==2314 and len(quests)==547,
}
# Independent material parser parity check for representative rows.
def parse(text):
    return [(m.group(1).strip(),int(m.group(2))) for m in re.finditer(r'(.*?)(?:[×*x]\s*(\d+))(?=\s|$)',str(text or '')) if m.group(1).strip()]
armor=next(a for a in armors if a['name']=='카브라헬름')
checks['armor_material_parse']=len(parse(armor.get('materials')))>0 and sum(n for _,n in parse(armor.get('materials')))>0
weapon=next(w for w in weapons if w.get('craft'))
recipe=next((c for c in weapon['craft'] if '생산' in c.get('method','')),weapon['craft'][0])
checks['weapon_material_parse']=len(parse(recipe.get('materials')))>0
out={'ok':all(checks.values()),'version':'0.7.7-chat4-research2-hotfix19','checks':checks,'samples':{'armor':armor['name'],'armorMaterials':parse(armor.get('materials')),'weapon':weapon['name'],'weaponMaterials':parse(recipe.get('materials'))}}
(ROOT/'tools/hotfix19_planner_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
