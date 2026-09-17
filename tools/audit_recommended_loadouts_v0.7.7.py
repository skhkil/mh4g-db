import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/recommended_loadouts.json').read_text(encoding='utf-8'))
errors=[]; warnings=[]
for e in d['entries']:
    expected=4 if e['rank']=='g' else 3
    if len(e['variants'])!=expected: errors.append(f"{e['weaponType']}/{e['rank']}: variants={len(e['variants'])} expected={expected}")
    for v in e['variants']:
        act={}
        for x in v.get('build',{}).get('activated',[]): act[x['skillId']]=max(int(x.get('points',0)),act.get(x['skillId'],0))
        for t in v.get('targets',[]):
            if act.get(t['skillId'],0)<int(t['points']): errors.append(f"{e['weaponType']}/{e['rank']}/{v['label']}: {t['name']} 미충족")
        if v.get('relaxed'): warnings.append(f"{e['weaponType']}/{e['rank']}/{v['label']}: 완화 {v['relaxed']}")
        if len(v.get('build',{}).get('armors',[]))!=5: errors.append(f"{e['weaponType']}/{e['rank']}/{v['label']}: 방어구 5부위 아님")
audit={'weaponTypes':len(d['weaponTypes']),'entries':len(d['entries']),'variants':sum(len(e['variants']) for e in d['entries']),'lowVariants':sum(len(e['variants']) for e in d['entries'] if e['rank']=='low'),'highVariants':sum(len(e['variants']) for e in d['entries'] if e['rank']=='high'),'gVariants':sum(len(e['variants']) for e in d['entries'] if e['rank']=='g'),'hardErrors':len(errors),'warnings':len(warnings),'errors':errors,'warningRows':warnings}
(ROOT/'tools/recommended_loadouts_audit_v0.7.7.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 추천 장비 감사 v0.7.7','',f'- 무기종: {audit["weaponTypes"]}',f'- 프로필: {audit["entries"]} (14 × 하위/상위/G급)',f'- 추천 조합: {audit["variants"]}',f'  - 하위: {audit["lowVariants"]}',f'  - 상위: {audit["highVariants"]}',f'  - G급: {audit["gVariants"]}',f'- 하드 오류: {audit["hardErrors"]}',f'- 목표 완화: {audit["warnings"]}','','## 설계','- 하위/상위: 공격형 / 방어형 / 균형형 3종','- G급: 무기별 커뮤니티 핵심스킬 기반 4종','- 호석 없음 / 무기 슬롯 0 기준으로 프로젝트 자동조합 엔진에서 실제 조합 검증','- 커뮤니티 자료는 핵심 스킬/플레이스타일 근거로 사용하며, 정확한 장비 조합을 그대로 옮기지 않은 경우 UI에서 커뮤니티 기반 커스텀으로 구분']
if errors: lines+=['','## 오류']+['- '+x for x in errors]
if warnings: lines+=['','## 완화']+['- '+x for x in warnings]
(ROOT/'tools/recommended_loadouts_audit_v0.7.7.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False))
