from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
d=json.load(open(ROOT/'data/relic_equipment.json',encoding='utf-8'))
weapons=json.load(open(ROOT/'data/weapons.json',encoding='utf-8'))
monsters=json.load(open(ROOT/'data/monster_summary.json',encoding='utf-8'))
def norm(s): return re.sub(r'[\s　]','',str(s or '')).replace('‐','-').replace('‑','-').replace('–','-').replace('—','-').replace('―','-')
idx={(w.get('weaponType'),norm(w.get('mh4uNameJa') or w.get('nameJa'))):w.get('name') for w in weapons}
groups=d.get('sealedGroups',[]); apps=d.get('weaponAppearances',{}); pools=d.get('armorAppearancePools',{})
issues=[]
if len(groups)!=11: issues.append(f'group count {len(groups)}')
if len(apps)!=14: issues.append(f'weapon type count {len(apps)}')
for t,arr in apps.items():
    if len(arr)!=11: issues.append(f'{t} appearance count {len(arr)}')
for i in range(1,12):
    if not pools.get(str(i)): issues.append(f'armor pool missing group {i}')
monster_names={x.get('name') for x in monsters}
missing_monsters=[m for g in groups for m in g.get('monsters',[]) if m not in monster_names]
if missing_monsters: issues.append('monster names missing: '+','.join(missing_monsters))
matched=0; total=0; unmatched=[]
for t,arr in apps.items():
    for jp in arr:
        if jp=='-': continue
        total+=1
        if (t,norm(jp)) in idx: matched+=1
        else: unmatched.append({'weaponType':t,'jp':jp})
out={'ok':not issues,'issues':issues,'groups':len(groups),'weaponTypes':len(apps),'appearanceEntries':total,'normalWeaponNameMatches':matched,'unmatchedAppearanceNames':unmatched,'armorGroups':len(pools),'attackRawTypes':len(d.get('attackRawTypes',[])),'sources':len(d.get('sources',[]))}
(ROOT/'tools/relic_guide_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
