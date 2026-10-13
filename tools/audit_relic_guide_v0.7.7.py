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
deriv=d.get('guildQuestDerivation',{}); entries=deriv.get('entries',[])
valid_modes={'normal','rare','intruder'}
if len(entries)<150: issues.append(f'derivation entries too few: {len(entries)}')
if any(x.get('appearance') not in valid_modes for x in entries): issues.append('invalid derivation appearance mode')
if any(not x.get('source') or not x.get('target') for x in entries): issues.append('blank derivation source/target')
# key reverse-query examples cross-checked against MH4G@wiki
checks={
 'alceltas_to_rajang':any(x.get('source')=='알셀타스' and x.get('target')=='라잔' for x in entries),
 'gore_to_shagaru':any(x.get('source')=='고어·마가라' and x.get('target')=='샤가르마가라' and x.get('appearance')=='rare' for x in entries),
 'rathalos_sub_to_kushala':any(x.get('source')=='리오레우스 아종' and x.get('target')=='크샬다오라' for x in entries),
 'rajang_reverse_has_alceltas':any(x.get('target')=='라잔' and x.get('source')=='알셀타스' for x in entries),
}
if not all(checks.values()): issues.append('derivation sample mismatch: '+repr(checks))

qg=d.get('qualityGuide',{})
if len(qg.get('mh4gBands',[]))!=5: issues.append(f"quality bands {len(qg.get('mh4gBands',[]))}")
if not any(x.get('level')=='Lv86~100' and '영광' in x.get('quality','') for x in qg.get('mh4gBands',[])): issues.append('missing 86-100 glory band')
if not any(x.get('level')=='Lv126~135' and '봉인' in x.get('quality','') for x in qg.get('mh4gBands',[])): issues.append('missing 126-135 sealed band')
if not any(x.get('route')=='맵 채굴/채집' and '몬스터와 무관' in x.get('rule','') for x in qg.get('mh4gRules',[])): issues.append('missing mh4g mining rule')
if not any('MH4의 Lv91' in x for x in qg.get('cautions',[])): issues.append('missing mh4 vs mh4g caution')
out={'ok':not issues,'issues':issues,'groups':len(groups),'weaponTypes':len(apps),'appearanceEntries':total,'normalWeaponNameMatches':matched,'unmatchedAppearanceNames':unmatched,'armorGroups':len(pools),'attackRawTypes':len(d.get('attackRawTypes',[])),'sources':len(d.get('sources',[])),'derivationEntries':len(entries),'derivationSources':len(set(x.get('source') for x in entries)),'derivationTargets':len(set(x.get('target') for x in entries)),'derivationChecks':checks,'gradeRows':len(d.get('grades',[])),'qualityBands':len(qg.get('mh4gBands',[])),'qualityExamples':len(qg.get('evidenceExamples',[]))}
(ROOT/'tools/relic_guide_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['ok'] else 1)
