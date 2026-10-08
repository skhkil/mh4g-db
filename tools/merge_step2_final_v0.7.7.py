#!/usr/bin/env python3
import json, sqlite3, shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1]
DATA=P/'data'
OLD=Path('/mnt/data/mh4g_step2')
DB=Path('/mnt/data/mh4g_step2_final_work/external/mh4u.db')

def load(p): return json.load(open(p,encoding='utf-8'))
def dump(obj,p,compact=False):
    with open(p,'w',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=None if compact else 2,separators=(',',':') if compact else None)

# Preserve audit inputs inside release tree.
shutil.copy2(OLD/'data/quest_item_external_manifest_step2.json', DATA/'quest_item_external_manifest_step2.json')
shutil.copy2(OLD/'data/quest_reference_audit_v0.7.7.json', DATA/'quest_reference_audit_step2_source_v0.7.7.json')
manifest=load(DATA/'quest_item_external_manifest_step2.json')
audit=load(DATA/'quest_reference_audit_step2_source_v0.7.7.json')
quests=load(DATA/'quests.json')
qref_old=load(DATA/'quest_reference_index.json')
items=load(DATA/'items.json')
monster_refs=load(DATA/'monster_references.json')

# Japanese MH4G DLC rows restored in prior STEP 2. Exact Japanese names are the manifest keys.
# The fields below are conservative display metadata; reward relations are rebuilt from the verified manifest.
events=[
('USJ・火竜達の舞い','USJ·화룡들의 춤','low','★3','리오레우스 2마리 수렵','천공산','1,400z','13,800z','리오레우스'),
('JUMP・新たなライバル！','JUMP·새로운 라이벌!','low','★2','브라키디오스와 고어·마가라 수렵','격투장','1,300z','12,000z','브라키디오스|고어·마가라'),
('ケロロ軍曹・スカウト大作戦','케로로 중사·스카우트 대작전','low','★2','테츠카브라와 자보아자길 수렵','빙해','700z','6,000z','테츠카브라|자보아자길'),
('ネギま！・闇の世界に忍ぶ影','네기마!·어둠의 세계에 숨은 그림자','low','★3','푸루푸루 1마리 수렵','지저 동굴','700z','6,000z','푸루푸루'),
('武装戦線・男たちの覚悟！','무장전선·남자들의 각오!','low','★3','아르셀타스와 게넬·셀타스 수렵','격투장','800z','7,200z','아르셀타스|게넬·셀타스'),
('ファミ通・突進と回転の脅威','패미통·돌진과 회전의 위협','low','★3','리노프로스 10마리와 스쿠아길 10마리 토벌','격투장','300z','2,400z','게리오스'),
('犬夜叉・大妖の牙を巡る狩猟','이누야샤·대요괴의 이빨을 둘러싼 수렵','low','★3','가라라아자라 1마리 수렵','격투장','700z','6,600z','가라라아자라'),
('USJ・ザボアザギル3D','USJ·자보아자길 3D','high','★5','자보아자길 1마리 수렵','빙해','700z','6,900z','자보아자길'),
('JUMP・黒雷に染まる銀世界','JUMP·흑뢰로 물든 은세계','high','★6','진오우거 아종 1마리 수렵','빙해','1,500z','14,400z','진오우거 아종'),
('JUMP・決戦、炎の王！！','JUMP·결전, 불꽃의 왕!!','high','★7','테오·테스카토르 1마리 토벌','용암도','2,200z','21,600z','테오·테스카토르'),
('OP・最強の宴','OP·최강의 연회','high','★7','격앙 라잔과 광폭 이블조 수렵','격투장','2,600z','25,200z','격앙 라잔|광폭 이블조'),
('OP・氷の国から来た牙獣','OP·얼음 나라에서 온 아수','high','★5','울크스스 1마리 수렵','격투장','500z','4,200z','울크스스'),
('クローズ・ヘッド達の激突！','크로우즈·헤드들의 격돌!','high','★5','도스이오스 2마리 수렵','용암도','700z','6,900z','도스이오스'),
('範馬刃牙・地上最強の食卓','한마 바키·지상 최강의 식탁','high','★7','이블조 1마리 수렵','지저 화산','1,900z','18,000z','이블조'),
('範馬刃牙・男一代','한마 바키·남자 일대','high','★7','브라키디오스 1마리 수렵','격투장','1,300z','12,600z','브라키디오스'),
('ファミ通・ケチャワチャ包囲網','패미통·케차와차 포위망','high','★4','케차와차 2마리 수렵','투기장','900z','8,700z','케차와차'),
('サンデー・闇に巣食う者','선데이·어둠에 둥지 튼 자','high','★5','네르스큐라 1마리 수렵','지저 동굴','800z','7,800z','네르스큐라'),
('銀の匙・卵の試食パーティ','은수저·알 시식 파티','high','★4','비룡의 알 5개 납품','천공산','600z','5,400z',''),
('コロコロ・モンスターじゃい！','코로코로·몬스터다!','high','★7','쿤추 12마리 토벌','격투장','600z','5,400z',''),
('電撃・赤き飛竜の双雷','전격·붉은 비룡의 쌍뢰','high','★4','푸루푸루 아종 2마리 수렵','지저 동굴','1,500z','14,400z','푸루푸루 아종'),
('電撃・閃烈なる狩人達','전격·섬렬한 사냥꾼들','high','★6','진오우거 2마리 수렵','격투장','2,000z','19,200z','진오우거'),
('ファミ通・特別取材、天廻龍','패미통·특별취재, 천회룡!','g','G★3','샤가르마가라 1마리 토벌','금지된 땅','2,200z','21,900z','샤가르마가라'),
('七つの大罪・魔神の眷属','일곱 개의 대죄·마신의 권속','g','G★1','가라라아자라 1마리 수렵','원생림','1,300z','12,600z','가라라아자라'),
]
existing_ja={q.get('nameJa') for q in quests}
restored=[]
for i,e in enumerate(events,1):
    ja,ko,grp,level,obj,loc,fee,reward,mons=e
    if ja in existing_ja: continue
    qid=f'event-step2-jp-{i:03d}'
    q={'id':qid,'questType':'event','questTypeLabel':'이벤트','eventGroup':grp,'eventSeries':'일본 MH4G DLC','level':level,'key':False,
       'name':ko,'nameJa':ja,'nameEn':'','objective':obj,'location':loc,'fee':fee,'reward':reward,'hrp':'','time':'50분','conditions':'DLC 이벤트',
       'subObjective':'','subReward':'-','note':'STEP 2 일본 MH4G 이벤트 복원','source':'https://w.atwiki.jp/3dsmh4g/pages/173.html'}
    quests.append(q); restored.append(qid)
assert restored==manifest['restoredQuestIds'], (restored,manifest['restoredQuestIds'])
dump(quests,DATA/'quests.json')

# Rebuild canonical Quest -> Item from exact validated prior match manifest + MH4U DB.
by_mh4u={int(x['mh4uId']):x for x in items if x.get('mh4uId') not in (None,'')}
by_name={x['name']:x for x in items}
conn=sqlite3.connect(DB)
cur=conn.cursor()
base_qrefs=qref_old.get('quests',{})
qby={q['id']:q for q in quests}
qrefs={}
for q in quests:
    prev=base_qrefs.get(q['id'],{})
    qrefs[q['id']]={'monsters':list(prev.get('monsters') or []),'rewardItems':[],'rewardDetails':[],
                    'tags':list(prev.get('tags') or (['event'] if q.get('questType')=='event' else [])),
                    'location':q.get('location',''),'level':q.get('level',''),'questType':q.get('questType','')}
# Exact monster lists for restored 23: total +25, matching prior STEP2 audit total 611.
mons_by_ja={e[0]:([x for x in e[8].split('|') if x]) for e in events}
for q in quests:
    if q['id'] in restored: qrefs[q['id']]['monsters']=mons_by_ja[q['nameJa']]

imported_rows=0
for qid,meta in audit['matchMethods'].items():
    if qid not in qrefs: raise SystemExit(f'missing matched quest {qid}')
    mid=int(meta['mh4uQuestId'])
    rows=cur.execute('select item_id,reward_slot,percentage,stack_size from quest_rewards where quest_id=?',(mid,)).fetchall()
    seen_det=set()
    for item_id,slot,pct,stack in rows:
        it=by_mh4u.get(int(item_id))
        if not it: continue
        name=it['name']; qrefs[qid]['rewardItems'].append(name)
        sig=(name,slot,pct,stack)
        if sig not in seen_det:
            seen_det.add(sig); imported_rows+=1
            qrefs[qid]['rewardDetails'].append({'name':name,'rewardSlot':slot,'percentage':pct,'stackSize':stack,'source':'MH4U DB','mh4uQuestId':mid})
# Add the 41 independently verified Japanese MH4G DLC unique reward pairs.
by_ja={q.get('nameJa'):q for q in quests}
for pair in manifest['verifiedPairs']:
    q=by_ja.get(pair['questNameJa']); item=by_name.get(pair['itemName'])
    if not q or not item: raise SystemExit(f'bad verified pair {pair}')
    row=qrefs[q['id']]; row['rewardItems'].append(item['name'])
    row['rewardDetails'].append({'name':item['name'],'source':'MH4G event verified manifest'})
for r in qrefs.values():
    r['rewardItems']=sorted(dict.fromkeys(r['rewardItems']))
# Canonical output.
out={'version':'0.7.7-step2-final-xref','generated':'2026-10-08','quests':qrefs}
dump(out,DATA/'quest_reference_index.json')
conn.close()

reward_links=sum(len(r['rewardItems']) for r in qrefs.values())
monster_links=sum(len(r['monsters']) for r in qrefs.values())
print('quests',len(quests),'restored',len(restored),'matched',len(audit['matchMethods']))
print('reward links',reward_links,'mh4u detail rows',imported_rows,'monster links',monster_links)
assert len(quests)==595
assert reward_links==5539, reward_links
assert imported_rows==8042, imported_rows
assert monster_links==610, monster_links
assert len(manifest['verifiedPairs'])==41
