#!/usr/bin/env python3
"""Precompute monster hitzone highlights for the UI.

Rules (chat 4, part-wise elemental highlights):
- Every monster part gets exactly one best elemental attribute when its best value is > 0.
- The best attribute is chosen by raw hitzone value; ties are broken by the monster's
  element-grade metadata, then by a stable element order.
- Rank parts by that per-part best elemental value and mark the strongest top 3 parts
  (or fewer when fewer valid parts exist) with a part badge.
- UI only reads this precomputed metadata; no comparison/search runs on monster click.
- Compound values such as "19 / 24" are compared by their maximum numeric value.
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
ELEMENTS=('fire','water','thunder','ice','dragon')
GRADE={'◎':5,'○':4,'△':3,'▲':2,'×':1,'-':0,'':0,None:0}


def load(name):
    return json.loads((DATA/name).read_text(encoding='utf-8'))


def val(v):
    nums=re.findall(r'-?\d+(?:\.\d+)?',str(v or ''))
    return max((float(x) for x in nums), default=0.0)


def main():
    summaries=load('monster_summary.json')
    details={x.get('name'):x for x in load('monster_details.json')}
    detail_alias={
        '임계 브라키디오스':'맹폭 브라키디오스',
        '혼돈의 고어·마가라':'혼돈에 신음하는 고어·마가라',
        '밀라보레아스':'밀라보레아스 (흑룡)',
        '밀라보레아스 (조룡)':'밀라보레아스 (선조룡)',
    }
    audit=[]
    for mon in summaries:
        detail_name=detail_alias.get(mon.get('name'), mon.get('name'))
        parts=(details.get(detail_name) or {}).get('parts') or []
        elems=mon.get('elements') or {}
        part_best={}
        ranked=[]
        for idx,part in enumerate(parts):
            values={k:val(part.get(k)) for k in ELEMENTS}
            maxv=max(values.values(),default=0.0)
            if maxv<=0:
                continue
            tied=[k for k in ELEMENTS if values[k]==maxv]
            # One badge per part: stronger monster-wide weakness grade wins a raw-value tie.
            chosen=sorted(tied,key=lambda k:(-GRADE.get(elems.get(k),0), ELEMENTS.index(k)))[0]
            name=part.get('part','')
            if not name:
                continue
            part_best[name]={'element':chosen,'value':maxv}
            ranked.append((maxv, GRADE.get(elems.get(chosen),0), -idx, name, chosen))

        ranked.sort(reverse=True)
        top_parts=[x[3] for x in ranked[:3]]
        best_part=top_parts[0] if top_parts else (parts[0].get('part','') if parts else '')
        mon['hitzoneHighlights']={
            'bestPart':best_part,
            'topElementParts':top_parts,
            'partBestElements':{name:meta['element'] for name,meta in part_best.items()},
            'partBestValues':{name:meta['value'] for name,meta in part_best.items()},
        }
        audit.append({
            'monster':mon.get('name'),
            'bestPart':best_part,
            'topElementParts':top_parts,
            'parts':[{'part':name,**meta} for name,meta in part_best.items()],
        })

    (DATA/'monster_summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DATA/'monster_hitzone_highlight_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'updated {len(summaries)} monsters; audit {len(audit)}')

if __name__=='__main__':
    main()
