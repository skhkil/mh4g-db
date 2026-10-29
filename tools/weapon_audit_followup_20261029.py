import json,sqlite3,re,collections,copy,os,pathlib,zipfile,unicodedata
root=pathlib.Path('/mnt/data/weaponaudit/mh4g-db-main');wpath=root/'data/weapons.json';spath=root/'data/sim_weapons.json';w=json.loads(wpath.read_text());sim=json.loads(spath.read_text());con=sqlite3.connect(root/'sources/mh4u.db');con.row_factory=sqlite3.Row
refs={r['_id']:dict(r) for r in con.execute('select * from weapons')}; comps=collections.defaultdict(list)
for r in con.execute('select c.created_item_id,c.type,c.quantity,i.name,i.name_jp from components c join items i on i._id=c.component_item_id'):
 comps[r['created_item_id']].append(dict(r))
changes=[];problems=[]; tree=[]; material=[]; id_map={x.get('mh4uWeaponId'):x for x in w if x.get('mh4uWeaponId')}
fixjids=set()
prior=json.loads((root/'data/weapon_full_audit_20261029.json').read_text())
fixjids={x['id'] for x in prior['nameConflicts']}
# Korean production source is independent; do not replace translated material names without equivalence verified.
for x in w:
 i=x.get('mh4uWeaponId');r=refs.get(i); 
 if not r:
  problems.append({'id':x['id'],'name':x['name'],'type':'no_reference_id','note':'MH4U item page found; no trusted local DB ID: maintain unchanged'});continue
 if x['id'] in fixjids:
  before=x.get('nameJa','');after=x.get('mh4uNameJa') or next((z['matchedRefJa'] for z in prior['nameConflicts'] if z['id']==x['id']),before)
  if after and before!=after:
   x['nameJa']=after; changes.append({'id':x['id'],'name':x['name'],'field':'nameJa','before':before,'after':after,'basis':'linked MH4U weapon ID + confirmed Japanese reference'})
 par=r['parent_id']; depth=r['tree_depth']
 parent=id_map.get(par)
 if par not in (None,0) and not parent:
  tree.append({'id':x['id'],'name':x['name'],'parent_id':par,'finding':'parent missing from local weapon list'})
 elif parent:
  pr=refs.get(par)
  if pr and depth<=pr['tree_depth']:
   tree.append({'id':x['id'],'name':x['name'],'parent':parent['name'],'finding':'tree_depth not increasing'})
  if parent['weaponType']!=x['weaponType']:
   tree.append({'id':x['id'],'name':x['name'],'parent':parent['name'],'finding':'type mismatch'})
  if x['tree']==parent['tree'] and x.get('rowOrder',0)<=parent.get('rowOrder',0):
   tree.append({'id':x['id'],'name':x['name'],'parent':parent['name'],'finding':'source row order inconsistent with parent'})
 # materials: parse original localized crafting, compare per method number of quantities with reference.
 for craft in x.get('craft',[]):
  method=craft['method']; refmethod={'생산':'Create','강화':'Improve'}.get(method)
  if not refmethod:continue
  actual=comps.get(i,[]); ar=[z for z in actual if z['type']==refmethod and z['name_jp'] not in [q['mh4uNameJa'] for q in w if q.get('mh4uWeaponId')==r['parent_id']]];
  if not ar and refmethod=='Improve': ar=[z for z in actual if z['type'].startswith('Create') and z['name_jp'] not in [q['mh4uNameJa'] for q in w if q.get('mh4uWeaponId')==r['parent_id']]]
  # some MH4U components types Create/Improve may be present while Korean source lists only one
  loccounts=[int(t) for t in re.findall(r'[×xX]\s*(\d+)',craft.get('materials',''))]
  refcounts=[int(z['quantity']) for z in ar]
  if not ar:
   material.append({'id':x['id'],'name':x['name'],'method':method,'status':'NO_REFERENCE_RECIPE','ko':craft['materials']});continue
  if sorted(loccounts)!=sorted(refcounts):
   material.append({'id':x['id'],'name':x['name'],'method':method,'status':'QUANTITY_OR_ENTRY_MISMATCH','ko':craft['materials'],'ko_counts':loccounts,'ref_counts':refcounts,'reference':[(z['name_jp'],z['quantity']) for z in ar]})
  else:
   # Counts match does NOT verify ingredient identity. Explicitly track this.
   pass
# Sync nameJa only for changes that share stable id; no values guessed
lookup={x['id']:x for x in w};simchange=0
for x in sim:
 source=lookup.get(x['id']);
 if source and x.get('nameJa')!=source.get('nameJa'):
  x['nameJa']=source['nameJa'];simchange+=1
wpath.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n');spath.write_text(json.dumps(sim,ensure_ascii=False,indent=2)+'\n')
# machine-readable supplement with explicit unresolved identity verification
out={'summary':{'weapons':len(w),'japanese_name_verified_and_corrected':len(changes),'sim_name_synced':simchange,'reference_id_missing':len(problems),'tree_flags':len(tree),'materials_recipe_quantity_flags':len(material),'material_identity_verified':False,'note':'Japanese names corrected using stable pre-linked MH4U IDs; source-localized ingredients are NOT replaced without translation-key identity verification.'},'nameChanges':changes,'noReference':problems,'treeChecks':tree,'materialCountChecks':material}
(root/'data/weapon_audit_followup_20261029.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out['summary'],ensure_ascii=False,indent=2));print('material sample',json.dumps(material[:3],ensure_ascii=False)[:700]);print('tree sample',json.dumps(tree[:3],ensure_ascii=False)[:600])
