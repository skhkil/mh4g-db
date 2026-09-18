import json, copy, os, datetime
BASE='/mnt/data/reco_weapon_research/data'

def load(n): return json.load(open(f'{BASE}/{n}',encoding='utf-8'))
armors=load('armors.json'); sets=load('armor_sets.json'); skills=load('skills.json'); decos=load('decorations.json')
armor_by_id={x['id']:x for x in armors}; skill_by_id={x['id']:x for x in skills}; deco_by_name={x['name']:x for x in decos}
old=load('recommended_loadouts.json')
oldvar={}
for e in old['entries']:
  for v in e.get('variants',[]): oldvar[(e['weaponType'],e['rank'],v['label'])]=v
  # generic lookup too
  for v in e.get('variants',[]): oldvar.setdefault(('*',e['rank'],v['label']),v)

def activated(points):
  out=[]
  for sid,p in points.items():
    s=skill_by_id.get(sid)
    if not s: continue
    chosen=None
    if p>=0:
      for a in sorted([a for a in s.get('activations',[]) if a['points']>0],key=lambda x:x['points']):
        if p>=a['points']: chosen=a
    else:
      for a in sorted([a for a in s.get('activations',[]) if a['points']<0],key=lambda x:x['points'], reverse=True):
        if p<=a['points']: chosen=a
    if chosen: out.append({'skillId':sid,'name':chosen['name'],'points':p})
  return sorted(out,key=lambda x:x['name'])

def build_fullset(name,hunter='blade'):
  candidates=[s for s in sets if s.get('name')==name and s.get('hunterType')==hunter]
  if not candidates: raise KeyError((name,hunter))
  s=candidates[0]
  aa=[]; pts={}; defense=0; res={k:0 for k in ['fire','water','thunder','ice','dragon']}
  for p in s['pieces']:
    a=copy.deepcopy(armor_by_id[p['id']]); aa.append(a); defense+=int(a.get('defense') or 0)
    for k in res: res[k]+=int((a.get('resist') or {}).get(k,0) or 0)
    for sid,n in (a.get('skills') or {}).items(): pts[sid]=pts.get(sid,0)+int(n or 0)
  return {'armors':aa,'decorations':[],'defense':defense,'resist':res,'activated':activated(pts)}

def clone(label,rank='g',weapon='*'):
  v=oldvar.get((weapon,rank,label)) or oldvar.get(('*',rank,label))
  if not v: raise KeyError((weapon,rank,label))
  return copy.deepcopy(v)

def V(label, style, kind, build, domestic, foreign=None, reco_decos=None, talisman='', usage='', compare='', note=''):
  deco_list=reco_decos or []
  if '3슬롯' in talisman:
    socket=f"3슬롯 호석이면 {deco_list[0] if deco_list else '핵심 스킬 장식주'}의 고슬롯 장식주를 우선. 남는 슬롯은 카드의 보조 장식주로 조정."
  elif '1슬롯' in talisman:
    socket=f"호석 1슬롯에는 {deco_list[0] if deco_list else '핵심 스킬 장식주'}의 1슬롯 장식주를 우선."
  elif talisman:
    socket=f"호석에 슬롯이 있으면 {deco_list[0] if deco_list else '핵심 스킬 장식주'}부터 부족 포인트를 채우고, 남는 슬롯은 보조 스킬에 사용."
  else:
    socket=''
  return {
    'label':label,'style':style,'kind':kind,'note':note,'build':build,
    'recommendedDecorations':deco_list,'talismanGuide':talisman,'talismanSocketGuide':socket,'usageGuide':usage,'foreignComparison':compare,
    'source':domestic or {},'foreignSource':foreign or {}
  }

DC_LOW={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (하위편)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=24587'}
DC_HIGH={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (상위편)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=24815'}
DC_G={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (G급편)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=24935'}
DC_GP={'type':'국내 커뮤니티','title':'몬4G 교복 지침서 (G급+)','url':'https://gall.dcinside.com/board/view/?id=monsterhunter&no=25076'}
DC_INV={'type':'국내 인벤','title':'[4G] G급 추천 방어구 (번역)','url':'https://www.inven.co.kr/board/mhf/3746/393'}

FOREIGN={
'GS':{'title':'GameFAQs · GS skills/sets','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71344548'},
'LS':{'title':'GameFAQs · weapon skill discussion','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71182691'},
'SNS':{'title':'GameFAQs · weapon skill discussion','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71182691'},
'DB':{'title':'GameFAQs · Endgame Dual Blade Sets','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/72239247'},
'HAM':{'title':'GameFAQs · G-rank Hammer mix','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71911054'},
'HH':{'title':'GameFAQs · Hunting Horn armor','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/72594127'},
'LANCE':{'title':'GameFAQs · Lance sets','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/72202099'},
'GL':{'title':'GameFAQs · weapon skill discussion','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71182691'},
'SA':{'title':'GameFAQs · Switch Axe setup','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/73167171'},
'CB':{'title':'GameFAQs · Charge Blade armor sets','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/72702463'},
'IG':{'title':'GameFAQs · Insect Glaive armor','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71811235'},
'LBG':{'title':'GameFAQs · LBG skills','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/72332328'},
'HBG':{'title':'GameFAQs · HBG armor recommendations','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71383732'},
'BOW':{'title':'GameFAQs · Bow skills/armor','url':'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/72115904'},
}

weapon_types=old['weaponTypes']
blade=set(weapon_types[:11])

def common_low(w):
  guides={
    '람포스 세트':('공격형',['공격주','천리주'],'공격 계열 또는 1슬롯 호석','초반 화력을 올리기 쉬운 세트. 공격 스킬을 한 단계 올리는 방향으로 활용.'),
    '카브라 세트':('방어형',['방어주','체력주'],'방어/체력 계열 또는 슬롯 호석','체력과 방어를 올려 실수 허용치를 높이는 진행용 세트.'),
    '재기 세트':('밸런스형',['연마주'],'슬롯 호석','숫돌사용고속화를 살리고 남는 슬롯은 공격/생존 보조에 사용.'),
  }
  out=[]
  for lab,(sty,ds,tal,use) in guides.items():
    v=clone(lab,'low',w); out.append(V(lab,sty,'세트',v['build'],DC_LOW,None,ds,tal,use))
  return out

def common_high(w):
  out=[]
  # 실제 상위 교복 3종. 무기 적합도는 활용 설명으로 조정.
  v=clone('리오소울 세트','high',w)
  out.append(V('리오소울 세트','공격형','세트',v['build'],DC_HIGH,None,['방음주','체력주','달인주'],'청각보호/달인 또는 3슬롯 호석','예리(업물)+회심+귀마개 기반. 포효를 막고 공격 기회를 늘리는 검사 범용 교복.'))
  v=clone('카브라S 세트','high',w)
  out.append(V('카브라S 세트','방어형','세트',v['build'],DC_HIGH,None,['방어주','체력주','연마주'],'방어/체력 계열 또는 슬롯 호석','상위 진입 안정용. 방어·체력 보강 후 남는 슬롯을 숫돌/공격에 사용.'))
  v=clone('진오우U 세트','high',w)
  out.append(V('진오우U 세트','밸런스형','세트',v['build'],DC_HIGH,None,['회피주','도약주','공격주'],'회피/공격 계열 호석','회피·기동 계열을 보완해 공격과 생존을 절충하는 상위 진행 세트.'))
  return out

# Full sets / custom source clones
reg=clone('레기오스X 세트','g','*'); star=clone('스타나이트 세트','g','*'); uka=clone('우카우카우','g','*'); bai=clone('바이바이카이저','g','대검'); dia=clone('디아블로X 세트','g','대검');
herm=clone('자자미X 세트','g','랜스'); lance_mix=clone('G2 가드 랜스 커스텀','g','랜스'); gl_mix=clone('G2 포술 건랜스 커스텀','g','건랜스')

# Fix Inven exact decoration guidance on lance/gl mixed cards (do not silently count as equipped in base build)
lance_mix['build']['decorations']=[]; gl_mix['build']['decorations']=[]

# additional full sets
full=lambda n,h='blade': build_fullset(n,h)

def mixed_from_names(names):
  aa=[]; pts={}; defense=0; res={k:0 for k in ['fire','water','thunder','ice','dragon']}
  for name in names:
    hits=[a for a in armors if a.get('name')==name]
    if not hits: raise KeyError(name)
    a=copy.deepcopy(hits[0]); aa.append(a); defense+=int(a.get('defense') or 0)
    for k in res: res[k]+=int((a.get('resist') or {}).get(k,0) or 0)
    for sid,n in (a.get('skills') or {}).items(): pts[sid]=pts.get(sid,0)+int(n or 0)
  return {'armors':aa,'decorations':[],'defense':defense,'resist':res,'activated':activated(pts)}

miku_names=['수신·진【복면】','크샤나X딜','수신·진【넓은소매】','크샤나X안다','수신·진【각갑】']
miku_build=mixed_from_names(miku_names) if all(any(a.get('name')==n for a in armors) for n in miku_names) else None

G={}
G['대검']=[
 V('디아블로X 세트','공격형','세트',dia['build'],DC_G,FOREIGN['GS'],['단축주','발도주','공격주'],'차지단축 계열 + 슬롯 호석','발도술【기술】·납도·내진 기반. 집중을 우선 추가하고 남는 슬롯에 공격/예리도 계열을 보완.','해외 MH4U에서도 집중+발도술【기술】을 대검 핵심으로 반복 추천.'),
 V('바이바이카이저','공격형','커스텀',bai['build'],DC_GP,FOREIGN['GS'],['단축주','발도주','공격주'],'차지단축 +2 이상 / 3슬롯 예시','대검용 대표 커스텀. 집중+발도술【기술】을 먼저 완성하고 공격을 추가.','국내 글이 대검 특화라고 명시하며 해외도 동일한 핵심 스킬을 강조.'),
 V('우카우카우','밸런스형','커스텀',uka['build'],DC_GP,FOREIGN['GS'],['통격주','내진주','공격주'],'공격/통격 계열 호석','심안+예리도레벨+1 기반의 범용 검사 커스텀. 대검은 바이바이카이저가 더 직접적이므로 보조 선택.','해외에서는 대검 전용 세팅이 더 선호되어 범용 대안으로 취급.')]
G['태도']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['LS'],['연마주','공격주'],'공격/회심 또는 슬롯 호석','G급 입문. 심검일체로 예리 관리가 편해 태도 진행용으로 무난.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['LS'],['명장주','방음주','공격주'],'장인 +5 1슬롯 예시','도전자+2+심검일체를 기본으로 예리도레벨+1 또는 고급귀마개를 추가하는 범용 최종 세트.','해외에서도 Star Knight를 범용 검사 세트로 높게 평가.'),
 V('우카우카우','공격형','커스텀',uka['build'],DC_GP,FOREIGN['LS'],['통격주','공격주','내진주'],'공격/통격/장인 계열 호석','심안+예리도레벨+1에 약점특효·공격을 얹기 좋은 태도 범용 커스텀.'),
 V('가루루가X 세트','밸런스형','세트',full('가루루가X'),{},FOREIGN['LS'],['방음주','달인주','참철주'],'청각보호/달인 계열','예리·귀마개·통찰 계열을 동시에 챙기는 리오소울 계열 상위호환 성격의 G급 세트.')]
G['한손검']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['SNS'],['연마주','회피주'],'회피/공격 계열','회피가 잦은 한손검과 체술+2·심검일체가 잘 맞는 G급 입문 세트.'),
 V('미쿠미쿠미','상태이상형','커스텀',miku_build or uka['build'],DC_GP,FOREIGN['SNS'],['특공주','회피주','방음주','명장주'],'장인 +4 / 3슬롯 예시','마비·수면·독 한손검에 특히 유용. 상태이상공격+1, 회피성능+1, 고급귀마개, 예리도+1 방향.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['SNS'],['명장주','회피주','연마주'],'장인/회피 계열','도전자+2+심검일체를 바탕으로 한 범용 최종 세트.'),
 V('우카우카우','공격형','커스텀',uka['build'],DC_GP,FOREIGN['SNS'],['통격주','공격주'],'통격/공격 계열','심안+예리도+1에 약점특효/공격을 얹어 짧은 리치를 보완하는 화력형.')]
G['쌍검']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['DB'],['참철주','회피주'],'예리/회피 계열','체술+2와 심검일체로 스태미나·예리 관리가 편한 G급 입문.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['DB'],['명장주','참철주','속성주'],'장인/속성 계열','도전자+2+심검일체를 활용하는 범용 화력 세트. 속성 쌍검은 해당 속성 강화 장식주를 우선.'),
 V('셀레네X 세트','밸런스형','세트',full('셀레네X'),{},FOREIGN['DB'],['속성주','회피주','참철주'],'속성/회피 계열','귀마개 계열과 스태미나 관련 보조를 활용하기 쉬운 선택지.','해외 DB 논의에서는 런너보다 업물(예리) 우선 의견이 강하고, 스태미나는 강주약으로 관리하는 경우가 많음.'),
 V('우카우카우','공격형','커스텀',uka['build'],DC_GP,FOREIGN['DB'],['참철주','속성주','통격주'],'속성/통격 계열','예리도+1 기반 화력 커스텀. 업물/속성 강화가 우선이고 런너는 취향·강주약 사용 여부에 따라 선택.','해외 MH4U도 쌍검 전용 필수는 업물 쪽을 더 높게 보고 런너는 필수로 보지 않음.')]
G['해머']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['HAM'],['통격주','방음주'],'통격/청각보호 계열','초반 안정용. 이후 약점특효·도전자·귀마개 방향으로 전환.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['HAM'],['통격주','공격주','방음주'],'통격/공격 계열','도전자+2를 살리고 머리 타격을 위한 약점특효를 추가하는 화력형.'),
 V('우카우카우','공격형','커스텀',uka['build'],DC_GP,FOREIGN['HAM'],['통격주','공격주'],'통격/공격 계열','심안+예리도+1 기반. 약점특효를 넣어 머리 집중 타격에 맞춤.'),
 V('가루루가X 세트','밸런스형','세트',full('가루루가X'),{},FOREIGN['HAM'],['방음주','통격주'],'청각보호/통격 계열','귀마개·회심·예리 관리가 편한 안정형.','해외는 약점특효·도전자+2·고급귀마개를 해머 주요 스킬로 반복 추천.')]
G['수렵피리']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['HH'],['고적주','공격주'],'피리/공격 계열','G급 입문. 피리명인은 장식주로 가볍게 추가하고 나머지는 공격 스킬을 우선.'),
 V('가루루가X 세트','밸런스형','세트',full('가루루가X'),{},FOREIGN['HH'],['고적주','방음주','공격주'],'피리/공격 계열','귀마개·회심·예리 기반에 피리명인을 추가하기 쉬운 구성.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['HH'],['고적주','공격주','명장주'],'피리/공격/장인 계열','피리명인만 최소 투자하고 도전자+2·심검일체를 활용하는 공격형.'),
 V('우카우카우','공격형','커스텀',uka['build'],DC_GP,FOREIGN['HH'],['고적주','통격주'],'피리/통격 계열','예리도+1 기반의 범용 커스텀에 피리명인을 추가.','해외 커뮤니티도 지원 전용보다 일반 검사 화력 스킬+Maestro를 권하는 의견이 강함.')]
G['랜스']=[
 V('자자미X 세트','방어형','세트',herm['build'],DC_INV,FOREIGN['LANCE'],['철벽주','강벽주'],'가드성능/가드강화 또는 슬롯 호석','G1 가드랜스 입문. 기본 가드성능+2와 많은 슬롯을 활용.'),
 V('보로스X 세트','밸런스형','세트',full('보로스X'),DC_INV,FOREIGN['LANCE'],['강벽주','공격주'],'가드강화/공격 계열','가드성능+2+공격UP 계열로 자자미X보다 공격적인 G1 선택.'),
 V('G2 가드 랜스 커스텀','방어형','커스텀',lance_mix['build'],DC_INV,FOREIGN['LANCE'],['철벽주','명장주'],'3슬롯 호석','가드성능+2와 예리도레벨+1을 동시에 노리는 G2 정석 방향.'),
 V('나르가X 세트','회피형','세트',full('나르가X'),{},FOREIGN['LANCE'],['회피주','도약주'],'회피성능/회피거리 계열','가드 대신 회피랜스를 운용할 때의 해외 커뮤니티 대표 선택지.','해외는 가드랜스와 회피랜스를 명확히 분리하며 Narga 계열을 회피형으로 추천.')]
G['건랜스']=[
 V('자자미X 세트','방어형','세트',herm['build'],DC_INV,FOREIGN['GL'],['포술주','철벽주'],'포술/가드 계열','G1 입문. 가드성능+2를 확보한 뒤 포술을 슬롯으로 추가.'),
 V('보로스X 세트','밸런스형','세트',full('보로스X'),DC_INV,FOREIGN['GL'],['포술주','강벽주'],'포술/가드강화 계열','공격과 가드를 같이 챙기는 G1 선택. 다만 슬롯이 적어 포술 고레벨은 어렵다.'),
 V('G2 포술 건랜스 커스텀','포술형','커스텀',gl_mix['build'],DC_INV,FOREIGN['GL'],['포술주 ×6','철벽주 ×3'],'자유 호석','국내 인벤에 명시된 가드성능+2·예리·포술마스터 G2 건랜스 조합.'),
 V('셀타스X 세트','포술형','세트',full('셀타스X'),DC_INV,FOREIGN['GL'],['포술주','명장주'],'장인/포술 계열','포술계 스킬 포인트가 높은 풀세트 대안. 포격 중심 운용에 사용.')]
G['슬래시액스']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['SA'],['회피주','도약주','참철주'],'회피거리/회피성능 계열','G급 입문. 체술+2와 심검일체로 기동·예리 관리가 편함.'),
 V('나르가X 세트','회피형','세트',full('나르가X'),{},FOREIGN['SA'],['회피주','도약주'],'회피거리 계열','슬래시액스의 낮은 기동성을 회피거리UP으로 보완하는 해외 대표 선택.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['SA'],['도약주','명장주'],'회피거리/장인 계열','도전자+2+심검일체에 회피거리UP을 추가하는 범용 최종형.'),
 V('고어X 세트','공격형','세트',full('고어X'),{},FOREIGN['SA'],['도약주','명장주'],'회피거리/장인 계열','도전자 계열을 기본으로 화력을 챙기는 해외 진행 대안.')]
G['차지액스']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['CB'],['포술주','철벽주'],'포술/가드 계열','G급 입문. 이후 유탄병이면 포술사, 가드포인트 운용이면 가드성능을 추가.'),
 V('셀타스X 세트','포술형','세트',full('셀타스X'),{},FOREIGN['CB'],['포술주','명장주','철벽주'],'장인 +5 전후 호석 예시','해외 MH4U에서 Sharpness+1/Razor Sharp/Artillery God 조합용 풀세트로 자주 언급.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['CB'],['포술주','철벽주','명장주'],'포술/가드/장인 계열','도전자+2+심검일체에 포술사를 추가. 유탄병 차액 범용.'),
 V('우카우카우','공격형','커스텀',uka['build'],DC_GP,FOREIGN['CB'],['포술주','통격주','공격주'],'공격 +8 예시','국내 글 작성자가 차지액스가 가장 잘 쓰기 좋은 장비라고 직접 평가한 범용 커스텀.','해외도 차액은 예리도·공격·도전자에 포술사/가드성능을 추가하는 방향을 권장.')]
G['조충곤']=[
 V('레기오스X 세트','밸런스형','세트',reg['build'],DC_G,FOREIGN['IG'],['명장주','공격주'],'장인/공격 계열','G급 초반 입문용. 심검일체로 연타 무기의 예리도 관리가 편함.'),
 V('스타나이트 세트','공격형','세트',star['build'],DC_G,FOREIGN['IG'],['명장주','공격주','방음주'],'장인 +5 1슬롯 예시','도전자+2·심검일체·탑승마스터가 조충곤과 특히 잘 맞는 대표 최종 세트.','국내/해외 모두 Star Knight를 조충곤 대표 세트로 강하게 추천.'),
 V('가루루가X 세트','밸런스형','세트',full('가루루가X'),{},FOREIGN['IG'],['방음주','명장주'],'청각보호/장인 계열','고급귀마개·회심·예리 관리 쪽으로 확장 가능한 안정형.'),
 V('미쿠미쿠미','상태이상형','커스텀',miku_build or uka['build'],DC_GP,FOREIGN['IG'],['특공주','회피주','명장주'],'장인 +4 3슬롯 예시','마비·수면·독 조충곤에 상태이상+회피+예리도 보강 방향으로 활용.')]

# Gunner: 국내 하/상 범용 교복 근거가 원문에서 명시적으로 제외되므로 빈 목록 유지, G는 국내/해외 근거만 수록.
G['라이트보우건']=[
 V('스타나이트 거너 세트','공격형','세트',full('스타나이트','gunner'),{},FOREIGN['LBG'],['속성주','강탄주/관통주','회피주'],'주력 탄/속성 강화 호석','고정 교복이 아니라 주력 탄종에 맞춰 장식주를 바꾸는 해외 비교용 범용 베이스.','해외 MH4U는 LBG를 탄종별로 나눠 속성강화 또는 Normal/Pierce/Pellet Up을 우선.'),
 V('가루루가X 거너 세트','밸런스형','세트',full('가루루가X','gunner'),{},FOREIGN['LBG'],['강탄주/관통주','회피주','도약주'],'탄강화/회피 계열','귀마개·회심 기반 범용 베이스. 실제 추천은 사용하는 라보의 속사 탄종에 맞춰 결정.'),
 V('고어X 거너 세트','공격형','세트',full('고어X','gunner'),{},FOREIGN['LBG'],['속성주','강탄주/관통주'],'속성/탄강화 계열','도전자 계열을 살리는 공격형 베이스. 국내 고정 교복 근거는 부족해 해외 비교 항목으로만 수록.')]
G['헤비보우건']=[
 V('자자미Z 거너 세트','관통형','세트',full('자자미Z','gunner'),DC_INV,FOREIGN['HBG'],['관통주','반동주','도약주'],'관통강화/회피거리 계열','국내 인벤이 G1 관통 헤보용으로 직접 추천. 반동경감+1·관통탄/관통활 강화·근성 기반.'),
 V('진아마기 거너 세트','관통형','해외 커뮤니티',full('진아마기【','gunner'),{},FOREIGN['HBG'],['관통주','반동주','도약주'],'회피거리/관통 계열','관통 HBG 최종 방향 비교용. 반동경감+1·관통강화·회피거리UP을 우선.'),
 V('가루루가X 거너 세트','통상형','세트',full('가루루가X','gunner'),{},FOREIGN['HBG'],['강탄주','도약주','도전주'],'통상강화/회피거리 계열','통상탄 운용 시 Normal Up과 회피거리UP을 추가하는 범용 베이스.'),
 V('스타나이트 거너 세트','공격형','세트',full('스타나이트','gunner'),{},FOREIGN['HBG'],['관통주/강탄주','반동주','도약주'],'탄종별 강화/회피거리 계열','최종적으로 탄종강화+회피거리+공격 스킬을 맞추는 방향의 비교용 베이스.')]
G['활']=[
 V('스타나이트 거너 세트','공격형','세트',full('스타나이트','gunner'),{},FOREIGN['BOW'],['단축주','강탄주/산탄주/관통주'],'집중 + 탄/화살강화 호석','활은 활의 3차지 화살 타입에 맞춰 Normal/Rapid, Pellet/Spread, Pierce Up 중 하나와 집중을 우선.','해외 커뮤니티도 집중을 최우선으로 두고 화살 타입 강화 선택을 강조.'),
 V('셀레네X 거너 세트','밸런스형','세트',full('셀레네X','gunner'),{},FOREIGN['BOW'],['단축주','강탄주/산탄주/관통주'],'집중/화살강화 계열','귀마개 등 안정성을 확보한 뒤 집중+화살타입 강화를 맞추는 방향.'),
 V('가루루가X 거너 세트','밸런스형','세트',full('가루루가X','gunner'),{},FOREIGN['BOW'],['단축주','강탄주/산탄주/관통주'],'집중/화살강화 계열','회심·귀마개 베이스. 국내 고정 활 교복 근거가 부족해 해외 비교용으로만 수록.')]

entries=[]
for w in weapon_types:
  if w in blade:
    entries.append({'weaponType':w,'rank':'low','rankLabel':'하위','hunterType':'blade','variants':common_low(w),'researchNote':'국내 하위 교복 자료의 검사 범용 세트. 무기별 고정 교복이 아니라 진행용 공통 세트.'})
    entries.append({'weaponType':w,'rank':'high','rankLabel':'상위','hunterType':'blade','variants':common_high(w),'researchNote':'국내 상위 교복 자료의 검사 범용 세트. G급부터 무기별 세팅을 분리.'})
  else:
    entries.append({'weaponType':w,'rank':'low','rankLabel':'하위','hunterType':'gunner','variants':[],'researchNote':'국내 교복 원문이 거너는 탄종별 차이가 커 범용 추천에서 제외했다고 명시. 확인되지 않은 고정 세트는 넣지 않음.'})
    entries.append({'weaponType':w,'rank':'high','rankLabel':'상위','hunterType':'gunner','variants':[],'researchNote':'국내 교복 원문이 거너는 탄종별 차이가 커 범용 추천에서 제외했다고 명시. 확인되지 않은 고정 세트는 넣지 않음.'})
  entries.append({'weaponType':w,'rank':'g','rankLabel':'G급','hunterType':'blade' if w in blade else 'gunner','variants':G[w],'researchNote':'국내 자료를 우선하고 해외 MH4U 커뮤니티를 교차 비교. 국내 근거가 없는 항목은 해외 비교 항목으로 명시.'})

out={
 'generatedAt':'2026-09-18T10:30:00+09:00',
 'method':'자동조합을 추천 DB 생성에 사용하지 않음. 국내 MH4G 교복/커스텀 자료를 우선 수집하고, 해외 MH4U 커뮤니티와 무기별 핵심 스킬을 교차 비교.',
 'progressionNote':'추천 카드의 장식주/호석은 커뮤니티 예시 또는 해당 세트를 활용하는 대표 방향이며, 실제 보유 호석·무기 슬롯에 따라 조정.',
 'weaponTypes':weapon_types,'entries':entries,
 'sources':[
  DC_LOW,DC_HIGH,DC_G,DC_GP,DC_INV,
  *[{'type':'해외 커뮤니티 비교','title':v['title'],'url':v['url']} for v in FOREIGN.values()]
 ]
}
json.dump(out,open(f'{BASE}/recommended_loadouts.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
print('entries',len(entries),'cards',sum(len(e['variants']) for e in entries))
