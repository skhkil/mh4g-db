from pathlib import Path
import json, re
R=Path(__file__).resolve().parents[1];D=R/'data'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v,pretty=True):p.write_text(json.dumps(v,ensure_ascii=False,indent=2 if pretty else None,separators=None if pretty else (',',':'))+'\n',encoding='utf-8')
items=load(D/'item_references.json');mon=load(D/'monster_references.json');idx=load(D/'monster_reference_index.json');rewards=load(D/'monster_rewards.json')
names=['다라·아마듈라','다라·아마듈라 아종']
notes={'운석 채굴':'운석 공격 후 드물게 남는 잔해를 곡괭이로 채굴. 시간이 지나면 사라짐','머리 올라타기':'머리 1단계 파괴 후 휘감은 상태에서 머리로 이동해 갈무리','몸통':'토벌 후 상반신 갈무리','꼬리':'꼬리 부위. 토벌 후 하반신 갈무리와 절단된 꼬리 갈무리는 별개','등':'등 2단계 부위 파괴 보수','앞다리':'좌우 앞다리 모두 파괴 보수','흉부':'흉부 2단계 파괴 보수','뒷다리':'뒷다리 부위 파괴 보수','하반신':'하반신 갈무리 또는 부위 파괴 보수. 보상 타입은 각 기록 참조','머리':'머리 2단계 부위 파괴 보수'}
# Resolve implicit part-break methods inherited from source table rows, without altering raw method.
for m in names:
 rows=[x for x in rewards if x['monster']==m]; part=None
 for x in rows:
  method=x['method'];count=x.get('count','')
  if method in ('머리','흉부','등','앞다리','뒷다리','하반신'):part=method
  if method in ('2회 파괴 시 보수','좌우모두 파괴 시 보수','파괴 시 보수'):
   x['part']=part or '부위 확인 필요';x['acquisitionCategory']='part_break';x['conditionNote']=f'{part} {method}' if part else method
  elif method=='운석 채굴': x['acquisitionCategory']='gather';x['conditionNote']=notes[method]
  elif method=='머리 올라타기':x['acquisitionCategory']='carve';x['conditionNote']=notes[method]
  if x.get('part') in ('부위 확인 필요',): x['verificationStatus']='part_ambiguous'
  elif x.get('conditionNote'):x['verificationStatus']='mh4g_wiki_condition_checked'
# Rebuild missing reverse material/gear usages from existing item-level sources.
for m in names:
 row=mon[m];match=[];uses=[];seen=set()
 for itemid,iv in items['items'].items():
  ac=iv.get('acquire',[])
  if iv['name'].startswith('사왕룡' if m==names[0] else '사황룡') and any(a.get('type')=='monster' and a.get('monster')==m for a in ac):
   match.append({'name':iv['name'],'id':itemid})
   for u in iv.get('uses',[]):
    key=(u.get('type'),u.get('id'),u.get('name'),u.get('result'))
    if key not in seen:uses.append(u);seen.add(key)
 row['items']=sorted(match,key=lambda a:a['name']);row['uses']=uses
 meta=idx['items'][m];meta['items']=len(row['items']);meta['uses']=len(row['uses'])
 save(D/'monster_refs'/f"{meta['file']}.json",row,False)
# Synchronize enriched reward descriptions to item reference records where no ambiguity is introduced.
# Do not overwrite percentages or change item display names.
for r in rewards:
 if r['monster'] not in names:continue
 for itemid,iv in items['items'].items():
  if iv['name']!=r['item']:continue
  for a in iv.get('acquire',[]):
   if a.get('type')=='monster' and a.get('monster')==r['monster'] and a.get('rank')==r['rank'] and a.get('method')==r['method'] and a.get('probability')==r['probability']:
    if 'conditionNote' in r:a['conditionNote']=r['conditionNote']
    if 'part' in r:a['part']=r['part']
    if r.get('verificationStatus')=='part_ambiguous':a['verificationStatus']='part_ambiguous'
for id,v in items['items'].items():
 shard=D/'item_refs'/f'{id}.json'
 if shard.exists() and load(shard)!=v:save(shard,v,False)
save(D/'item_references.json',items);save(D/'monster_references.json',mon);save(D/'monster_reference_index.json',idx);save(D/'monster_rewards.json',rewards)
report={'scope':'MH4G Dalamadur normal/subspecies link and condition repair','monsters':{n:{'materials':len(mon[n]['items']),'uses':len(mon[n]['uses']),'rewards':len([r for r in rewards if r['monster']==n])} for n in names},'sourceURLs':['https://w.atwiki.jp/3dsmh4g/pages/331.html','https://w.atwiki.jp/3dsmh4g/pages/371.html','https://mh4info.com/m/d/103'],'warning':'Acquisition probabilities remain sourced from original database, not all independently verified against MH4G Japanese primary material'}
save(R/'tools/dalamadur_integration_audit.json',report)
print(json.dumps(report,ensure_ascii=False))
