#!/usr/bin/env python3
import json, re, unicodedata, difflib
from pathlib import Path
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def load(name):
    return json.loads((DATA/name).read_text(encoding='utf-8'))

def norm(s):
    s=unicodedata.normalize('NFKC',str(s or ''))
    return ''.join(c for c in s if c.isalnum()).lower()

def qlevel_token(level):
    return str(level or '').replace('G★','★')

quests=load('quests.json')
dragon=load('dragon_exchange.json')
decos=load('decoration_unlocks.json')
decoration_rows=load('decorations.json')
deco_name_by_id={d.get('id'):d.get('name') for d in decoration_rows}
qbyid={q['id']:q for q in quests}

TYPE_ALIASES={'village':'village','hub':'hub','g':'g'}

def find_quest(name, quest_type=None, level=None, min_score=.78):
    target=norm(name)
    cand=[]
    for q in quests:
        if quest_type and q.get('questType')!=quest_type: continue
        if level and str(q.get('level'))!=level: continue
        best=0
        for k in ('nameJa','name'):
            x=norm(q.get(k,''))
            if not x: continue
            score=difflib.SequenceMatcher(None,target,x).ratio()
            if target in x or x in target: score=max(score,.96)
            best=max(best,score)
        if best>=min_score: cand.append((best,q))
    cand.sort(key=lambda z:z[0],reverse=True)
    if not cand:return None,0
    if len(cand)>1 and cand[0][0]-cand[1][0]<.03 and cand[0][0]<.96:return None,cand[0][0]
    return cand[0][1],cand[0][0]

# Unlock relation index. `quest -> targets` and `target -> quests` are generated from the same rows.
relations=[]
unresolved=[]

def add_rel(q, *, target_type, target_id, name, effect, relation='direct', source='', condition_mode='single', group_id=None, confidence='verified', note=''):
    if not q:
        unresolved.append({'targetType':target_type,'targetId':target_id,'name':name,'effect':effect,'source':source,'note':note})
        return
    relations.append({
        'questId':q['id'],'questType':q.get('questType'),'level':q.get('level'),'questName':q.get('name'),'questNameJa':q.get('nameJa',''),
        'targetType':target_type,'targetId':target_id,'name':name,'effect':effect,'relation':relation,
        'conditionMode':condition_mode,'groupId':group_id or f"{target_type}:{target_id}",'confidence':confidence,'source':source,'note':note
    })

def add_named(quest_name, *, quest_type=None, level=None, **kw):
    q,score=find_quest(quest_name,quest_type,level)
    if not q:
        kw['note']=(kw.get('note','')+f' [DB quest match unresolved: {quest_name}, score={score:.3f}]').strip()
    add_rel(q,**kw)
    return q

# 1) Wyporium material exchanges: project table is exhaustive (139 rows / 39 unlock groups).
# Parse Korean quest names in the unlock strings; use level/type to prevent same-title collisions.
def extract_specs(text):
    # each branch: 여단★N - NAME / 집회소★N - NAME / G★N - NAME
    out=[]
    for m in re.finditer(r'(여단|집회소|G)★(\d+)\s*-\s*([^「]+?)(?=\s+(?:또는|村|集|G★)|$)', text):
        who,nm,name=m.group(1),m.group(2),m.group(3).strip()
        qt={'여단':'village','집회소':'hub','G':'g'}[who]
        lvl=f"★{nm}"
        out.append((qt,lvl,name))
    return out

exchange_groups=defaultdict(list)
for i,row in enumerate(dragon): exchange_groups[row.get('unlock','')].append((i,row))

unlock_to_qids={}
for gi,(unlock,rows) in enumerate(exchange_groups.items(),1):
    specs=extract_specs(unlock)
    qids=[]
    for bi,(qt,lvl,name) in enumerate(specs):
        q,score=find_quest(name,qt,lvl,min_score=.68)
        if not q:
            unresolved.append({'kind':'wyporium-condition','unlock':unlock,'questText':name,'questType':qt,'level':lvl,'score':score})
            continue
        qids.append(q['id'])
        for row_index,row in rows:
            # old Village★6 OR Hub★3 line is preserved but flagged for review because community notes conflict.
            confidence='needs-review' if ('또는' in unlock and len(specs)>1) else 'verified'
            add_rel(q,target_type='wyporium_exchange',target_id=f'exchange:{row_index}',name=f"용인족 교환 · {row['result']}",
                    effect=f"{row['required']} → {row['result']} 교환 해금",source='MH4G@wiki 竜人問屋 + project dragon_exchange.json',
                    condition_mode='any' if len(specs)>1 else 'single',group_id=f'wyporium:{gi}',confidence=confidence,note=unlock)
    unlock_to_qids[unlock]=qids

# 2) Direct facility / delivery request unlocks from MH4G wiki.
SRC_DELIVERY='MH4G@wiki 納品依頼'
SRC_FOOD='MH4G@wiki 食事'
SRC_EXP='MH4G@wiki 探索'
SRC_SCENARIO='MH4G scenario/wiki cross-check'

add_named('危機！テツカブラを狩れ！',quest_type='village',level='★3',target_type='facility',target_id='smithy:decoration',name='장식주 생산/탈착',effect='나구리 마을에서 장식주 생산·탈착 기능 해금',source=SRC_SCENARIO)

# Delivery requests: quest clear unlocks a request; delivery completion applies the result.
delivery_specs=[
 ('危機！テツカブラを狩れ！','village','★3','delivery:honey','납품 의뢰 · 거래는 꿀맛','납품 의뢰 발생 → 완료 시 용인족 도매상 「모가 양봉장」 추가','single'),
 ('ゲリョスを狩猟せよ！','village','★3','delivery:milk','납품 의뢰 · 영양 만점 우유!','납품 의뢰 발생 → 완료 시 유제품 식재료 레벨 상승','single'),
 ('ドクターのドス毒研究','village','★5','delivery:fish','납품 의뢰 · 생선은 신선도가 생명!','납품 의뢰 발생 → 완료 시 생선 식재료 레벨 상승','single'),
 ('ガブラス討伐','village','★5','delivery:meat-grill','납품 의뢰 · 요리장, 고기를 굽다','두 선행 퀘스트 완료 시 의뢰 발생 → 완료 시 요리장 특제 고기굽기 추가','all'),
 ('気高き女王・リオレイア','village','★4','delivery:meat-grill','납품 의뢰 · 요리장, 고기를 굽다','두 선행 퀘스트 완료 시 의뢰 발생 → 완료 시 요리장 특제 고기굽기 추가','all'),
 ('高難度：暗黒の狩猟','village','★6','delivery:palico40','납품 의뢰 · 따끈따끈섬, 추가 증축!','납품 의뢰 발생 → 완료 시 오토모 고용 상한 40','single'),
 ('熱砂の中からゴアイサツ','village','★7','delivery:palico50','납품 의뢰 · 따끈따끈섬, 더 증축!','납품 의뢰 발생 → 완료 시 오토모 고용 상한 50','single'),
]
for n,qt,lvl,tid,label,effect,mode in delivery_specs:
    add_named(n,quest_type=qt,level=lvl,target_type='delivery_request',target_id=tid,name=label,effect=effect,source=SRC_DELIVERY,condition_mode=mode,group_id=tid)

# Research lab requests. Wiki states any two / all four, with village ending likely an additional prerequisite.
research=[('高難度：暴走する虎鮫','g','★1'),('高難度：怪しき骸蜘蛛達の研究','g','★2'),('高難度：大脱走はお静かに','g','★2'),('高難度：侵蝕の残滓','g','★3')]
for n,qt,lvl in research:
    add_named(n,quest_type=qt,level=lvl,target_type='delivery_request',target_id='delivery:lab1',name='납품 의뢰 · 연구소, 개량!',effect='4개 후보 중 2개 + 여단 엔딩 조건 추정 → 완료 시 항룡석·속격/심격 추가',source=SRC_DELIVERY,condition_mode='any2',group_id='delivery:lab1',confidence='needs-review',note='위키 검증 코멘트상 여단★10 결전! 크샬다오라! 완료도 필요할 가능성이 높음')
    add_named(n,quest_type=qt,level=lvl,target_type='delivery_request',target_id='delivery:lab2',name='납품 의뢰 · 연구소, 추가 개량!',effect='4개 전부 + 여단 엔딩 조건 추정 → 완료 시 항룡석 2종 동시 소지 및 연구소 탄약 판매',source=SRC_DELIVERY,condition_mode='all',group_id='delivery:lab2',confidence='needs-review',note='여단 엔딩 추가 조건 가능성')
add_named('決戦！クシャルダオラ！',quest_type='village',level='★10',target_type='delivery_request',target_id='delivery:lab1',name='납품 의뢰 · 연구소, 개량!',effect='연구소 의뢰 출현의 추가 선행 조건으로 보고됨',source=SRC_DELIVERY,condition_mode='all-extra',group_id='delivery:lab1',confidence='needs-review')
add_named('決戦！クシャルダオラ！',quest_type='village',level='★10',target_type='delivery_request',target_id='delivery:lab2',name='납품 의뢰 · 연구소, 추가 개량!',effect='연구소 의뢰 출현의 추가 선행 조건으로 보고됨',source=SRC_DELIVERY,condition_mode='all-extra',group_id='delivery:lab2',confidence='needs-review')

# Exploration feature unlocks.
add_named('アルセルタス、突撃！',quest_type='village',level='★2',target_type='facility',target_id='expedition:low',name='하위 탐색',effect='탐색 기능 해금',source=SRC_EXP)
for n,qt,lvl in [('高難度：天を廻りて戻り来よ','village','★6'),('高難度：砂を渡るは錆びた岩船','hub','★3')]:
    add_named(n,quest_type=qt,level=lvl,target_type='facility',target_id='expedition:high',name='상위 탐색',effect='두 퀘스트를 모두 완료하면 상위 탐색 해금',source=SRC_EXP,condition_mode='all',group_id='expedition:high')
for n,qt,lvl in [('決戦！クシャルダオラ！','village','★10'),('高難度：極氷に座す、崩せし者','hub','★7')]:
    add_named(n,quest_type=qt,level=lvl,target_type='facility',target_id='expedition:g',name='G급 탐색',effect='두 퀘스트를 모두 완료하면 G급 탐색 해금',source=SRC_EXP,condition_mode='all',group_id='expedition:g')

# Food level/unlock table. Each listed quest contributes one level; delivery-request-only rows are represented above.
food_specs=[
 ('凍れるポポノタン','hub','★2','food:meat','식재료 · 고기','고기 식재료 1단계 상승'),
 ('高難度：氷海の大食漢共！','hub','★3','food:meat','식재료 · 고기','고기 식재료 1단계 상승'),
 ('金と緑の牙獣旋風','hub','★4','food:meat','식재료 · 고기','고기 식재료 1단계 상승'),
 ('ドスゲネポスの捕獲','village','★3','food:fish','식재료 · 생선','생선 식재료 1단계 상승'),
 ('狩人たちの天域','hub','★3','food:fish','식재료 · 생선','생선 식재료 1단계 상승'),
 ('アルセルタス、突撃！','village','★2','food:grain','식재료 · 곡물','곡물 식재료 1단계 상승'),
 ('ガララアジャラの狩猟','village','★4','food:grain','식재료 · 곡물','곡물 식재료 1단계 상승'),
 ('火竜を捕獲せよ！','village','★5','food:grain','식재료 · 곡물','곡물 식재료 1단계 상승'),
 ('アルセルタス、突撃！','village','★2','food:vegetable','식재료 · 채소','채소 식재료 1단계 상승'),
 ('ガララアジャラの狩猟','village','★4','food:vegetable','식재료 · 채소','채소 식재료 1단계 상승'),
 ('火竜を捕獲せよ！','village','★5','food:vegetable','식재료 · 채소','채소 식재료 1단계 상승'),
 ('ふたつの影','village','★4','food:dairy','식재료 · 유제품','유제품 식재료 1단계 상승'),
 ('秘密の卵運搬・最後の難問','village','★6','food:dairy','식재료 · 유제품','유제품 식재료 1단계 상승'),
 ('砂を渡るは錆びた岩船','hub','★3','food:alcohol','식재료 · 술','술 식재료 카테고리 해금'),
 ('なんて素敵な灰水晶','hub','★4','food:alcohol','식재료 · 술','술 식재료 1단계 상승'),
 ('燃え上がる双炎','hub','★5','food:alcohol','식재료 · 술','술 식재료 1단계 상승'),
 ('高難度：天と地の領域','hub','★6','food:alcohol','식재료 · 술','술 식재료 1단계 상승'),
 ('花より団子、時々夜桜','village','★8','food:premium','식사 · 극상 신선도','식사에 「극상」 신선도 추가',),
]
for n,qt,lvl,tid,label,effect in food_specs:
    add_named(n,quest_type=qt,level=lvl,target_type='food',target_id=tid,name=label,effect=effect,source=SRC_FOOD)

# 3) Decoration reverse tracking. Existing decoration_unlocks records explicit material unlock notes.
# Map those notes back to Wyporium quest groups and attach *indirect* decoration availability relations.
for deco_id,d in (decos.get('decorations') or {}).items():
    for mat in d.get('materials',[]):
        for unlock in mat.get('unlocks',[]):
            # exact project unlock text is normally the same dragon_exchange.unlock text
            qids=unlock_to_qids.get(unlock,[])
            if not qids:
                # fuzzy unlock string containment fallback
                match=next((u for u in unlock_to_qids if norm(unlock) in norm(u) or norm(u) in norm(unlock)),None)
                qids=unlock_to_qids.get(match,[]) if match else []
            for qid in qids:
                q=qbyid.get(qid)
                add_rel(q,target_type='decoration',target_id=deco_id,name=deco_name_by_id.get(deco_id) or deco_id,
                        effect=f"소재 「{mat.get('name')}」 교환 해금 → 장식주 제작 경로 개방",relation='indirect_material',
                        source='decoration_unlocks.json + dragon_exchange.json',condition_mode='material',group_id=f'decoration:{deco_id}',note=unlock)

# Deduplicate exact rows.
seen=set(); uniq=[]
for r in relations:
    key=(r['questId'],r['targetType'],r['targetId'],r['relation'],r['effect'])
    if key in seen: continue
    seen.add(key);uniq.append(r)
relations=uniq

qindex=defaultdict(lambda:{'unlocks':[]})
tindex=defaultdict(lambda:{'quests':[]})
for r in relations:
    rr={k:v for k,v in r.items() if k not in ('questId','questType','level','questName','questNameJa')}
    qindex[r['questId']]['unlocks'].append(rr)
    tk=f"{r['targetType']}:{r['targetId']}"
    if 'type' not in tindex[tk]:
        tindex[tk].update({'type':r['targetType'],'id':r['targetId'],'name':r['name'],'effect':r['effect'],'quests':[]})
    tindex[tk]['quests'].append({k:r[k] for k in ('questId','questType','level','questName','questNameJa','relation','conditionMode','groupId','confidence','source','note')})

# summary & audit
summary={
    'questCount':len(quests),'relationCount':len(relations),'questWithUnlockCount':len(qindex),'targetCount':len(tindex),
    'directRelationCount':sum(r['relation']=='direct' for r in relations),
    'indirectDecorationRelationCount':sum(r['relation']=='indirect_material' for r in relations),
    'wyporiumExchangeRows':len(dragon),'wyporiumUnlockGroups':len(exchange_groups),
    'decorationCount':len(decos.get('decorations') or {}),
    'decorationWithQuestDependencyCount':len({r['targetId'] for r in relations if r['targetType']=='decoration'}),
    'unresolvedCount':len(unresolved),
    'needsReviewCount':sum(r['confidence']=='needs-review' for r in relations),
}
out={
 'version':'0.7.7-step2-unlock-xref','policy':{
   'singleSource':'All quest→unlock and unlock→quest views are generated from the same relation rows.',
   'directVsIndirect':'Decoration rows derived from material/Wyporium unlocks are marked indirect_material and are not asserted as direct recipe unlocks.',
   'uncertainty':'Community-disputed prerequisites are retained as needs-review instead of silently promoted to verified.'
 },
 'sources':['project:dragon_exchange.json','project:decoration_unlocks.json','MH4G@wiki:竜人問屋','MH4G@wiki:納品依頼','MH4G@wiki:食事','MH4G@wiki:探索'],
 'summary':summary,'quests':dict(qindex),'targets':dict(tindex),'relations':relations,'unresolved':unresolved
}
(DATA/'quest_unlock_index.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
if unresolved:
    print('\nUNRESOLVED')
    for x in unresolved: print(json.dumps(x,ensure_ascii=False))
