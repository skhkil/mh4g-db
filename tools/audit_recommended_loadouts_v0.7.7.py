import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rec=json.loads((ROOT/'data/recommended_loadouts.json').read_text())
rank_order={'low':1,'high':2,'g':3}
issues=[]
expected=set(rec.get('weaponTypes',[]))
seen=set()
variant_count=0
for e in rec.get('entries',[]):
    key=(e['weaponType'],e['rank']); seen.add(key)
    targets={x['skillId']:int(x['points']) for x in e.get('targets',[])}
    if not e.get('variants'): issues.append({'type':'empty_variants','key':key})
    for v in e.get('variants',[]):
        variant_count+=1
        active={x['skillId']:int(x.get('points',0)) for x in v.get('build',{}).get('activated',[])}
        miss=[sid for sid,need in targets.items() if active.get(sid,0)<need]
        if miss: issues.append({'type':'missing_target','key':key,'variant':v['label'],'missing':miss})
        for a in v.get('build',{}).get('armors',[]):
            if rank_order.get(a.get('rank'),99)>rank_order[e['rank']]: issues.append({'type':'rank_over','key':key,'armor':a['name'],'armorRank':a.get('rank')})
for w in expected:
    for r in ('low','high','g'):
        if (w,r) not in seen: issues.append({'type':'missing_entry','key':[w,r]})
audit={'weaponTypes':len(expected),'entries':len(rec.get('entries',[])),'variants':variant_count,'issues':issues,'hardErrors':len(issues)}
(ROOT/'tools/recommended_loadouts_audit_v0.7.7.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
lines=['# 추천 장비 감사 v0.7.7','',f'- 무기종: {audit["weaponTypes"]}',f'- 하위/상위/G급 프로필: {audit["entries"]}',f'- 추천 조합: {audit["variants"]}',f'- 하드 오류: {audit["hardErrors"]}','','## 기준','- 자동조합 엔진 사전계산','- 호석 없음 / 무기 슬롯 0 / 장식주 허용','- 모든 추천 조합은 목표 스킬 충족과 진행도 초과 여부를 재검증','- 라이트보우건/헤비보우건/활은 탄종·사격 타입에 따라 핵심 스킬이 달라질 수 있어 범용 예시로 표시']
if issues:
    lines+=['','## 문제']+[f'- {x}' for x in issues]
(ROOT/'tools/recommended_loadouts_audit_v0.7.7.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(audit,ensure_ascii=False))
