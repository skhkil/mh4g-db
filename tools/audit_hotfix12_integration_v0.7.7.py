import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
armors=json.loads((ROOT/'data/armors.json').read_text())
sim=json.loads((ROOT/'data/sim_armors.json').read_text())
restore=json.loads((ROOT/'tools/missing_armor_restore_audit_v0.7.7.json').read_text())
prog=json.loads((ROOT/'tools/armor_progression_audit_v0.7.7.json').read_text())
bench=json.loads((ROOT/'tools/armor_search_benchmark_v0.7.7.json').read_text())
app=(ROOT/'js/app.js').read_text()
loader=(ROOT/'js/data-loader.js').read_text()
index=(ROOT/'index.html').read_text()
version='0.7.7-chat4-research2-hotfix12'
ids={a['id'] for a in armors}; simids={a['id'] for a in sim}
restored=[a for a in armors if a.get('restoredFromExternal')]
# restore script marks may vary; authoritative audit count used if marker absent
errors=[]
checks={
 'armorCount':len(armors),
 'simArmorCount':len(sim),
 'restoredArmorCount':restore['summary']['restoredArmorCount'],
 'restoredGXCount':restore['summary']['restoredGXCount'],
 'externalCommonRemainingMissing':restore['summary']['externalCommonRemainingMissing'],
 'progressionMaterials':prog['materials'],
 'progressionUnresolved':prog['unresolved'],
 'progressionErrors':prog['errors'],
 'searchSpeedup':bench['speedup'],
 'searchCountParity':all(x['old']==x['optimized'] for x in bench['sameSampleCounts']),
 'simMissingFromFull':len(simids-ids),
 'versionApp':version in app,
 'versionLoader':version in loader,
 'versionIndex':version in index,
 'cachedQueryContext':'armorSearchQueryContextCache' in app,
 'cachedArmorCorpus':'armorSearchCorpusCache' in app,
 'debouncedArmorPicker':'debounceMs:60' in app,
 'debouncedArmorTable':'setTimeout(renderArmorTable,110)' in app,
}
if len(armors)!=3119: errors.append('armor count')
if checks['externalCommonRemainingMissing']!=0: errors.append('remaining missing armor')
if prog['unresolved'] or prog['errors']: errors.append('progression unresolved/errors')
if not checks['searchCountParity']: errors.append('search result parity')
if bench['speedup']<5: errors.append('search speedup too low')
if checks['simMissingFromFull']!=0: errors.append('sim armor orphan')
for k in ['versionApp','versionLoader','versionIndex','cachedQueryContext','cachedArmorCorpus','debouncedArmorPicker','debouncedArmorTable']:
    if not checks[k]: errors.append(k)
out={'ok':not errors,'version':version,'checks':checks,'errors':errors}
(ROOT/'tools/hotfix12_integration_audit_v0.7.7.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
