import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'; T=ROOT/'tools'
load=lambda p: json.loads(Path(p).read_text())
armors=load(D/'armors.json'); items=load(D/'items.json'); quests=load(D/'quests.json'); audit=load(T/'missing_armor_restore_audit_v0.7.7.json')
restored={x['id'] for x in audit['restored']}; itemids={x['id'] for x in items}; qids={x['id'] for x in quests}
rows=[a for a in armors if a['id'] in restored]
errs=[]; mats=0; unresolved=0; project_q=0; gx=[]
for a in rows:
    p=a.get('progression') or {}
    if not p.get('materials'): errs.append(f"no progression: {a['name']}"); continue
    if a['name'].startswith('GX'): gx.append(a)
    for m in p['materials']:
        mats+=1
        if m.get('itemId') and m['itemId'] not in itemids: errs.append(f"bad item {a['name']} {m['name']} {m['itemId']}")
        ss=m.get('sources') or []
        if not ss: unresolved+=1; errs.append(f"no source {a['name']} {m['name']}")
        for s in ss:
            if s.get('type')=='quest' and s.get('id'):
                project_q+=1
                if s['id'] not in qids: errs.append(f"bad quest {a['name']} {m['name']} {s['id']}")
# GX key routes
expect={
 'GX그리드':'event-g-076',
 'GX황천':'event-g-071',
 'GX창천':'event-g-071',
 'GX밀라발Z':'event-g-078',
}
for prefix,qid in expect.items():
    matches=[a for a in gx if a['name'].startswith(prefix)]
    if not matches: errs.append(f'missing GX family {prefix}'); continue
    for a in matches:
        got={s.get('id') for m in a['progression']['materials'] for s in m.get('sources',[]) if s.get('type')=='quest'}
        if qid not in got: errs.append(f'missing event route {a["name"]} -> {qid}')
print(json.dumps({'restoredArmors':len(rows),'materials':mats,'gxArmors':len(gx),'unresolved':unresolved,'projectQuestLinks':project_q,'errors':len(errs),'errorSamples':errs[:20]},ensure_ascii=False,indent=2))
sys.exit(1 if errs else 0)
