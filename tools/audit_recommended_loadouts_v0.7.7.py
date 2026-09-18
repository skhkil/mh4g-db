import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/recommended_loadouts.json').read_text(encoding='utf-8'))
armors={x['id']:x for x in json.loads((ROOT/'data/armors.json').read_text(encoding='utf-8'))}
decos={x['id']:x for x in json.loads((ROOT/'data/decorations.json').read_text(encoding='utf-8'))}
errors=[]; warnings=[]
seen={(e['weaponType'],e['rank']) for e in d['entries']}
for w in d['weaponTypes']:
    for r in ('low','high','g'):
        if (w,r) not in seen: errors.append(f'{w}/{r}: 프로필 누락')
for e in d['entries']:
    for v in e.get('variants',[]):
        b=v.get('build') or {}
        aa=b.get('armors') or []
        if len(aa)!=5: errors.append(f"{e['weaponType']}/{e['rank']}/{v.get('label')}: 방어구 5부위 아님")
        for a in aa:
            if a.get('id') not in armors: errors.append(f"{e['weaponType']}/{e['rank']}/{v.get('label')}: 방어구 ID 누락 {a.get('id')}")
        cap=sum(int(a.get('slots',0) or 0) for a in aa)
        need=0
        for x in b.get('decorations') or []:
            if x.get('id') not in decos: errors.append(f"{e['weaponType']}/{e['rank']}/{v.get('label')}: 장식주 ID 누락 {x.get('id')}")
            need+=int(x.get('slots',0) or 0)*int(x.get('count',0) or 0)
        if need>cap: errors.append(f"{e['weaponType']}/{e['rank']}/{v.get('label')}: 장식주 슬롯 {need}>{cap}")
        if v.get('targets'): errors.append(f"{e['weaponType']}/{e['rank']}/{v.get('label')}: 추천 카드에 targets 잔존")
        if not v.get('source',{}).get('url'): warnings.append(f"{e['weaponType']}/{e['rank']}/{v.get('label')}: 출처 URL 없음")
counts={r:sum(len(e.get('variants',[])) for e in d['entries'] if e['rank']==r) for r in ('low','high','g')}
audit={'weaponTypes':len(d['weaponTypes']),'entries':len(d['entries']),'variants':sum(counts.values()),'lowVariants':counts['low'],'highVariants':counts['high'],'gVariants':counts['g'],'hardErrors':len(errors),'warnings':len(warnings),'errors':errors,'warningRows':warnings}
(ROOT/'tools/recommended_loadouts_audit_v0.7.7.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 추천 장비 감사 v0.7.7','',f'- 무기종: {audit["weaponTypes"]}',f'- 프로필: {audit["entries"]}',f'- 추천 조합: {audit["variants"]}',f'  - 하위: {audit["lowVariants"]}',f'  - 상위: {audit["highVariants"]}',f'  - G급: {audit["gVariants"]}',f'- 하드 오류: {audit["hardErrors"]}',f'- 경고: {audit["warnings"]}','','## 설계','- 추천 DB는 자동조합 엔진으로 생성하지 않음.','- 국내 MH4G 커뮤니티에서 교복/추천/대표 커스텀으로 확인되는 장비만 수록.','- 무기별 추천 수는 실제 검증 자료 수에 따라 가변. 억지로 고정 개수를 채우지 않음.','- 공격형/방어형/밸런스형은 카드의 실제 스킬 성격 태그이며 별도 그룹이 아님.','- 카드에는 목표 스킬을 두지 않고 실제 발동 스킬만 표시.']
if errors: lines+=['','## 오류']+['- '+x for x in errors]
if warnings: lines+=['','## 경고']+['- '+x for x in warnings]
(ROOT/'tools/recommended_loadouts_audit_v0.7.7.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False))
