#!/usr/bin/env python3
from pathlib import Path
import json,re,collections,datetime
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
load=lambda n: json.loads((D/n).read_text(encoding='utf-8'))
qs=load('quests.json'); mons=load('monster_summary.json'); items=load('items.json')
qidx=load('quest_reference_index.json'); oldq=qidx.get('quests',{})
event=load('event_major_rewards.json').get('quests',{})
iref=load('item_references.json'); mref=load('monster_references.json')
# Canonical monster aliases used by project data.
alias={
'임계 브라키디오스':['맹폭 브라키디오스'],'혼돈의 고어·마가라':['혼돈에 신음하는 고어·마가라','혼돈의 고어마가라'],
'오나즈치':['오오나즈치'],'밀라보레아스':['밀라보레아스 (흑룡)'],'밀라보레아스 (조룡)':['밀라보레아스 (선조룡)'],
'도스재기':['도스 재기'],'게넬·셀타스':['게넬셀타스'],'게넬·셀타스 아종':['게넬셀타스 아종']}
# Quests whose main objective is generic "all large monsters" and therefore cannot be recovered from objective text alone.
manual={
'quest_892cd4874989':['도스이오스','고어·마가라'],
'quest_edb764c92723':['아르셀타스','바바콩가','게리오스'],
'quest_ce42de045bec':['리오레이아','리오레우스','티가렉스'],
'quest_f64398c414f0':['가라라아자라','그라비모스','고어·마가라'],
'quest_b70696983b12':['그라비모스 아종','티가렉스 아종','브라키디오스'],
'quest_3d3cab9ceabc':['진오우거 아종','리오레우스 아종','게넬·셀타스','아르셀타스'],
'quest_34bc81d3575a':['도스이오스','케차와차 아종','가라라아자라'],
'quest_29711c404465':['테츠카브라 아종','리오레우스','디아블로스'],
'quest_ec5e4230105d':['진오우거','가라라아자라 아종','티가렉스','그라비모스'],
'quest_2a1a883d1049':['셀레기오스','디아블로스 아종','라잔'],
'quest_51193dda98d4':['티가렉스','진오우거','브라키디오스','고어·마가라','셀레기오스'],
}
canon_names={m['name'] for m in mons}
for qid,names in manual.items():
    bad=[x for x in names if x not in canon_names]
    if bad: raise SystemExit(f'bad manual monster names {qid}: {bad}')
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
            if not any(i<e and j>s for s,e in occupied):
                occupied.append((i,j)); found.append((i,c))
            start=max(j,i+1)
    out=[]
    for _,c in sorted(found):
        if c not in out: out.append(c)
    return out
# Item label resolver for event rewards.
item_by_label={}
for it in items:
    for k in ('name','nameJa','nameEn'):
        if it.get(k): item_by_label.setdefault(it[k],it)
    for a in it.get('aliases') or []:
        if a:item_by_label.setdefault(a,it)
# Rebuild quest monster lists while preserving imported reward details.
qby={q['id']:q for q in qs}; newq={}
for q in qs:
    qid=q['id']; prev=oldq.get(qid,{})
    explicit=match(' '.join(str(q.get(k,'') or '') for k in ('objective','subObjective')))
    if qid in manual: monster_list=manual[qid]
    elif explicit: monster_list=explicit
    else:
        # Endless hunt objectives omit the monster name; name-based matching is safe only when objective has no explicit monster.
        byname=match(q.get('name',''))
        monster_list=byname or list(prev.get('monsters') or [])
    rewards=list(prev.get('rewardItems') or [])
    details=list(prev.get('rewardDetails') or [])
    for label in event.get(qid,{}).get('rewardLabels') or []:
        it=item_by_label.get(label)
        if it and it['name'] not in rewards:
            rewards.append(it['name']); details.append({'name':it['name'],'source':'event-major-reward'})
    row=dict(prev)
    row.update({'monsters':monster_list,'rewardItems':sorted(dict.fromkeys(rewards)),'rewardDetails':details,
                'location':q.get('location',''),'level':q.get('level',''),'questType':q.get('questType','')})
    newq[qid]=row
qidx['version']='0.7.7-chat4-xref-hotfix7'; qidx['generated']=datetime.datetime.now().isoformat(timespec='seconds'); qidx['quests']=newq
(D/'quest_reference_index.json').write_text(json.dumps(qidx,ensure_ascii=False,indent=2),encoding='utf-8')
# Synchronize item <-> quest reward links without rebuilding unrelated manual/external uses.
iref_items=iref.setdefault('items',{}); item_by_name={it['name']:it for it in items}
for qid,row in newq.items():
    q=qby[qid]
    for name in row.get('rewardItems') or []:
        it=item_by_name.get(name)
        if not it: continue
        ent=iref_items.setdefault(it['id'],{'name':name,'acquire':[],'uses':[]})
        if not any(a.get('type')=='quest' and a.get('id')==qid for a in ent.get('acquire',[])):
            ent.setdefault('acquire',[]).append({'type':'quest','id':qid,'name':q.get('name',''),'questType':q.get('questType',''),'level':q.get('level',''),'location':q.get('location',''),'objective':q.get('objective','')})
# Remove impossible quest links only; leave all other acquisition/use data untouched.
valid=set(qby)
for ent in iref_items.values():
    ent['acquire']=[a for a in ent.get('acquire',[]) if a.get('type')!='quest' or a.get('id') in valid]
    ent['acquire'].sort(key=lambda x:(x.get('type',''),x.get('name',''),x.get('monster',''),str(x.get('no',''))))
iref['version']='0.7.7-chat4-xref-hotfix7'; iref['generated']='2026-10-02'; iref['indexedCount']=len(iref_items)
(D/'item_references.json').write_text(json.dumps(iref,ensure_ascii=False,indent=2),encoding='utf-8')
# Refresh item shards and index from the synchronized monolithic data.
shard=D/'item_refs'; shard.mkdir(exist_ok=True)
iindex={'version':'0.7.7-chat4-xref-hotfix7','generated':'2026-10-02','items':{}}
for iid,v in iref_items.items():
    payload={'id':iid,'acquire':v.get('acquire',[]),'uses':v.get('uses',[])}
    (shard/f'{iid}.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    iindex['items'][iid]={'acquire':len(payload['acquire']),'uses':len(payload['uses'])}
(D/'item_reference_index.json').write_text(json.dumps(iindex,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
# Monster reverse quest lists are now generated only by reversing quest_reference_index.
rev=collections.defaultdict(list)
for q in qs:
    for name in newq[q['id']].get('monsters') or []:
        rev[name].append({k:q.get(k) for k in ['id','questType','questTypeLabel','level','name','objective','location']})
for name,row in mref.items(): row['quests']=rev.get(name,[])
(D/'monster_references.json').write_text(json.dumps(mref,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
# Refresh monster shards/index preserving items/uses.
ms=load('monster_reference_index.json'); mi={}
mdir=D/'monster_refs'; mdir.mkdir(exist_ok=True)
for m in mons:
    name=m['name']; row=mref.get(name,{'monster':name,'items':[],'quests':[],'uses':[]})
    fname=re.sub(r'[^a-z0-9_-]+','-',m['id'].lower())
    (mdir/f'{fname}.json').write_text(json.dumps(row,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    mi[name]={'file':fname,'quests':len(row.get('quests',[])),'uses':len(row.get('uses',[])),'items':len(row.get('items',[]))}
(D/'monster_reference_index.json').write_text(json.dumps({'version':'0.7.7-chat4-xref-hotfix7','items':mi},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('synced quests',len(qs),'items',len(iref_items),'monsters',len(mons))
