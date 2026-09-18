import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
rec=json.load(open(D/'recommended_loadouts.json',encoding='utf-8'))
decos=json.load(open(D/'decorations.json',encoding='utf-8')); byname={x['name']:x for x in decos}

def deco(name,count):
 d=byname[name]; return {'id':d['id'],'name':d['name'],'slots':d['slots'],'count':count}

def placement(name,container): return {'id':byname[name]['id'],'container':container}

# 국내 하위 원문 직접 근거가 없는 람포스 카드는 제거. 재기/카브라 2종이 원문 교복.
for e in rec['entries']:
 if e['rank']=='low' and e['hunterType']=='blade':
  e['variants']=[v for v in e.get('variants',[]) if v.get('label')!='람포스 세트']
  e['researchNote']='국내 하위 교복 원문에서 직접 소개한 재기·카브라 2종만 유지. 람포스는 직접 근거가 없어 제외.'

for e in rec['entries']:
 for v in e.get('variants',[]):
  label=v.get('label',''); b=v.get('build',{})
  # defaults: actual equipped build, not hypothetical skill target
  base=[x.get('name') for x in b.get('activated',[]) if x.get('name')]
  v['exampleEvidence']='기본 구성 검증'
  v['decorationPlacementExample']='현재 카드의 적용 장식주 기준. 추가 장식주는 보유 호석·무기 슬롯에 따라 조정.'
  v['finalSkillsExample']=base

  if label=='재기 세트':
   v['exampleEvidence']='국내 원문 기본 세트'
   v['decorationPlacementExample']='추가 장식주 없이 숫돌사용고속화·기절확률반감을 그대로 활용. 슬롯은 공격/생존 보조에 사용.'
  elif label=='카브라 세트':
   b['decorations']=[deco('체력주【1】',1),deco('채집주【1】',1)]
   b['decorationPlacements']=[placement('체력주【1】','head'),placement('채집주【1】','arms')]
   v['recommendedDecorations']=['체력주【1】 ×1','채집주【1】 ×1']
   v['talismanGuide']='호석 불필요(원문 예시)'
   v['talismanSocketGuide']='원문 예시는 방어구 2슬롯만 사용. 호석 슬롯은 자유 보조.'
   v['decorationPlacementExample']='머리 1슬롯: 체력주【1】 ×1 / 팔 1슬롯: 채집주【1】 ×1.'
   v['exampleEvidence']='국내 원문 장식주 예시'
  elif label=='카브라S 세트':
   b['decorations']=[deco('채집주【1】',2),deco('연마주【1】',1)]
   # 몸통의 채집주는 몸통배가(다리)로 2배 반영됨
   b['decorationPlacements']=[placement('채집주【1】','body'),placement('채집주【1】','head'),placement('연마주【1】','arms')]
   v['recommendedDecorations']=['채집주【1】 ×2','연마주【1】 ×1']
   v['talismanGuide']='호석 불필요(원문 예시)'
   v['talismanSocketGuide']='머리/몸통/팔 3슬롯을 사용하므로 호석 슬롯은 자유 보조.'
   v['decorationPlacementExample']='몸통: 채집주【1】 / 머리: 채집주【1】 / 팔: 연마주【1】. 몸통 장식주는 몸통배가로 2배 적용.'
   v['exampleEvidence']='국내 원문 장식주 예시'
  elif label=='리오소울 세트':
   b['decorations']=[deco('방음주【1】',5),deco('체력주【1】',2)]
   # 7 armor slots, no torso-up; deterministic explicit placement
   b['decorationPlacements']=[
    placement('방음주【1】','head'),placement('방음주【1】','head'),placement('방음주【1】','head'),
    placement('방음주【1】','body'),placement('방음주【1】','arms'),
    placement('체력주【1】','waist'),placement('체력주【1】','legs')]
   v['recommendedDecorations']=['방음주【1】 ×5','체력주【1】 ×2']
   v['talismanGuide']='호석 불필요(국내 정석 예시)'
   v['talismanSocketGuide']='방어구 7슬롯을 모두 쓰는 예시. 호석 슬롯은 다른 스킬로 교체할 때 사용.'
   v['decorationPlacementExample']='머리: 방음주【1】×3 / 몸통: 방음주【1】 / 팔: 방음주【1】 / 허리·다리: 체력주【1】 각 1.'
   v['exampleEvidence']='국내 원문 정석 장식주 예시'
  elif label=='진오우U 세트':
   v['talismanGuide']='회피성능 +5 / 2슬롯 호석(국내 원문 예시)'
   v['talismanSocketGuide']='원문은 2슬롯 무기 + 호석 2슬롯을 함께 사용해 회피성능+3과 숫돌사용고속화를 구성.'
   v['decorationPlacementExample']='무기 2슬롯 + 회피성능+5/2슬롯 호석을 전제로 회피·연마 장식주를 배치하는 원문 예시. 정확한 장식주 개별 위치는 보유 호석에 따라 조정.'
   v['finalSkillsExample']=['회피성능+3','집중','풀차지','용속성공격UP+1','숫돌사용고속화','체력회복량DOWN']
   v['exampleEvidence']='국내 원문 호석/무기슬롯 예시'
  elif label=='레기오스X 세트':
   b['decorations']=[deco('연마주【1】',3)]
   b['decorationPlacements']=[placement('연마주【1】','head'),placement('연마주【1】','head'),placement('연마주【1】','head')]
   v['recommendedDecorations']=['연마주【1】 ×3'] + [x for x in v.get('recommendedDecorations',[]) if '연마주' not in x]
   v['decorationPlacementExample']='머리 3슬롯에 연마주【1】 ×3을 넣어 숫돌사용저속화(-10 이하)를 해제하는 국내 원문 예시.'
   v['exampleEvidence']='국내 원문 장식주 예시'
  elif label=='스타나이트 세트' and e['hunterType']=='blade':
   v['talismanGuide']='장인 +5 / 1슬롯 호석(국내 원문 정석 예시)'
   v['talismanSocketGuide']='무기 3슬롯 + 호석 1슬롯 사용. 방어구 11슬롯과 합쳐 고급귀마개·예리도레벨+1을 추가.'
   v['decorationPlacementExample']='검증 가능한 예: 머리/팔/다리 3슬롯에 방음주【3】 각 1, 몸통/허리/호석에 방음주【1】 각 1, 무기 3슬롯에 장인주【2】 1. 호석은 장인+5/1슬롯.'
   v['finalSkillsExample']=['도전자+2','탑승마스터','심검일체','고급귀마개','예리도레벨+1']
   v['exampleEvidence']='국내 원문 조건 + 프로젝트 DB 슬롯 재현'
  elif label=='디아블로X 세트':
   v['talismanGuide']='현실적 예: 집중 +5 / 3슬롯 호석. 고급 예: 공격 +10·집중 +5 호석.'
   v['talismanSocketGuide']='방어구 슬롯과 3슬롯 호석으로 집중을 우선 완성하고, 남는 슬롯으로 공격/숫돌저속화 해제를 조정.'
   v['decorationPlacementExample']='집중+5/3슬롯 호석 기준으로 단축주를 우선 배치 → 집중 발동. 남는 슬롯은 공격주 또는 연마주로 조정.'
   v['finalSkillsExample']=['발도술【기술】','납도술','내진','집중','공격력UP【소】(호석/슬롯에 따라)','숫돌사용저속화 해제 권장']
   v['exampleEvidence']='국내 원문 호석 예시'
  elif label=='미쿠미쿠미':
   v['talismanGuide']='장인 +4 / 3슬롯 호석(국내 원문 예시)'
   v['talismanSocketGuide']='무기 1슬롯 + 호석 3슬롯 + 방어구 10슬롯을 사용.'
   v['decorationPlacementExample']='장인+4/3슬롯 호석과 무기 1슬롯을 전제로 청각보호·장인·회피·연마·특수공격 장식주를 배치.'
   v['finalSkillsExample']=['고급귀마개','예리도레벨+1','회피성능+1','숫돌사용고속화','상태이상공격+1']
   v['exampleEvidence']='국내 원문 최종 스킬 예시'
  elif label=='우카우카우':
   v['talismanGuide']='공격 +8 노슬롯 호석(국내 원문 예시) 또는 통격/공격 호석'
   v['talismanSocketGuide']='기본 11슬롯을 약점특효·내진·공격 보강에 사용. 원문 예시는 공격+8 노슬롯 호석.'
   v['decorationPlacementExample']='심안+예리도레벨+1 기본 상태에서 통격주/내진주/공격주를 우선 배치. 차지액스는 포술주를 대안으로 사용.'
   v['exampleEvidence']='국내 원문 호석 예시'
  elif label=='바이바이카이저':
   v['talismanGuide']='차지단축 +2 / 3슬롯 호석(국내 원문 예시)'
   v['talismanSocketGuide']='호석 3슬롯 + 크샤나X 허리 3슬롯 등으로 집중·발도술【기술】·공격을 완성.'
   v['decorationPlacementExample']='차지단축+2/3슬롯 호석을 사용하고 단축주·발도주·공격주를 배치. 몸통배가 2부위이므로 카이저X 몸통 장식주는 3배 효율을 고려.'
   v['finalSkillsExample']=['베기술【힘】','예리도레벨+1','발도술【기술】','집중','공격력UP【소】']
   v['exampleEvidence']='국내 원문 호석/최종스킬 예시'
  elif label=='자자미X 세트':
   v['decorationPlacementExample']='기본 가드성능+2를 유지하고 빈 8슬롯에 가드강화/포술/예리도 보조를 무기별로 배치.'
   v['exampleEvidence']='국내 번역 자료 기본 세트'
  elif label=='보로스X 세트':
   v['decorationPlacementExample']='기본 가드성능+2·공격력UP【중】·체술+1을 사용하고 5슬롯은 가드강화/예리 보조에 사용.'
   v['exampleEvidence']='국내 번역 자료 기본 세트'
  elif label=='G2 가드 랜스 커스텀':
   v['talismanGuide']='3슬롯 호석(국내 번역 자료 명시)'
   v['talismanSocketGuide']='방어구 슬롯 + 3슬롯 호석으로 가드성능+2·예리도레벨+1을 구성.'
   v['decorationPlacementExample']='3슬롯 호석을 포함해 가드성능/장인 계열 장식주를 부족 포인트 순서로 배치.'
   v['finalSkillsExample']=['가드성능+2','예리도레벨+1','방어력UP【소】']
   v['exampleEvidence']='국내 번역 자료 명시 스킬'
  elif label=='자자미Z 거너 세트':
   v['decorationPlacementExample']='기본 반동경감+1·관통탄/관통활 강화·근성을 유지하고 9슬롯을 탄종/회피거리 보조에 사용.'
   v['finalSkillsExample']=['반동경감+1','관통탄·관통활 강화','근성']
   v['exampleEvidence']='국내 번역 자료 명시 스킬'
  else:
   # Foreign-only / weapon-specific cards: do not pretend a unique canonical jewel layout exists.
   if not v.get('source',{}).get('url') and v.get('foreignSource',{}).get('url'):
    v['exampleEvidence']='해외 가이드 방향(고정 장식주 조합 아님)'
    v['decorationPlacementExample']='고정 교복 장식주 조합은 확인되지 않음. 카드의 기본 발동 스킬을 유지하고 추천 장식주는 무기 탄종/슬롯에 맞춰 추가.'

rec['generatedAt']='2026-09-18T12:35:00+09:00'
rec['method']='자동조합을 추천 DB 생성에 사용하지 않음. 국내 MH4G 원문 직접 근거를 우선하고, 해외 MH4U 자료·mh4u.db·Athena Data로 방어구/스킬/슬롯을 교차검증. 원문에 없는 구성은 근거 수준을 명시.'
(D/'recommended_loadouts.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
print('refined',sum(len(e.get('variants',[])) for e in rec['entries']))
