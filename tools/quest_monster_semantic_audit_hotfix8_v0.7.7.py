#!/usr/bin/env python3
from pathlib import Path
import json, collections, sys
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
load=lambda n: json.loads((D/n).read_text(encoding='utf-8'))
qs=load('quests.json'); qby={q['id']:q for q in qs}
mons=load('monster_summary.json'); mnames={m['name'] for m in mons}
qidx=load('quest_reference_index.json')['quests']; mref=load('monster_references.json')
issues=[]; checks=[]
def ok(cond,label,detail=None):
    checks.append({'name':label,'ok':bool(cond),'detail':detail})
    if not cond: issues.append({'name':label,'detail':detail})
# Structural integrity.
ok(len(qs)==572,'quest_count_572',len(qs))
ok(sum(q.get('questType')=='village' for q in qs)==193,'caravan_count_193')
ok(sum(q.get('questType') in ('hub','g') for q in qs)==258,'guild_count_258')
unknown=[]
for qid,row in qidx.items():
    for n in row.get('monsters',[]):
        if n not in mnames: unknown.append((qid,n))
ok(not unknown,'all_quest_monsters_are_canonical',unknown[:20])
# Reverse relation must be a true inversion, not a separately guessed relation.
forward={(qid,n) for qid,row in qidx.items() for n in row.get('monsters',[])}
reverse=set()
for name,row in mref.items():
    for q in row.get('quests',[]): reverse.add((q.get('id'),name))
ok(forward==reverse,'forward_reverse_exact_inverse',{'forward':len(forward),'reverse':len(reverse),'missingReverse':list(forward-reverse)[:10],'extraReverse':list(reverse-forward)[:10]})
# Authoritatively verified special-individual standard quests. Kiranico/MH4G sources checked 2026-10-02.
expected={
 '녹슨크샬다오라': {'quest_1dd30bcc8189','quest_c83c67f7419a','quest_h8_g3_operation_rust_remover'},
 '혼돈의 고어·마가라': {'quest_h8_c10_all_in_place','quest_6acd493ed64d','quest_5f701615a1a9','quest_750a954c6940'},
 '임계 브라키디오스': {'quest_6cae3017e9a4'},
 '광폭 이블조': {'quest_558d05b90a04'},
 '밀라보레아스 (홍룡)': {'quest_h8_c10_red_dragon_dawn'},
 '밀라보레아스 (홍염룡)': {'quest_fe44e93bc43b'},
}
standard_types={'village','hub','g'}
for mon,want in expected.items():
    got={qid for qid,row in qidx.items() if qby.get(qid,{}).get('questType') in standard_types and mon in row.get('monsters',[])}
    ok(got==want,f'special_standard_{mon}',{'expected':sorted(want),'actual':sorted(got)})
# Furious Rajang: standard known appearances available in this project source set.
furious_known={'quest_h8_c6_caravaneer_challenge','quest_h8_c10_bad_hair_rajang','quest_7550d093194d','quest_d79e85dfcb06','quest_ade6bb5f20bb'}
furious_got={qid for qid,row in qidx.items() if qby.get(qid,{}).get('questType') in standard_types and '격앙 라잔' in row.get('monsters',[])}
ok(furious_known.issubset(furious_got),'furious_rajang_known_appearances',{'required':sorted(furious_known),'actual':sorted(furious_got)})
# Exact semantic spot checks that previously failed or are hidden behind generic base-species objective labels.
spots={
 'quest_c83c67f7419a':['녹슨크샬다오라'],
 'quest_h8_g3_operation_rust_remover':['녹슨크샬다오라'],
 'quest_fd112c29a3cc':['크샬다오라'],
 'quest_5f611f56f63c':['크샬다오라'],
 'quest_5f701615a1a9':['진오우거 아종','혼돈의 고어·마가라'],
 'quest_6acd493ed64d':['혼돈의 고어·마가라'],
 'quest_750a954c6940':['혼돈의 고어·마가라'],
 'quest_6cae3017e9a4':['임계 브라키디오스'],
 'quest_ade6bb5f20bb':['격앙 라잔'],
 'quest_fe44e93bc43b':['밀라보레아스 (홍염룡)'],
 'quest_558d05b90a04':['광폭 이블조'],
 'quest_h8_c10_masters_test':['셀레기오스','디아블로스','이블조'],
}
for qid,want in spots.items():
    got=qidx.get(qid,{}).get('monsters',[])
    ok(got==want,f'spot_{qid}',{'quest':qby.get(qid,{}).get('name'),'expected':want,'actual':got})
# Prevent base-species leakage in special-individual quests.
for qid,special,base in [
 ('quest_c83c67f7419a','녹슨크샬다오라','크샬다오라'),
 ('quest_h8_g3_operation_rust_remover','녹슨크샬다오라','크샬다오라'),
 ('quest_6cae3017e9a4','임계 브라키디오스','브라키디오스'),
 ('quest_6acd493ed64d','혼돈의 고어·마가라','고어·마가라'),
 ('quest_750a954c6940','혼돈의 고어·마가라','고어·마가라'),
 ('quest_ade6bb5f20bb','격앙 라잔','라잔'),
 ('quest_558d05b90a04','광폭 이블조','이블조')]:
    got=qidx.get(qid,{}).get('monsters',[])
    ok(special in got and base not in got,f'no_base_leak_{qid}',got)
# All explicitly curated restored quests must keep their verified list exactly.
for q in qs:
    if q.get('_verifiedMonsters'):
        ok(qidx[q['id']].get('monsters',[])==q['_verifiedMonsters'],f'verified_{q["id"]}',{'expected':q['_verifiedMonsters'],'actual':qidx[q['id']].get('monsters',[])})
report={'version':'0.7.7-chat4-quest-monster-hotfix8','questCount':len(qs),'monsterCount':len(mons),'forwardLinks':len(forward),'reverseLinks':len(reverse),'checks':checks,'issueCount':len(issues),'issues':issues}
(D/'quest_monster_semantic_audit_hotfix8_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['questCount','monsterCount','forwardLinks','reverseLinks','issueCount']},ensure_ascii=False,indent=2))
if issues: sys.exit(1)
