#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'
x=json.loads((D/'quest_unlock_index.json').read_text(encoding='utf-8'))
qs={q['id']:q for q in json.loads((D/'quests.json').read_text(encoding='utf-8'))}
dr=json.loads((D/'dragon_exchange.json').read_text(encoding='utf-8'))
decos={d['id']:d for d in json.loads((D/'decorations.json').read_text(encoding='utf-8'))}
issues=[]
relations=x.get('relations',[])
for r in relations:
    if r['questId'] not in qs: issues.append({'type':'missingQuest','relation':r})
    qrows=x.get('quests',{}).get(r['questId'],{}).get('unlocks',[])
    if not any(y.get('targetType')==r['targetType'] and y.get('targetId')==r['targetId'] and y.get('relation')==r['relation'] for y in qrows):
        issues.append({'type':'missingForward','relation':r})
    tk=f"{r['targetType']}:{r['targetId']}"; t=x.get('targets',{}).get(tk)
    if not t or not any(y.get('questId')==r['questId'] and y.get('relation')==r['relation'] for y in t.get('quests',[])):
        issues.append({'type':'missingReverse','relation':r})
for i in range(len(dr)):
    tk=f'wyporium_exchange:exchange:{i}'
    if tk not in x.get('targets',{}): issues.append({'type':'unlinkedWyporiumExchange','index':i,'row':dr[i]})
for tk,t in x.get('targets',{}).items():
    if t.get('type')=='decoration' and t.get('id') not in decos: issues.append({'type':'missingDecoration','target':t})
report={
 'ok':not issues,
 'relationCount':len(relations),
 'forwardCount':sum(len(v.get('unlocks',[])) for v in x.get('quests',{}).values()),
 'reverseCount':sum(len(v.get('quests',[])) for v in x.get('targets',{}).values()),
 'wyporiumExchangeRows':len(dr),
 'wyporiumTargets':sum(t.get('type')=='wyporium_exchange' for t in x.get('targets',{}).values()),
 'decorationTargets':sum(t.get('type')=='decoration' for t in x.get('targets',{}).values()),
 'unresolvedCount':len(x.get('unresolved',[])),
 'needsReviewCount':x.get('summary',{}).get('needsReviewCount',0),
 'issues':issues
}
out=ROOT/'tools'/'quest_unlock_xref_audit_v0.7.7.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(0 if report['ok'] else 1)
