#!/usr/bin/env python3
from pathlib import Path
import json,glob,re,unicodedata,datetime,collections
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data'
qs=json.load(open(D/'quests.json',encoding='utf-8'))
def norm(s):
 s=unicodedata.normalize('NFKC',str(s or '')).lower()
 return re.sub(r'[\s・･·:：!！?？,，.。\-—–_「」『』\[\]()（）<>＜＞]+','',s)
idx=collections.defaultdict(list)
for q in qs:
 for v in [q.get('name'),q.get('nameJa'),q.get('nameEn'),*(q.get('aliases') or [])]:
  if v: idx[norm(v)].append(q['id'])
refs=[]
for p in glob.glob(str(D/'armor_progressions'/'*.json')):
 d=json.load(open(p,encoding='utf-8'))
 for m in d.get('materials',[]):
  for s in m.get('sources',[]):
   if s.get('type')=='quest' and str(s.get('questType','')).lower()=='event': refs.append((Path(p).name,m.get('name'),s))
uniq={}
for fn,mat,s in refs:
 k=(s.get('id',''),s.get('name',''),s.get('nameJa',''),s.get('nameEn',''),s.get('level',''))
 uniq.setdefault(k,[]).append((fn,mat))
unmatched=[];bad_ids=[]
qids={q['id'] for q in qs}
for k,uses in uniq.items():
 qid,name,nj,ne,level=k
 found=[]
 if qid:
  if qid in qids: found=[qid]
  else: bad_ids.append({'id':qid,'name':name,'uses':uses[:5]})
 if not found:
  for v in (name,nj,ne):
   if v: found.extend(idx.get(norm(v),[]))
 if not found: unmatched.append({'name':name,'nameJa':nj,'nameEn':ne,'level':level,'uses':uses[:10]})
# targeted canonical checks
checks={
 'jump_exists':any(q.get('nameJa')=='JUMP・灼熱燃闘！' and q.get('questType')=='event' for q in qs),
 'jump_korean_name':any(q.get('name')=='JUMP·작열연투!' for q in qs),
 'hunter_alias_bound':any(q.get('id')=='event-g-043' and '헌터 일지 괴조 편' in (q.get('aliases') or []) for q in qs),
 'kirin_typo_bound':any(q.get('id')=='event-high-020' and 'Kirin Aquisition' in (q.get('aliases') or []) for q in qs),
}
rep={'version':'0.7.7-hotfix5','generated':datetime.datetime.now().isoformat(timespec='seconds'),'questCount':len(qs),'eventQuestCount':sum(q.get('questType')=='event' for q in qs),'eventMaterialReferenceRows':len(refs),'eventMaterialReferenceUnique':len(uniq),'unmatchedEventMaterialReferences':unmatched,'badEventQuestIds':bad_ids,'checks':checks}
rep['ok']=not unmatched and not bad_ids and all(checks.values())
out=ROOT/'tools'/'material_event_quest_link_audit_hotfix5_v0.7.7.json';out.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rep,ensure_ascii=False,indent=2));raise SystemExit(0 if rep['ok'] else 1)
