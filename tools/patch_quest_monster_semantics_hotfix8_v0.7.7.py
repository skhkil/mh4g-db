#!/usr/bin/env python3
from pathlib import Path
import json, copy
ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'data'/'quests.json'
qs=json.loads(P.read_text(encoding='utf-8')); byid={q['id']:q for q in qs}

def fix(qid, **kw):
    if qid not in byid: raise SystemExit(f'missing quest {qid}')
    byid[qid].update(kw)

# Existing quest semantic corrections verified against MH4G/MH4U quest sources.
fix('quest_1dd30bcc8189', objective='녹슨 크샬다오라 격퇴')
fix('quest_c83c67f7419a', objective='녹슨 크샬다오라 토벌 또는 격퇴', time='30분')
fix('quest_6acd493ed64d', objective='혼돈의 고어·마가라 1마리 수렵')
fix('quest_750a954c6940', objective='혼돈의 고어·마가라 1마리 수렵')
# G★3 天見るごとく蝕を見し: Stygian Zinogre followed by Chaotic Gore Magala.
fix('quest_5f701615a1a9', objective='진오우거 아종 1마리와 혼돈의 고어·마가라 1마리 수렵', _verifiedMonsters=['진오우거 아종','혼돈의 고어·마가라'])
# G★3 高難度：乱れ咲く連爆の華: Raging Brachydios special individual.
fix('quest_6cae3017e9a4', objective='임계 브라키디오스 1마리 토벌', _verifiedMonsters=['임계 브라키디오스'])
fix('quest_ade6bb5f20bb', objective='격앙 라잔 1마리 수렵')
fix('quest_fe44e93bc43b', objective='밀라보레아스 (홍염룡) 토벌 또는 격퇴')
# Event variant corrections.
for qid in ['event-g-070','event-g-078']:
    if qid in byid: byid[qid]['objective']='밀라보레아스 (홍염룡) 토벌 또는 격퇴'
if 'event-high-023' in byid: byid['event-high-023']['objective']='밀라보레아스 (홍룡) 토벌 또는 격퇴'
if 'event-episodic-096' in byid: byid['event-episodic-096']['objective']='밀라보레아스 (조룡) 토벌 또는 격퇴'

# Missing standard Caravan story/special quests in the previous source set.
# Korean display names are conservative project translations where an official Korean title was not verified;
# nameEn + source preserve the authoritative identity.
missing=[
 dict(id='quest_h8_c2_research_velocidrome',level='★2',name='조사: 도스람포스',nameEn='Research: Velocidrome',objective='도스람포스 조사',location='미지의 삼림',monsters=['도스람포스']),
 dict(id='quest_h8_c2_research_yian_kutku',level='★2',name='조사: 얀쿡크',nameEn='Research: Yian Kut-Ku',objective='얀쿡크 조사',location='미지의 삼림',monsters=['얀쿡크']),
 dict(id='quest_h8_c3_research_basarios',level='★3',name='조사: 바살모스',nameEn='Research: Basarios',objective='바살모스 1마리 수렵',location='미지의 삼림',monsters=['바살모스']),
 dict(id='quest_h8_c3_unknown_gore',level='★3',name='???',nameEn='???',objective='고어·마가라 격퇴',location='대해',monsters=['고어·마가라']),
 dict(id='quest_h8_c4_wild_palico_panic',level='★4',name='Wild Palico Panic',nameEn='Wild Palico Panic',objective='바바콩가 1마리 수렵',location='원생림',monsters=['바바콩가']),
 dict(id='quest_h8_c4_meownster_hunter_havoc',level='★4',name='Meownster Hunter Havoc',nameEn='Meownster Hunter Havoc',objective='자보아자길 1마리 수렵',location='빙해',monsters=['자보아자길']),
 dict(id='quest_h8_c4_gore_magala_drama',level='★4',name='Gore Magala Drama',nameEn='Gore Magala Drama',objective='고어·마가라 격퇴',location='미지의 삼림',monsters=['고어·마가라']),
 dict(id='quest_h8_c5_research_yian_garuga',level='★5',name='조사: 얀가루루가',nameEn='Research: Yian Garuga',objective='얀가루루가 1마리 수렵',location='미지의 삼림',monsters=['얀가루루가']),
 dict(id='quest_h8_c6_research_kirin',level='★6',name='조사: 키린',nameEn='Research: Kirin',objective='키린 토벌',location='미지의 삼림',monsters=['키린']),
 dict(id='quest_h8_c6_whole_lava_love',level='★6',name='Whole Lava Love',nameEn='Whole Lava Love',objective='브라키디오스 1마리 수렵',location='지저 화산',monsters=['브라키디오스']),
 dict(id='quest_h8_c6_fleet_action',level='★6',name='고난도: Fleet Action',nameEn='Advanced: Fleet Action',objective='다렌·모란 토벌 또는 격퇴',location='대사막',monsters=['다렌·모란']),
 dict(id='quest_h8_c6_deep_trouble',level='★6',name='고난도: Deep Trouble',nameEn='Advanced: Deep Trouble',objective='테오·테스카토르 토벌 또는 격퇴',location='지저 화산',monsters=['테오·테스카토르']),
 dict(id='quest_h8_c6_stand_tall',level='★6',name='고난도: Stand Tall',nameEn='Advanced: Stand Tall',objective='아캄토름 토벌',location='용암도',monsters=['아캄토름']),
 dict(id='quest_h8_c6_wicked_wings',level='★6',name='고난도: Wicked Wings',nameEn='Advanced: Wicked Wings',objective='크샬다오라 토벌 또는 격퇴',location='빙해',monsters=['크샬다오라']),
 dict(id='quest_h8_c6_tough_love',level='★6',name='고난도: Tough Love',nameEn='Advanced: Tough Love',objective='라잔 1마리 수렵',location='원생림',monsters=['라잔']),
 dict(id='quest_h8_c6_caravaneer_challenge',level='★6',name="The Caravaneer's Challenge",nameEn="The Caravaneer's Challenge",objective='격앙 라잔·진오우거·샤가르마가라 모두 수렵',location='금지된 땅',monsters=['격앙 라잔','진오우거','샤가르마가라']),
 dict(id='quest_h8_c10_red_dragon_dawn',level='★10',name='고난도: 홍룡 탄생',nameEn="Advanced: Red Dragon's Dawn",objective='밀라보레아스 (홍룡) 토벌 또는 격퇴',location='용암도',monsters=['밀라보레아스 (홍룡)'],time='35분'),
 dict(id='quest_h8_c10_moving_mountains',level='★10',name='고난도: 벗이여, 호산룡과 만나라',nameEn='Advanced: Moving Mountains',objective='다렌·모란 토벌 또는 격퇴',location='대사막',monsters=['다렌·모란'],time='35분'),
 dict(id='quest_h8_c10_into_mist',level='★10',name='사라지는 것, 마치 안개처럼',nameEn='Into the Mist',objective='오나즈치 토벌 또는 격퇴',location='미지의 삼림',monsters=['오나즈치']),
 dict(id='quest_h8_c10_elder_dragon_mist',level='★10',name='고난도: 안개의 고룡',nameEn='Advanced: Elder Dragon of Mist',objective='오나즈치 토벌 또는 격퇴',location='유적 평원',monsters=['오나즈치']),
 dict(id='quest_h8_c10_bad_hair_rajang',level='★10',name='고난도: 격앙 라잔',nameEn='Advanced: Bad Hair Rajang',objective='격앙 라잔 1마리 수렵',location='유적 평원',monsters=['격앙 라잔']),
 dict(id='quest_h8_c10_all_in_place',level='★10',name='고난도: 혼돈의 고어·마가라',nameEn='Advanced: All in Its Place',objective='혼돈의 고어·마가라 1마리 수렵',location='천공산',monsters=['혼돈의 고어·마가라']),
 dict(id='quest_h8_c10_masters_test',level='★10',name='고난도: 스승의 시련',nameEn="Advanced: The Master's Test",objective='극한 셀레기오스·극한 디아블로스·극한 이블조 모두 수렵',location='격투장',monsters=['셀레기오스','디아블로스','이블조']),
]
# Missing standard Guild G-rank quest.
missing.append(dict(id='quest_h8_g3_operation_rust_remover',questType='g',questTypeLabel='G급',level='★3',name='녹슨강룡 대비 방위 작전!',nameJa='対錆鋼龍防衛作戦！',nameEn='Operation Rust Remover',objective='녹슨 크샬다오라 토벌 또는 격퇴',location='전투 구역',monsters=['녹슨크샬다오라'],time='30분',fee='3100z',reward='30300z'))

existing_ids={q['id'] for q in qs}; existing_en={q.get('nameEn') for q in qs if q.get('nameEn')}
for row in missing:
    if row['id'] in existing_ids or (row.get('nameEn') and row['nameEn'] in existing_en): continue
    mons=row.pop('monsters')
    row.setdefault('questType','village'); row.setdefault('questTypeLabel','여단'); row.setdefault('key',False)
    row.setdefault('nameJa',''); row.setdefault('fee',''); row.setdefault('reward',''); row.setdefault('time','50분'); row.setdefault('conditions',''); row.setdefault('note','hotfix8 외부 원자료 복원')
    row['source']='https://kiranico.com/en/mh4u/quest'
    row['_verifiedMonsters']=mons
    qs.append(row)

# Keep deterministic category/rank order; preserve original order within existing data, append restored entries by rank.
P.write_text(json.dumps(qs,ensure_ascii=False,indent=2),encoding='utf-8')
print('quests',len(qs),'village',sum(q.get('questType')=='village' for q in qs),'guild',sum(q.get('questType') in ('hub','g') for q in qs))
