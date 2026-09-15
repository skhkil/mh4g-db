#!/usr/bin/env python3
"""Precompute monster hitzone highlights for the UI.

Rules:
- Determine primary elemental weakness from monster_summary element grades.
- Badge targets are ELEMENT-ONLY; physical maxima are kept as audit metadata only.
- bestPart is the highest hitzone part of the strongest primary element.
- Handles compound values such as "19 / 24" by comparing their maximum numeric value.
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
ELEMENTS=('fire','water','thunder','ice','dragon')
PHYSICAL=('cut','impact','shot')
GRADE={'◎':5,'○':4,'△':3,'▲':2,'×':1,'-':0,'':0,None:0}

def load(name):
    return json.loads((DATA/name).read_text(encoding='utf-8'))

def val(v):
    nums=re.findall(r'-?\d+(?:\.\d+)?',str(v or ''))
    return max((float(x) for x in nums), default=0.0)

def maxima(parts,key):
    m=max((val(p.get(key)) for p in parts),default=0.0)
    return m,[p.get('part','') for p in parts if val(p.get(key))==m and p.get('part')]

def main():
    summaries=load('monster_summary.json')
    details={x.get('name'):x for x in load('monster_details.json')}
    for mon in summaries:
        parts=(details.get(mon.get('name')) or {}).get('parts') or []
        if not parts:
            continue
        elems=mon.get('elements') or {}
        top=max((GRADE.get(elems.get(k),0) for k in ELEMENTS),default=0)
        primary=[k for k in ELEMENTS if GRADE.get(elems.get(k),0)==top and top>0]
        # If grade metadata is unavailable, fall back to raw elemental hitzone maxima.
        if not primary:
            raw={k:maxima(parts,k)[0] for k in ELEMENTS}
            topv=max(raw.values(),default=0)
            primary=[k for k in ELEMENTS if raw[k]==topv and topv>0]
        max_values={}; best_parts={}
        for key in (*PHYSICAL,*primary):
            m,b=maxima(parts,key); max_values[key]=m; best_parts[key]=b
        chosen=max(primary,key=lambda k:max_values.get(k,0),default=None)
        best_part=(best_parts.get(chosen) or [parts[0].get('part','')])[0]
        mon['hitzoneHighlights']={
            'bestPart':best_part,
            'primaryElements':primary,
            'primaryElement':chosen,
            'maxValues':max_values,
            'bestParts':best_parts,
        }
    (DATA/'monster_summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'updated {len(summaries)} monsters')

if __name__=='__main__': main()
