#!/usr/bin/env python3
from pathlib import Path
import json,glob,datetime
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'
qpath=D/'quests.json'
qs=json.load(open(qpath,encoding='utf-8'))
byid={q['id']:q for q in qs}

# 1) Existing aliases/canonical localization fixes.
kirin=byid.get('event-high-020')
if kirin:
    aliases=set(kirin.get('aliases') or [])
    aliases.update(['Kirin Aquisition'])
    kirin['aliases']=sorted(aliases)

hunter=byid.get('event-g-043')
if hunter:
    hunter['nameJa']='ハンター日誌　怪鳥の回'
    aliases=set(hunter.get('aliases') or [])
    aliases.update(['헌터 일지 괴조 편','헌터일지 괴조의 회','Hunter\'s Log: Yian Kut-Ku'])
    hunter['aliases']=sorted(aliases)

# 2) True missing event quest from material-source data.
jump_id='event-g-079'
if jump_id not in byid:
    jump={
      'id':jump_id,'questType':'event','questTypeLabel':'이벤트','eventGroup':'g','eventSeries':'JUMP',
      'level':'G★3','key':False,'name':'JUMP·작열연투!','nameJa':'JUMP・灼熱燃闘！','nameEn':'',
      'aliases':['JUMP・작열열투!','JUMP 작열전투','JUMP·작열연투'],
      'objective':'테오·테스카토르 토벌 또는 격퇴','objectiveEn':'Slay or repel a Teostra',
      'location':'구사막<낮>','fee':'3,100z','reward':'30,300z','hrp':'-','time':'35분',
      'conditions':'G★3 허가증 · DLC 이벤트','subObjective':'','subObjectiveEn':'','subReward':'-','subHrp':'-',
      'note':'주요 보수: 반역Ｊ티켓 · 대장로티켓S / 사용처: 반역왕J 시리즈',
      'source':'MH4G 국내 인벤 보수표 + MH4G@wiki/Japanese quest data cross-check'
    }
    # append to end of event G section / quests list. UI sorts by existing order; G★3 tail is acceptable.
    qs.append(jump)
    byid[jump_id]=jump

json.dump(qs,open(qpath,'w',encoding='utf-8'),ensure_ascii=False,indent=2)

# 3) Canonicalize material-source quest objects so navigation points at actual quest IDs.
replaced={'kirin_typo':0,'hunter_alias':0,'jump_missing':0}
for p in glob.glob(str(D/'armor_progressions'/'*.json')):
    obj=json.load(open(p,encoding='utf-8'))
    changed=False
    def patch(s):
        nonlocal_dummy=None
    for mat in obj.get('materials',[]):
        for s in mat.get('sources',[]):
            if s.get('type')!='quest': continue
            n=s.get('name',''); ne=s.get('nameEn',''); nj=s.get('nameJa','')
            if n=='Kirin Aquisition' or ne=='Kirin Aquisition':
                q=byid['event-high-020']; s.update({'id':q['id'],'name':q['name'],'nameJa':q.get('nameJa',''),'nameEn':q.get('nameEn',''),'level':q['level'],'questType':'event','location':q.get('location',''),'objective':q.get('objective','')}); replaced['kirin_typo']+=1;changed=True
            elif n=='헌터 일지 괴조 편' or nj=='ハンター日誌　怪鳥の回':
                q=byid['event-g-043']; s.update({'id':q['id'],'name':q['name'],'nameJa':q.get('nameJa',''),'nameEn':q.get('nameEn',''),'level':q['level'],'questType':'event','location':q.get('location',''),'objective':q.get('objective','')}); replaced['hunter_alias']+=1;changed=True
            elif n=='JUMP・작열열투!' or nj=='JUMP・灼熱燃闘！':
                q=byid[jump_id]; s.update({'id':q['id'],'name':q['name'],'nameJa':q.get('nameJa',''),'nameEn':q.get('nameEn',''),'level':q['level'],'questType':'event','location':q.get('location',''),'objective':q.get('objective','')}); replaced['jump_missing']+=1;changed=True
    # targets quests contain same refs independently
    for s in obj.get('targets',{}).get('quests',[]):
        n=s.get('name',''); ne=s.get('nameEn',''); nj=s.get('nameJa','')
        if n=='Kirin Aquisition' or ne=='Kirin Aquisition':
            q=byid['event-high-020']; s.update({'id':q['id'],'name':q['name'],'nameJa':q.get('nameJa',''),'nameEn':q.get('nameEn',''),'level':q['level'],'questType':'event','location':q.get('location',''),'objective':q.get('objective','')}); changed=True
        elif n=='헌터 일지 괴조 편' or nj=='ハンター日誌　怪鳥の回':
            q=byid['event-g-043']; s.update({'id':q['id'],'name':q['name'],'nameJa':q.get('nameJa',''),'nameEn':q.get('nameEn',''),'level':q['level'],'questType':'event','location':q.get('location',''),'objective':q.get('objective','')}); changed=True
        elif n=='JUMP・작열열투!' or nj=='JUMP・灼熱燃闘！':
            q=byid[jump_id]; s.update({'id':q['id'],'name':q['name'],'nameJa':q.get('nameJa',''),'nameEn':q.get('nameEn',''),'level':q['level'],'questType':'event','location':q.get('location',''),'objective':q.get('objective','')}); changed=True
    if changed: json.dump(obj,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)

# 4) Quest reference index entry for the new quest.
rpath=D/'quest_reference_index.json'
r=json.load(open(rpath,encoding='utf-8'))
r.setdefault('quests',{})[jump_id]={
 'monsters':['테오·테스카토르'],
 'rewardItems':['대장로티켓S','반역Ｊ티켓'],
 'rewardDetails':[{'name':'반역Ｊ티켓','source':'MH4G event reward cross-check'},{'name':'대장로티켓S','source':'MH4G event reward cross-check'}],
 'tags':['event'],'location':'구사막<낮>','level':'G★3','questType':'event'
}
r['generated']=datetime.datetime.now().isoformat(timespec='seconds')
json.dump(r,open(rpath,'w',encoding='utf-8'),ensure_ascii=False,indent=2)

# 5) Event-major rewards for immediate UI visibility.
epath=D/'event_major_rewards.json'
e=json.load(open(epath,encoding='utf-8'))
e.setdefault('quests',{})[jump_id]={'rewardLabels':['반역Ｊ티켓','대장로티켓S'],'source':'MH4G 국내 인벤 + MH4G Japanese event data'}
e['generated']=datetime.datetime.now().isoformat(timespec='seconds')
json.dump(e,open(epath,'w',encoding='utf-8'),ensure_ascii=False,indent=2)

print(json.dumps({'ok':True,'questCount':len(qs),'replaced':replaced,'newQuest':byid[jump_id]},ensure_ascii=False,indent=2))
