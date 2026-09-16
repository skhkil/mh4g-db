#!/usr/bin/env python3
import json,re,sqlite3,datetime,zipfile,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
DB=Path(sys.argv[1]) if len(sys.argv)>1 else None
qs=json.load(open(D/'quests.json',encoding='utf-8'))
mons=json.load(open(D/'monster_summary.json',encoding='utf-8'))
items=json.load(open(D/'items.json',encoding='utf-8'))
iref=json.load(open(D/'item_references.json',encoding='utf-8'))['items']
by_mh={int(x['mh4uId']):x['name'] for x in items if x.get('mh4uId') not in (None,'')}
reward={q['id']:set() for q in qs}; reward_details={q['id']:[] for q in qs}
name_to_ids={}
for q in qs:name_to_ids.setdefault(q.get('name',''),[]).append(q['id'])
for iid,r in iref.items():
    nm=r.get('name','')
    for a in r.get('acquire',[]):
        if a.get('type')!='quest':continue
        ids=[a.get('id')] if a.get('id') in reward else name_to_ids.get(a.get('name',''),[])
        for qid in ids:
            reward[qid].add(nm)
            reward_details[qid].append({'name':nm,'source':'project-xref'})
alias={'임계 브라키디오스':['맹폭 브라키디오스'],'혼돈의 고어·마가라':['혼돈에 신음하는 고어·마가라'],'오나즈치':['오오나즈치'],'밀라보레아스':['밀라보레아스 (흑룡)'],'밀라보레아스 (조룡)':['밀라보레아스 (선조룡)'],'도스재기':['도스 재기'],'게넬·셀타스':['게넬셀타스'],'게넬·셀타스 아종':['게넬셀타스 아종']}
def num(s):
    if s is None:return None
    m=re.search(r'[\d,]+',str(s));return int(m.group().replace(',','')) if m else 0
def star(s):
    m=re.search(r'(\d+)',str(s));return int(m.group(1)) if m else None
def qhub(q): return 'Event' if q.get('questType')=='event' else ('Caravan' if q.get('questType')=='village' else 'Guild')
def qkind(q):return 'Key' if q.get('key') else ('Urgent' if '긴급' in str(q.get('note','')) else 'Normal')
matched=0; ambiguous=0; no_match=0; imported_rows=0
if DB and DB.exists():
    con=sqlite3.connect(DB);con.row_factory=sqlite3.Row
    mqs=con.execute('select * from quests').fetchall()
    for q in qs:
        hub,t,st,fee,rew,tm=qhub(q),qkind(q),star(q.get('level')),num(q.get('fee')),num(q.get('reward')),num(q.get('time'))
        cand=[r for r in mqs if r['hub']==hub and r['stars']==st and r['fee']==fee and r['reward']==rew and r['time_limit']==tm]
        typed=[r for r in cand if r['type']==t]
        cand=typed or cand
        if len(cand)==1:
            matched+=1; mid=cand[0]['_id']
            rows=con.execute('select qr.item_id,qr.reward_slot,qr.percentage,qr.stack_size from quest_rewards qr where qr.quest_id=? order by qr.reward_slot,qr.percentage desc',(mid,)).fetchall()
            seen=set()
            for rr in rows:
                nm=by_mh.get(int(rr['item_id']))
                if not nm:continue
                reward[q['id']].add(nm)
                key=(nm,rr['reward_slot'],rr['percentage'],rr['stack_size'])
                if key not in seen:
                    reward_details[q['id']].append({'name':nm,'slot':rr['reward_slot'],'percentage':rr['percentage'],'quantity':rr['stack_size'],'source':'mh4u-db'});seen.add(key);imported_rows+=1
        elif cand: ambiguous+=1
        else:no_match+=1
idx={'version':'0.7.7-chat4-quest1','generated':datetime.datetime.now().isoformat(timespec='seconds'),'quests':{}}
for q in qs:
    text=' '.join(str(q.get(k,'') or '') for k in ('name','objective','subObjective','conditions','note'))
    found=[]
    for m in mons:
        n=m.get('name',''); names=[n]+alias.get(n,[])
        if any(x and x in text for x in names):found.append(n)
    tags=[]
    if q.get('key'):tags.append('key')
    if '긴급' in str(q.get('note','')):tags.append('urgent')
    if q.get('questType')=='event':tags.append('event')
    if q.get('eventGroup')=='episodic':tags.append('episodic')
    if q.get('questType')=='challenge':tags.append('challenge')
    idx['quests'][q['id']]={'monsters':list(dict.fromkeys(found)),'rewardItems':sorted(reward[q['id']]),'rewardDetails':reward_details[q['id']],'tags':tags,'location':q.get('location',''),'level':q.get('level',''),'questType':q.get('questType','')}
json.dump(idx,open(D/'quest_reference_index.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
audit={'questCount':len(qs),'monsterLinkedQuests':sum(bool(x['monsters']) for x in idx['quests'].values()),'rewardLinkedQuests':sum(bool(x['rewardItems']) for x in idx['quests'].values()),'rewardItemLinks':sum(len(x['rewardItems']) for x in idx['quests'].values()),'mh4uUniqueMatches':matched,'mh4uAmbiguousMatches':ambiguous,'mh4uNoMatches':no_match,'mh4uRewardRowsImported':imported_rows}
json.dump(audit,open(D/'quest_reference_audit_v0.7.7.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print(json.dumps(audit,ensure_ascii=False,indent=2))
