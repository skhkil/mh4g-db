import json, sqlite3, csv, os, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'
rec=json.load(open(D/'recommended_loadouts.json',encoding='utf-8'))
armors={x['id']:x for x in json.load(open(D/'armors.json',encoding='utf-8'))}
decos={x['id']:x for x in json.load(open(D/'decorations.json',encoding='utf-8'))}
# used ids
used_arm=[]; used_dec=[]
for e in rec['entries']:
  for v in e.get('variants',[]):
    for a in v.get('build',{}).get('armors',[]): used_arm.append((e['weaponType'],e['rank'],v['label'],a['id']))
    for de in v.get('build',{}).get('decorations',[]): used_dec.append((e['weaponType'],e['rank'],v['label'],de['id']))
used_arm_ids=sorted(set(x[3] for x in used_arm)); used_dec_ids=sorted(set(x[3] for x in used_dec))
# mh4u
con=sqlite3.connect('/mnt/data/mh4u_ref/mh4u.db'); con.row_factory=sqlite3.Row
cur=con.cursor()
mh_arm={r['name']:dict(r) for r in cur.execute('''select i.name,i.name_jp,a.* from items i join armor a on a._id=i._id''')}
mh_dec={r['name']:dict(r) for r in cur.execute('''select i.name,i.name_jp,d.* from items i join decorations d on d._id=i._id''')}
def mh_skills(item_id):
  return {r['name']:r['point_value'] for r in cur.execute('''select st.name,its.point_value from item_to_skill_tree its join skill_trees st on st._id=its.skill_tree_id where its.item_id=?''',(item_id,))}
# Athena parse armor files by JP name
athena={}
partmap={'head':'head.txt','body':'body.txt','arms':'arms.txt','waist':'waist.txt','legs':'legs.txt'}
for part,fn in partmap.items():
  p=Path('/mnt/data/athena_ref/Data')/fn
  with open(p,encoding='utf-8-sig',errors='replace',newline='') as f:
    rows=csv.reader(f)
    next(rows,None)
    for row in rows:
      if not row or not row[0]: continue
      # name, gender,type,rare,slots,hub,village,def,maxdef,fire,water,thunder,ice,dragon, skill pairs...
      try:
        skills={}
        for i in range(14,24,2):
          if i+1<len(row) and row[i].strip() and row[i+1].strip(): skills[row[i].strip()]=int(row[i+1])
        athena[(part,row[0])]={
          'rare':int(row[3]),'slots':int(row[4]),'defense':int(row[7]),'maxDefense':int(row[8]),
          'res':{'fire':int(row[9]),'water':int(row[10]),'thunder':int(row[11]),'ice':int(row[12]),'dragon':int(row[13])},'skills':skills
        }
      except Exception: pass
# skill JP names map project id -> ja/tree English
skills=json.load(open(D/'skills.json',encoding='utf-8'))
skill_by_id={s['id']:s for s in skills}
issues=[]; checked=[]
for aid in used_arm_ids:
  a=armors[aid]; row={'id':aid,'name':a['name'],'nameEn':a.get('nameEn'),'nameJa':a.get('nameJa'),'mh4u':False,'athena':False,'issues':[]}
  m=mh_arm.get(a.get('nameEn',''))
  if m:
    row['mh4u']=True
    for fld, mf in [('defense','defense'),('maxDefense','max_defense'),('slots','num_slots')]:
      if a.get(fld)!=m[mf]:
        (row.setdefault('maxDefenseNotes',[]).append(f'mh4u {fld}: project={a.get(fld)} ref={m[mf]}') if fld=='maxDefense' else row['issues'].append(f'mh4u {fld}: project={a.get(fld)} ref={m[mf]}'))
    for k,mf in [('fire','fire_res'),('water','water_res'),('thunder','thunder_res'),('ice','ice_res'),('dragon','dragon_res')]:
      if a.get('resistances',{}).get(k)!=m[mf]: row['issues'].append(f'mh4u res {k}: project={a.get("resistances",{}).get(k)} ref={m[mf]}')
  at=athena.get((a['part'],a.get('nameJa','')))
  if at:
    row['athena']=True
    for fld in ['defense','maxDefense','slots','rare']:
      if a.get(fld)!=at[fld]:
        (row.setdefault('maxDefenseNotes',[]).append(f'athena {fld}: project={a.get(fld)} ref={at[fld]}') if fld=='maxDefense' else row['issues'].append(f'athena {fld}: project={a.get(fld)} ref={at[fld]}'))
    for k in at['res']:
      if a.get('resistances',{}).get(k)!=at['res'][k]: row['issues'].append(f'athena res {k}: project={a.get("resistances",{}).get(k)} ref={at["res"][k]}')
  if row['issues']: issues.append(row)
  checked.append(row)
# decos, mh4u slots only + athena JP parse
ath_deco={}
with open('/mnt/data/athena_ref/Data/decorations.txt',encoding='utf-8-sig',errors='replace',newline='') as f:
 rows=csv.reader(f); next(rows,None)
 for r in rows:
  if r and r[0]:
   try: ath_deco[r[0]]={'slots':int(r[2])}
   except: pass
for did in used_dec_ids:
 d=decos[did]; row={'id':did,'name':d['name'],'nameEn':d.get('nameEn'),'nameJa':d.get('nameJa'),'mh4u':False,'athena':False,'issues':[]}
 m=mh_dec.get(d.get('nameEn',''))
 if m:
  row['mh4u']=True
  if d['slots']!=m['num_slots']: row['issues'].append(f'mh4u slots: project={d["slots"]} ref={m["num_slots"]}')
 at=ath_deco.get(d.get('nameJa',''))
 if at:
  row['athena']=True
  if d['slots']!=at['slots']: row['issues'].append(f'athena slots: project={d["slots"]} ref={at["slots"]}')
 if row['issues']: issues.append(row)
 checked.append(row)
out={
 'usedArmorIds':len(used_arm_ids),'usedDecorationIds':len(used_dec_ids),
 'armorMh4uMatched':sum(x.get('mh4u',False) for x in checked[:len(used_arm_ids)]),
 'armorAthenaMatched':sum(x.get('athena',False) for x in checked[:len(used_arm_ids)]),
 'criticalIssues':issues,
 'maxDefenseDifferenceCount':sum(1 for x in checked[:len(used_arm_ids)] if x.get('maxDefenseNotes')),
 'maxDefenseNote':'프로젝트 maxDefense는 기존 크롤러의 강화단계 수집 범위 차이로 참조 DB 최종강화치와 다를 수 있음. 추천 구성 검증에서는 초기 방어/슬롯/내성/장비 식별을 우선.',
 'unmatchedArmorMh4u':[x['name'] for x in checked[:len(used_arm_ids)] if not x['mh4u']],
 'unmatchedArmorAthena':[x['name'] for x in checked[:len(used_arm_ids)] if not x['athena']],
}
path=ROOT/'tools'/'recommended_loadouts_ref_crosscheck_v0.7.7.json'
path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
