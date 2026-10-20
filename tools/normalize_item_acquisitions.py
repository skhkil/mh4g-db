#!/usr/bin/env python3
"""Audit every monster material acquisition record without fabricating source certainty."""
import json,re,collections,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data/item_references.json'; d=json.loads(p.read_text()); counts=collections.Counter(); methods=collections.Counter(); bad=[]
# Cross-reference only; MH4U is not definitive evidence for MH4G.
mhdb=(ROOT/'sources/mh4u.db') if (ROOT/'sources/mh4u.db').exists() else Path('/mnt/data/mh4u.db')
rewardIndex=collections.defaultdict(set); monsterMap={}
itemIds={item['id']:item.get('mh4uId') for item in json.loads((ROOT/'data/items.json').read_text())}
if mhdb.exists():
 conn=sqlite3.connect(str(mhdb));conn.row_factory=sqlite3.Row
 englishMonsters={r['name'].casefold():r['_id'] for r in conn.execute('select _id,name from monsters')}
 for m in json.loads((ROOT/'data/monster_summary.json').read_text()):
  monsterMap[m['name']]=englishMonsters.get(str(m.get('nameEn','')).casefold())
 for r in conn.execute('select item_id,monster_id,rank,percentage,condition from hunting_rewards'):
  rewardIndex[(r['item_id'],r['monster_id'],r['rank'],r['percentage'])].add(r['condition'])
 conn.close()


def classify(a):
 s=str(a.get('originalMethod') or a.get('method','')).strip()
 if s in ('바람의 헌터',):return 'dispatch_reward','confirmed_category'
 if re.fullmatch(r'최대\s*\d+회',s):return 'possible_drop','needs_source'
 if s in ('유실물','낙하물') or '낙하물' in s:return 'drop','method_explicit'
 if '포획' in s:return 'capture','method_explicit'
 if '갈무리' in s or s in ('꼬리','몸통','입 속','하반신','죽은척 시 갈무리'):return 'carve','method_explicit'
 if '파괴' in s or s in ('머리','등','날개','앞다리','뒷다리','앞발톱','뿔','흉부','발톱','턱','귀','볏','독침','외피','발톱 어느 한쪽이든','등 지느러미','다리','날개다리','앞발','등껍질','집게발','좌날개다리','우날개다리','촉각','분사구','등/날개','머리와 흉부'):return 'part_condition','needs_detail' if '파괴' not in s else 'method_explicit'
 if '채굴' in s or '채집' in s or '광물' in s:return 'gather','method_explicit'
 if '광룡화' in s:return 'frenzy','needs_detail'
 return 'special_condition','needs_detail'

for key,item in d['items'].items():
 for a in item.get('acquire',[]):
  if a.get('type')!='monster':continue
  cat,status=classify(a)
  if a.get('source') and cat=='drop':status='source_attached'
  a['acquisitionCategory']=cat
  a['verificationStatus']=status
  m=re.fullmatch(r'최대\s*(\d+)회',str(a.get('method','')).strip())
  if m:
   a['maxAttempts']=int(m.group(1))
   a['originalMethod']=a['method']
   a['method']='획득 방식 미확인'
  if cat=='possible_drop' and (key.startswith('item_mh4u_') or itemIds.get(key)) and rewardIndex:
   try:
    identity=((int(key.rsplit('_',1)[-1]) if key.startswith('item_mh4u_') else int(itemIds[key])),monsterMap.get(a.get('monster')),{'low':'LR','high':'HR','g':'G','extreme':'G'}.get(a.get('rank')),int(re.sub('[^0-9]','',str(a.get('probability','')))))
    conditions=rewardIndex.get(identity,set())
    if 'Shiny Drop' in conditions:
     a['method']='유실물'
     a['acquisitionCategory']='drop'
     a['verificationStatus']='mh4u_correlated'
     a['corroboration']='MH4U hunting_rewards: Shiny Drop; MH4G source verification pending'
     cat,status='drop','mh4u_correlated'
    elif conditions:
     a['crosscheckNote']='MH4U 같은 확률에 유실물 없음. 획득 방식 미확정.'
   except (ValueError,TypeError):pass
  if a['method']=='바람의 헌터':
   a['originalMethod']=a['method']
   a['method']='떠돌이 헌터 파견 보수'
  if a['method']=='낙하물':
   a['originalMethod']=a['method']
   a['method']='유실물'
  probs=str(a.get('probability','')).strip()
  squashed=re.sub(r'\s+','',probs)
  if probs and squashed!=probs and re.fullmatch(r'(?:100|\d{1,2})(?:\.\d+)?%',squashed):
   a['originalProbability']=probs
   a['probability']=squashed
   a['probabilityNormalization']='removed_internal_whitespace'
   probs=squashed
  if probs and not re.fullmatch(r'(?:100|\d{1,2})(?:\.\d+)?%',probs):bad.append({'item':item['name'],'monster':a.get('monster'),'raw':probs})
  counts[(cat,status)]+=1;methods[a['method']]+=1
 # sync individually served shards
 shard=ROOT/'data/item_refs'/f'{key}.json'
 if shard.exists():
  obj=json.loads(shard.read_text());obj['acquire']=item.get('acquire',[]);shard.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n')
p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
audit={'totalMonsterAcquisitions':sum(counts.values()),'categories':[{'category':c,'verification':s,'count':n} for (c,s),n in sorted(counts.items())],'unvalidatedProbabilities':bad,'unvalidatedProbabilityCount':len(bad),'note':'All records are structured; needs_source/needs_detail remain unverified. Missing methods are NOT asserted as drops.'}
(ROOT/'tools/item_acquisition_full_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'total':audit['totalMonsterAcquisitions'],'count':dict((f'{k[0]}:{k[1]}',v) for k,v in counts.items()),'bad_probabilities':len(bad)},ensure_ascii=False))
