#!/usr/bin/env python3
from pathlib import Path
import json,re,collections,datetime
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
load=lambda n: json.loads((D/n).read_text(encoding='utf-8'))
qs=load('quests.json'); mons=load('monster_summary.json'); qidx=load('quest_reference_index.json'); oldq=qidx.get('quests',{}); mref=load('monster_references.json')
canon_names={m['name'] for m in mons}
alias={
'임계 브라키디오스':['맹폭 브라키디오스'],
'혼돈의 고어·마가라':['혼돈에 신음하는 고어·마가라','혼돈의 고어마가라','혼돈에 신음하는 고어마가라'],
'오나즈치':['오오나즈치'],'밀라보레아스':['밀라보레아스 (흑룡)'],
'밀라보레아스 (조룡)':['밀라보레아스 (선조룡)','조룡 밀라보레아스'],
'밀라보레아스 (홍룡)':['홍룡 밀라보레아스'],'밀라보레아스 (홍염룡)':['홍염룡 밀라보레아스'],
'도스재기':['도스 재기'],'게넬·셀타스':['게넬셀타스'],'게넬·셀타스 아종':['게넬셀타스 아종'],
'녹슨크샬다오라':['녹슨 크샬다오라'],'아르셀타스':['알셀타스'],'아르셀타스 아종':['알셀타스 아종'],
'도스가레오스':['도스가레오'],'네르스큐라':['넬스큐라'],'네르스큐라 아종':['넬스큐라 아종'],
'다라·아마듈라':['다라 아마듈라'],'다라·아마듈라 아종':['다라 아마듈라 아종'],
}
manual={
'quest_892cd4874989':['도스이오스','고어·마가라'],'quest_edb764c92723':['아르셀타스','바바콩가','게리오스'],'quest_ce42de045bec':['리오레이아','리오레우스','티가렉스'],'quest_f64398c414f0':['가라라아자라','그라비모스','고어·마가라'],'quest_b70696983b12':['그라비모스 아종','티가렉스 아종','브라키디오스'],'quest_3d3cab9ceabc':['진오우거 아종','리오레우스 아종','게넬·셀타스','아르셀타스'],'quest_34bc81d3575a':['도스이오스','케차와차 아종','가라라아자라'],'quest_29711c404465':['테츠카브라 아종','리오레우스','디아블로스'],'quest_ec5e4230105d':['진오우거','가라라아자라 아종','티가렉스','그라비모스'],'quest_2a1a883d1049':['셀레기오스','디아블로스 아종','라잔'],'quest_51193dda98d4':['티가렉스','진오우거','브라키디오스','고어·마가라','셀레기오스']}
patterns=[]
for m in mons:
 c=m['name']; labels=[c]+alias.get(c,[])
 for k in ('nameJa','nameEn'):
  if m.get(k): labels.append(m[k])
 for lab in set(labels):
  if lab: patterns.append((lab,c))
patterns.sort(key=lambda x:len(x[0]),reverse=True)
def match(text):
 text=str(text or ''); occupied=[]; found=[]
 for lab,c in patterns:
  start=0
  while True:
   i=text.find(lab,start)
   if i<0: break
   j=i+len(lab)
   if not any(i<e and j>s for s,e in occupied): occupied.append((i,j)); found.append((i,c))
   start=max(j,i+1)
 out=[]
 for _,c in sorted(found):
  if c not in out: out.append(c)
 return out
parent={}
for c in canon_names:
 for suffix in (' 아종',' 희소종'):
  if c.endswith(suffix) and c[:-len(suffix)] in canon_names: parent[c]=c[:-len(suffix)]
parent.update({'녹슨크샬다오라':'크샬다오라','혼돈의 고어·마가라':'고어·마가라','임계 브라키디오스':'브라키디오스','격앙 라잔':'라잔','광폭 이블조':'이블조','밀라보레아스 (홍룡)':'밀라보레아스','밀라보레아스 (홍염룡)':'밀라보레아스','밀라보레아스 (조룡)':'밀라보레아스'})
changes=[]; newq={}
for q in qs:
 qid=q['id']; prev=oldq.get(qid,{})
 main=match(q.get('objective','')) or match(q.get('objectiveEn',''))
 sub=match(q.get('subObjective','')) or match(q.get('subObjectiveEn',''))
 # If the main target is a special form, a generic base-species part-break in the sub target
 # describes the same monster. Do not add a second base monster to the appearance list.
 suppress={parent[c] for c in main if c in parent}
 sub=[c for c in sub if c not in suppress]
 explicit=[]
 for c in main+sub:
  if c not in explicit: explicit.append(c)
 if q.get('_verifiedMonsters'): monsters=list(q['_verifiedMonsters'])
 elif qid in manual: monsters=manual[qid]
 elif explicit: monsters=explicit
 else:
  byname=match(q.get('name',''))
  monsters=byname or list(prev.get('monsters') or [])
 row=dict(prev); row['monsters']=monsters; row['location']=q.get('location',''); row['level']=q.get('level',''); row['questType']=q.get('questType','')
 newq[qid]=row
 if list(prev.get('monsters') or [])!=monsters: changes.append({'id':qid,'name':q.get('name'),'before':prev.get('monsters',[]),'after':monsters})
qidx['version']='0.7.7-chat4-monster-link-hotfix11';qidx['generated']=datetime.datetime.now().isoformat(timespec='seconds');qidx['quests']=newq
(D/'quest_reference_index.json').write_text(json.dumps(qidx,ensure_ascii=False,indent=2),encoding='utf-8')
# True reverse only: never guess monster->quest separately.
rev=collections.defaultdict(list)
for q in qs:
 for name in newq[q['id']].get('monsters') or []:
  rev[name].append({k:q.get(k) for k in ['id','questType','questTypeLabel','level','name','objective','location']})
for name,row in mref.items(): row['quests']=rev.get(name,[])
(D/'monster_references.json').write_text(json.dumps(mref,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
mdir=D/'monster_refs'; mdir.mkdir(exist_ok=True); mi={}
for m in mons:
 name=m['name']; row=mref.get(name,{'monster':name,'items':[],'quests':[],'uses':[]}); fname=re.sub(r'[^a-z0-9_-]+','-',m['id'].lower())
 (mdir/f'{fname}.json').write_text(json.dumps(row,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 mi[name]={'file':fname,'quests':len(row.get('quests',[])),'uses':len(row.get('uses',[])),'items':len(row.get('items',[]))}
(D/'monster_reference_index.json').write_text(json.dumps({'version':'0.7.7-chat4-monster-link-hotfix11','items':mi},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(json.dumps({'questCount':len(qs),'monsterCount':len(mons),'changes':changes},ensure_ascii=False,indent=2))
