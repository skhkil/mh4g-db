#!/usr/bin/env python3
import argparse, json, re, unicodedata, zipfile
from collections import defaultdict
from pathlib import Path

PART_FILES = {p: p + '.txt' for p in ['head','body','arms','waist','legs']}
KO_DIR = 'Data/Languages/╟╤▒╣╛ε/'
JP_DIR = 'Data/Languages/Japanese/'
EN_DIR = 'Data/Languages/English/'

def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s or ''))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project',required=True)
    ap.add_argument('--athena',required=True)
    args=ap.parse_args()
    root=Path(args.project)
    arm_path=root/'data/armors.json'
    armors=json.loads(arm_path.read_text(encoding='utf-8'))

    jp_idx=defaultdict(list); ko_idx=defaultdict(list)
    with zipfile.ZipFile(args.athena) as z:
        for part, fn in PART_FILES.items():
            jp=z.read(JP_DIR+fn).decode('utf-8-sig').splitlines()
            en=z.read(EN_DIR+fn).decode('utf-8-sig').splitlines()
            ko=z.read(KO_DIR+fn).decode('utf-8-sig').splitlines()
            if not (len(jp)==len(en)==len(ko)):
                raise SystemExit(f'Localization row count mismatch for {part}')
            for line,(j,e,k) in enumerate(zip(jp,en,ko),1):
                rec={'part':part,'line':line,'nameJa':j.strip(),'nameEn':e.strip(),'nameKo':k.strip()}
                jp_idx[(part,norm(j))].append(rec)
                ko_idx[(part,norm(k))].append(rec)

    before_primary={a['id']:a.get('name') for a in armors}
    before_protected={a['id']:(a.get('maxDefense'),a.get('upgradeDefense')) for a in armors}
    filled=[]; unresolved=[]; methods=defaultdict(int)
    for a in armors:
        match=None; method=None
        j=jp_idx.get((a['part'],norm(a.get('nameJa'))),[])
        if len(j)==1:
            match=j[0]; method='Athena Japanese exact row'
        else:
            k=ko_idx.get((a['part'],norm(a.get('name'))),[])
            if len(k)==1:
                match=k[0]; method='Athena Korean exact row'
        if match and match['nameEn']:
            old=a.get('nameEn','')
            a['nameEn']=match['nameEn']
            methods[method]+=1
            filled.append({'id':a['id'],'name':a['name'],'nameJa':a.get('nameJa',''),'nameEn':a['nameEn'],'oldNameEn':old,'basis':method,'athenaLine':match['line']})
        else:
            a.pop('nameEn',None)
            unresolved.append({'id':a['id'],'name':a['name'],'nameJa':a.get('nameJa',''),'part':a['part']})

    # Localization enrichment must never change Korean primary names or defense progression.
    for a in armors:
        if a.get('name') != before_primary[a['id']]:
            raise SystemExit('Primary Korean name changed: '+a['id'])
        if (a.get('maxDefense'),a.get('upgradeDefense')) != before_protected[a['id']]:
            raise SystemExit('Protected defense progression changed: '+a['id'])

    arm_path.write_text(json.dumps(armors,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    # Keep compact simulator armor rows language-aware as well.
    sim_path=root/'data/sim_armors.json'
    if sim_path.exists():
        sim=json.loads(sim_path.read_text(encoding='utf-8'))
        amap={a['id']:a for a in armors}
        for r in sim:
            a=amap.get(r.get('id'))
            if not a: continue
            if a.get('nameEn'): r['nameEn']=a['nameEn']
            else: r.pop('nameEn',None)
        sim_path.write_text(json.dumps(sim,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    report={
        'version':'0.7.5',
        'policy':{'primary':'Korean name field remains canonical display name','secondary':['Japanese nameJa','English nameEn'],'protected':['maxDefense','upgradeDefense']},
        'source':'user-supplied Athena Data.zip localization rows',
        'summary':{'armorCount':len(armors),'nameEnFilled':len(filled),'unresolved':len(unresolved),'primaryKoreanNameChanges':0,'protectedDefenseProgressionChanges':0,'methods':dict(methods)},
        'filled':filled,
        'unresolved':unresolved,
    }
    (root/'tools/armor_localization_v0.7.5.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))

if __name__=='__main__': main()
