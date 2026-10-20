#!/usr/bin/env python3
"""Enrich monster reward route from an *optional* MH4U reference DB.
Keep MH4G certainty distinct. Does not choose among ambiguous reward matches.
"""
import json,sqlite3,collections,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data/item_references.json';D=json.loads(P.read_text());ITEMS={x['id']:x.get('mh4uId') for x in json.loads((ROOT/'data/items.json').read_text())}
DB=(ROOT/'sources/mh4u.db') if (ROOT/'sources/mh4u.db').exists() else Path('/mnt/data/mh4u.db');assert DB.exists(), 'MH4U reference database missing'
conn=sqlite3.connect(str(DB));conn.row_factory=sqlite3.Row
mons={x['name'].casefold():x['_id'] for x in conn.execute('select _id,name from monsters')}
MONS={x['name']:mons.get(x.get('nameEn','').casefold()) for x in json.loads((ROOT/'data/monster_summary.json').read_text())}
INDEX=collections.defaultdict(set)
for x in conn.execute('select item_id,monster_id,rank,percentage,condition from hunting_rewards'):
 INDEX[(x['item_id'],x['monster_id'],x['rank'],x['percentage'])].add(x['condition'])
conn.close()
CONDS={'Break Head':'머리','Break Back':'등','Break Wing':'날개','Break Front Leg':'앞다리','Break Back Leg':'뒷다리','Break Horn':'뿔','Break Ear':'귀','Break Tail':'꼬리','Break Belly':'배','Break Claw':'발톱','Break Talon':'발톱','Break Wing Leg':'날개다리','Break Chest':'가슴','Break Blowhole':'분사구','Break Fin':'등지느러미','Break Jaw':'턱','Break Shell':'껍질','Break Poison Stinger':'독침','Break Body':'몸통','Break Beak':'부리','Break Antenna':'촉각','Break Leg':'다리','Break Cover Skin':'외피','Break Eye':'눈'}
changes=collections.Counter()
for key,item in D['items'].items():
 iid=int(key.rsplit('_',1)[-1]) if key.startswith('item_mh4u_') else ITEMS.get(key)
 for a in item['acquire']:
  if a.get('type')!='monster':continue
  prob=a.get('probability','').strip().rstrip('%');rank={'low':'LR','high':'HR','g':'G','extreme':'G'}.get(a.get('rank'))
  if not iid or not prob.isdigit():continue
  conditions=INDEX.get((int(iid),MONS.get(a.get('monster')),rank,int(prob)),set())
  if not conditions:continue
  cat=a.get('acquisitionCategory');status=a.get('verificationStatus')
  # Distinct drop subtypes are valid drop routes; do not conflate tail/body carves.
  if cat=='possible_drop':
   shiny={x for x in conditions if x.startswith('Shiny Drop')}
   if shiny:
    a['method']='유실물'
    a['acquisitionCategory']='drop'
    a['verificationStatus']='mh4u_correlated'
    a['corroboration']='MH4U hunting_rewards: '+', '.join(sorted(shiny))+'; MH4G original pending'
    if len(shiny)==1 and next(iter(shiny))!='Shiny Drop':
     detail=next(iter(shiny))[len('Shiny Drop'):].strip(' ()')
     a['dropVariantMh4u']=detail
    changes['drop_more']+=1
  elif cat=='part_condition' and (status=='needs_detail' or (status=='method_explicit' and a.get('method') in ('파괴 시 보수','2회 파괴 시 보수','양쪽 파괴 시 보수','좌우모두 파괴 시 보수'))):
   found=[x for x in conditions if x in CONDS]
   if len(found)==1 and len(conditions)==1:
    original=a['method']
    if original in ('머리','등','날개','앞다리','뒷다리','뿔','귀','날개다리','발톱','배','흉부','볏','외피','독침'):
     a['method']=original+' 파괴 보수'
    elif original=='파괴 시 보수':
     a['method']=CONDS[found[0]]+' 파괴 보수'
    elif original=='2회 파괴 시 보수':
     a['method']=CONDS[found[0]]+' 2회 파괴 보수'
    elif original in ('양쪽 파괴 시 보수','좌우모두 파괴 시 보수'):
     a['method']=CONDS[found[0]]+' 양쪽 파괴 보수'
    else:
     a['method']=original+' · '+CONDS[found[0]]+' 파괴'
    a['originalMethod']=original
    a['verificationStatus']='mh4u_correlated'
    a['corroboration']='MH4U hunting_rewards: '+found[0]+'; MH4G original pending'
    changes['part_more']+=1
  elif cat=='frenzy' and status=='needs_detail' and conditions=={'Virus Reward'}:
   a['verificationStatus']='mh4u_correlated'
   a['corroboration']='MH4U hunting_rewards: Virus Reward; MH4G original pending'
   a['method']='광룡화 관련 보수'
   changes['frenzy_more']+=1
 # Sync individually used shards, not just consolidated dataset.
 shard=ROOT/'data/item_refs'/f'{key}.json'
 if shard.is_file():
  j=json.loads(shard.read_text());j['acquire']=item.get('acquire',[]);shard.write_text(json.dumps(j,ensure_ascii=False,separators=(',',':'))+'\n')
P.write_text(json.dumps(D,ensure_ascii=False,separators=(',',':'))+'\n')
(ROOT/'tools/item_acquisition_crosscheck_report.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
print(dict(changes))
