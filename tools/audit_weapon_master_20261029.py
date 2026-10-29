#!/usr/bin/env python3
"""Conservative MH4U source-backed audit: correct exact-id numerical stats, keep localized crafts and ranks untouched pending translation verification."""
import json,sqlite3,re,collections,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
con=sqlite3.connect(R/'sources/mh4u.db');con.row_factory=sqlite3.Row
ref={r['_id']:dict(r) for r in con.execute('select w.*,i.name as ref_name,i.name_jp as ref_jp,i.rarity as ref_rarity from weapons w join items i on i._id=w._id')}
items={r['_id']:dict(r) for r in con.execute('select _id,name,name_jp from items')}
comps=collections.defaultdict(list)
for r in con.execute('select * from components'):
 r=dict(r)
 if r['type'] in ('Create','Improve'):
  i=items.get(r['component_item_id'],{})
  if r['component_item_id'] not in ref: comps[r['created_item_id']].append({'method':r['type'],'nameJa':i.get('name_jp'),'nameEn':i.get('name'),'count':r['quantity']})
cols=['red','orange','yellow','green','blue','white','purple']
def bar(v):
 a=list(map(int,v.split('.')))
 return {'segments':[{'color':c,'length':q} for c,q in zip(cols,a) if q],'total':sum(a),'raw':v}
def sharp(s,id,r):
 z=s.split(' ')
 if len(z)!=2:return None
 return {'normal':bar(z[0]),'plus':bar(z[1]),'confidence':'high','method':'mh4u-db','coloredDelta':sum(map(int,z[1].split('.')))-sum(map(int,z[0].split('.'))),'source':'MonsterHunter4UDatabase/mh4u.db','sourceWeaponId':id,'sourceName':r['ref_name'],'sourceNameJa':r['ref_jp'],'matchMethod':'mh4uWeaponId'}
ks=['attack','affinity','slots','element','sharpness','rarityRef','rank','craft'];ch=collections.Counter();ex=collections.defaultdict(list);unmatched=[];name_conflicts=[];cross=[]
w=json.loads((R/'data/weapons.json').read_text())
for x in w:
 rid=x.get('mh4uWeaponId'); r=ref.get(rid)
 if not r:
  unmatched.append({'id':x['id'],'name':x['name'],'weaponType':x['weaponType'],'reason':'no MH4U linked ID'});continue
 # Block changes if weapon name is not corroborated by English alias OR normalized Japanese exact match (old source has corrupt JP names).
 jap=lambda s:re.sub(r'\s','',s or '').replace('・','').replace('＝','=')
 en=lambda s:re.sub(r'[^a-z0-9]','',(s or '').lower())
 corroborated=(jap(x.get('nameJa'))==jap(r['ref_jp']) or en(x.get('nameEn'))==en(r['ref_name']) or (x['id']=='weapon_88aae60aa94c' and rid==5673))
 if not corroborated:
  name_conflicts.append({'id':x['id'],'name':x['name'],'nameJa':x.get('nameJa'),'matchedRef':r['ref_name'],'matchedRefJa':r['ref_jp']});continue
 def setval(k,v):
  if x.get(k)!=v:
   ch[k]+=1
   if len(ex[k])<30:ex[k].append({'id':x['id'],'name':x['name'],'old':x.get(k),'new':v})
   x[k]=v
 setval('attack',int(r['attack'] or 0));setval('slots',int(r['num_slots'] or 0));setval('rarityRef',int(r['ref_rarity'] or 0))
 aff=str(r['affinity'] or '0');setval('affinityText',aff)
 # leave numerical affinity when multiple conditional states exist; retain original textual fidelity
 if re.fullmatch(r'-?\d+',aff):setval('affinity',int(aff))
 t={'Fire':'불','Water':'물','Thunder':'번개','Ice':'얼음','Dragon':'용','Poison':'독','Paralysis':'마비','Sleep':'수면','Blast':'폭파','Blastblight':'폭파'}
 def elem(k,n):return {'type':t.get(r[k],r[k]),'value':int(r[n])} if r[k] and r[n] not in ('',None) else None
 e1=elem('element','element_attack');e2=elem('element_2','element_2_attack');ea=elem('awaken','awaken_attack')
 for k,v in [('elementPrimary',e1),('elementSecondary',e2),('awakenElement',ea),('defenseBonus',int(r['defense'] or 0))]:setval(k,v)
 display=' · '.join([f"{e['type']} {e['value']}" for e in (e1,e2) if e]+([f"각성 {ea['type']} {ea['value']}"] if ea else [])+([f"방어+{r['defense']}"] if int(r['defense'] or 0) else []))
 setval('element',display)
 if r['sharpness'] and x['weaponType'] not in ('라이트보우건','헤비보우건','활'):
  sh=sharp(r['sharpness'],rid,r)
  if sh and x.get('sharpness')!=sh:setval('sharpness',sh)
 # audit crafting materials without overwriting official Korean source localized names
 if x.get('craft'):cross.append({'id':x['id'],'name':x['name'],'sourceCraft':x['craft'],'mh4uMaterials':comps[rid]})
 # rank/weaponLevel are NOT rarity. Don't silently conflate them.
open(R/'data/weapons.json','w').write(json.dumps(w,ensure_ascii=False,indent=2)+'\n')
simpath=R/'data/sim_weapons.json';sim=json.loads(simpath.read_text());lookup={x['id']:x for x in w};keys=['attack','affinity','affinityText','slots','element','elementPrimary','elementSecondary','awakenElement','defenseBonus','sharpness','rarityRef']
for x in sim:
 t=lookup.get(x['id']);
 if t:
  for k in keys:
   if k in t:x[k]=t[k]
simpath.write_text(json.dumps(sim,ensure_ascii=False,separators=(',',':')))
report={'summary':{'total':len(w),'sourceMatched':len(w)-len(unmatched)-len(name_conflicts),'unmatched':len(unmatched),'nameConflictUnchanged':len(name_conflicts),'changedFields':dict(ch),'craftsComparedNotOverwritten':len(cross),'notice':'원본 DB로 자동 교차검증 가능한 값만 변경. 레벨(강화 트리 단계)과 한국판 소재명/제작 유형은 자동 치환 금지; 확인된 참고 정보를 따로 보관.'},'sampleChanges':dict(ex),'sourceOnly':unmatched,'nameConflicts':name_conflicts,'craftCrosschecks':cross}
(R/'data/weapon_full_audit_20261029.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
