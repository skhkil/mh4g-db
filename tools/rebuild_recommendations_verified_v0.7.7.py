import json, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
load=lambda n: json.loads((ROOT/'data'/n).read_text())
skills=load('skills.json'); sets=load('armor_sets.json'); armors=load('armors.json'); decorations=load('decorations.json')
skill_by_id={s['id']:s for s in skills}; armor_by_id={a['id']:a for a in armors}; deco_by_name={d['name']:d for d in decorations}
set_by={(s['name'],s['hunterType']):s for s in sets}
WEAPONS=['대검','태도','한손검','쌍검','해머','수렵피리','랜스','건랜스','슬래시액스','차지액스','조충곤','라이트보우건','헤비보우건','활']
RANGED={'라이트보우건','헤비보우건','활'}
SRC_LOW={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (하위편)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=24587'}
SRC_HIGH={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (상위편)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=24815'}
SRC_G={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (G급편)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=24935'}
SRC_GPLUS={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (G급+)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=25076'}
SRC_INVEN={'type':'국내 커뮤니티','title':'[4G] G급 추천 방어구','url':'https://m.inven.co.kr/board/mhf/3746/393?category=%EC%A0%95%EB%B3%B4&p=1'}
SRC_CB={'type':'국내 커뮤니티','title':'차지액스 기초 가이드','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=87271'}
SRC_TA={'type':'국내 커뮤니티','title':'4G 태도 가이드','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=400221'}
SRC_LAMP={'type':'국내 커뮤니티/DB교차','title':'도스람포스 방어구 정보','url':'https://www.namu.moe/w/%EB%8F%84%EC%8A%A4%EB%9E%8C%ED%8F%AC%EC%8A%A4'}

def activated(points):
    out=[]
    for sid,val in points.items():
        s=skill_by_id.get(sid)
        if not s: continue
        candidates=[a for a in s.get('activations',[]) if int(a.get('points',0))>0 and int(a.get('points',0))<=int(val)]
        if candidates:
            a=max(candidates,key=lambda x:int(x['points']))
            out.append({'skillId':sid,'name':a['name'],'points':int(val)})
    return sorted(out,key=lambda x:x['name'])

def build_from_armors(ids, deco_specs=None):
    aa=[armor_by_id[i] for i in ids if i in armor_by_id]
    pts={}; torso_mult=1+sum(1 for a in aa if a.get('part')!='body' and a.get('torsoUp'))
    body=next((a for a in aa if a.get('part')=='body'),None)
    for a in aa:
        if a is body: continue
        for sid,p in (a.get('skills') or {}).items(): pts[sid]=pts.get(sid,0)+int(p or 0)
    if body:
        for sid,p in (body.get('skills') or {}).items(): pts[sid]=pts.get(sid,0)+int(p or 0)*torso_mult
    deco_list=[]
    for name,count in (deco_specs or []):
        d=deco_by_name.get(name)
        if not d: raise RuntimeError(f'missing decoration {name}')
        deco_list.append({'id':d['id'],'name':d['name'],'slots':d['slots'],'count':count})
        for sid,p in (d.get('skills') or {}).items(): pts[sid]=pts.get(sid,0)+int(p or 0)*count
    return {'armors':[{k:a.get(k) for k in ['id','name','part','defense','slots','rank','rare','materials']} for a in aa],
            'decorations':deco_list, 'defense':sum(int(a.get('defense',0) or 0) for a in aa),
            'resist':{e:sum(int((a.get('resistances') or {}).get(e,0) or 0) for a in aa) for e in ['fire','water','thunder','ice','dragon']},
            'activated':activated(pts)}

def fullset(name,hunter,deco_specs=None):
    s=set_by.get((name,hunter))
    if not s: return None
    return build_from_armors([p['id'] for p in s['pieces']],deco_specs)

def custom(names,hunter='blade'):
    ids=[]
    for part,name in names.items():
        found=next((a for a in armors if a.get('name')==name and a.get('part')==part and a.get('hunterType') in (hunter,'both')),None)
        if not found: raise RuntimeError(f'missing {hunter} {part} {name}')
        ids.append(found['id'])
    return build_from_armors(ids)

def card(label,style,build,source,note='',setName='',kind='세트'):
    return {'label':label,'style':style,'kind':kind,'note':note,'setName':setName,'build':build,'source':source}

def common_low(hunter):
    # 하위 국내 교복은 재기/카브라가 직접 확인됨. 람포스는 공격형 선택지로 DB 교차 확인.
    return [
      card('람포스 세트','공격형',fullset('람포스',hunter),SRC_LAMP,'공격력 상승 중심의 초반 세트.','람포스'),
      card('카브라 세트','방어형',fullset('카브라',hunter),SRC_LOW,'체력·방어 스킬 중심의 하위 교복.','카브라'),
      card('재기 세트','밸런스형',fullset('재기',hunter),SRC_LOW,'숫돌/기절 대응이 편한 초반 진행 세트.','재기')]

def common_high(hunter):
    return [
      card('리오소울 세트','공격형',fullset('리오소울',hunter,[('방음주【1】',5),('체력주【1】',2)]),SRC_HIGH,'','리오소울'),
      card('카브라S 세트','방어형',fullset('카브라S',hunter),SRC_HIGH,'체력·방어 중심, 숫돌고속화 확장도 쉬운 상위 입문 세트.','카브라S'),
      card('진오우U 세트','밸런스형',fullset('진오우U',hunter),SRC_HIGH,'회피/집중 계열이 함께 붙는 상위 선택지.','진오우U')]

def ukauka():
    return custom({'head':'우캄루X사쿠파케','body':'카이저X메일','arms':'우캄루X사쿰페','waist':'카이저X펄드','legs':'우캄루X케마르'})

def byebye():
    return custom({'head':'스컬헤드','body':'카이저X메일','arms':'카이저X암','waist':'크샤나X안다','legs':'카브라X그리브'})

def guard_lance_g2():
    return custom({'head':'그라비드X헬름','body':'자자미X메일','arms':'그라비드X암','waist':'아그나X펄드','legs':'그라비드X그리브'})

def gunlance_g2():
    return custom({'head':'셀타스X헬름','body':'셀타스X메일','arms':'아그나X암','waist':'아그나X펄드','legs':'반기스그리브'})

def g_cards(weapon,hunter):
    if hunter=='gunner':
        if weapon=='헤비보우건':
            return [card('자자미Z 세트','공격형 · 관통',fullset('자자미Z','gunner'),SRC_INVEN,'G1 관통 헤보용으로 국내 추천 자료에 명시.','자자미Z')]
        # 국내 4G 자료에서 라보/활 범용 "교복"을 이번 조사 범위에서 확정하지 못해 억지 추천하지 않음.
        return []
    out=[]
    if weapon=='대검':
        out += [card('디아블로X 세트','공격형 · 대검',fullset('디아블로X','blade'),SRC_G,'발도술【기술】·납도술 기반 대검용 G급 세트.','디아블로X'),
                card('바이바이카이저','공격형 · 대검 커스텀',byebye(),SRC_GPLUS,'몸통배가+카이저X/크샤나X 조합의 유명 대검 커스텀.','', '커스텀')]
    if weapon=='랜스':
        out += [card('자자미X 세트','방어형 · 가드',fullset('자자미X','blade'),SRC_INVEN,'G1부터 가드성능+2를 확보하는 랜스/건랜스 입문 세트.','자자미X'),
                card('G2 가드 랜스 커스텀','밸런스형 · 가드',guard_lance_g2(),SRC_INVEN,'가드성능+2와 예리도+1을 함께 노리는 국내 추천 조합.','', '커스텀')]
    if weapon=='건랜스':
        out += [card('자자미X 세트','방어형 · 가드',fullset('자자미X','blade'),SRC_INVEN,'G1 가드형 건랜스 입문 세트.','자자미X'),
                card('G2 포술 건랜스 커스텀','공격형 · 포술',gunlance_g2(),SRC_INVEN,'가드성능+2·예리·포술마스터 구성으로 소개된 G급 건랜스 조합.','', '커스텀')]
    if weapon=='차지액스':
        out += [card('자자미Z 세트','밸런스형 · 가드',fullset('자자미Z','blade'),SRC_INVEN,'가드성능·근성·체술 계열을 가진 G급 선택지.','자자미Z')]
    # 범용 G 진행/후반 세팅. 대검은 스타나이트보다 전용 커스텀 우선이지만 진행용으로 포함.
    out.insert(0,card('레기오스X 세트','밸런스형 · G급 입문',fullset('레기오스X','blade'),SRC_G,'소재 수급이 쉬워 G급 입문용 교복으로 소개됨.','레기오스X'))
    if weapon!='대검':
        src=SRC_CB if weapon=='차지액스' else SRC_G
        out.append(card('스타나이트 세트','공격형 · 범용',fullset('스타나이트','blade'),src,'도전자+2·심검일체 기반의 대표 G급 범용 세트.','스타나이트'))
    out.append(card('우카우카우','공격형 · 범용 커스텀',ukauka(),SRC_GPLUS,'우캄루X/카이저X를 섞는 대표 G급 검사 커스텀.','', '커스텀'))
    # max 5, preserve weapon-specific first/important entries
    return out[:5]

entries=[]
for w in WEAPONS:
    hunter='gunner' if w in RANGED else 'blade'
    # low/high: gunner variants exist in DB, but the domestic "교복" source explicitly treats blademaster.
    # We still show the armor family per weapon only for blade weapons; ranged gets a transparent no-verified-data message via empty list.
    low=common_low(hunter) if hunter=='blade' else []
    high=common_high(hunter) if hunter=='blade' else []
    entries.append({'weaponType':w,'rank':'low','rankLabel':'하위','hunterType':hunter,'variants':low})
    entries.append({'weaponType':w,'rank':'high','rankLabel':'상위','hunterType':hunter,'variants':high})
    entries.append({'weaponType':w,'rank':'g','rankLabel':'G급','hunterType':hunter,'variants':g_cards(w,hunter)})

rec={'generatedAt':'2026-09-18T09:55:00+09:00','method':'국내 MH4G 커뮤니티에서 실제 교복/추천 장비로 확인되는 세트만 수록. 자동조합 결과는 추천 데이터 생성에 사용하지 않음.','progressionNote':'','weaponTypes':WEAPONS,'entries':entries,
     'sources':{'low':SRC_LOW,'high':SRC_HIGH,'g':SRC_G,'gplus':SRC_GPLUS,'inven_g':SRC_INVEN,'charge_blade':SRC_CB,'long_sword':SRC_TA}}
(ROOT/'data'/'recommended_loadouts.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2))

# audit
bad=[]; total=0
for e in entries:
    for v in e['variants']:
        total+=1
        b=v.get('build') or {}
        if len(b.get('armors',[]))!=5: bad.append((e['weaponType'],e['rank'],v['label'],len(b.get('armors',[]))))
audit={'entries':len(entries),'cards':total,'badBuilds':bad,'counts':{w:{r:len(next(e for e in entries if e['weaponType']==w and e['rank']==r)['variants']) for r in ['low','high','g']} for w in WEAPONS}}
(ROOT/'tools'/'recommended_loadouts_verified_audit_v0.7.7.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(json.dumps(audit,ensure_ascii=False,indent=2))
