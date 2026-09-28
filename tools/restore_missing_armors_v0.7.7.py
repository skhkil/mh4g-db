#!/usr/bin/env python3
import csv, hashlib, io, json, re, sqlite3, unicodedata, zipfile
from collections import Counter, defaultdict
from pathlib import Path

PART_FILES={'head':'head.txt','body':'body.txt','arms':'arms.txt','waist':'waist.txt','legs':'legs.txt'}
PART_MH={'Head':'head','Body':'body','Arms':'arms','Waist':'waist','Legs':'legs'}
PART_ORDER={'head':0,'body':1,'arms':2,'waist':3,'legs':4}
H_A={'0':'both','1':'blade','2':'gunner'}
G_A={'0':'','1':'남','2':'여'}
SKILL_ALIASES={'気術':'体術','徹甲榴弾追加':'榴弾追加'}
RES=['fire','water','thunder','ice','dragon']

def norm(s): return re.sub(r'\s+','',unicodedata.normalize('NFKC',s or ''))
def stable_id(prefix,*parts):
    key='|'.join(map(str,parts))
    return f"{prefix}_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"
def dump(p,obj,compact=False):
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=None if compact else 2,separators=(',',':') if compact else None)+("" if compact else "\n"),encoding='utf-8')

def load_components(z):
    jp=z.read('Data/components.txt').decode('utf-8-sig').splitlines()
    ko=z.read('Data/Languages/╟╤▒╣╛ε/components.txt').decode('utf-8-sig').splitlines()
    out={norm(a.split(',')[0]):b.strip() for a,b in zip(jp,ko) if a.strip() and b.strip()}
    out[norm('※店売り')]='※상점판매'
    return out

def load_athena(zpath):
    out=[]
    with zipfile.ZipFile(zpath) as z:
        comp=load_components(z)
        for part,fn in PART_FILES.items():
            rows=list(csv.reader(io.StringIO(z.read('Data/'+fn).decode('utf-8-sig'))))[1:]
            kos=z.read('Data/Languages/╟╤▒╣╛ε/'+fn).decode('utf-8-sig').splitlines()
            for line,(r,ko) in enumerate(zip(rows,kos),2):
                skills={}; torso=False
                for j in range(14,24,2):
                    sn=norm(r[j]); sv=r[j+1].strip()
                    if not sn: continue
                    if sn=='胴系統倍加': torso=True; continue
                    if sv: skills[sn]=int(sv)
                mats=[]
                for j in range(24,32,2):
                    mj=r[j].strip(); qty=r[j+1].strip()
                    if not mj: continue
                    mk=comp.get(norm(mj),mj)
                    mats.append(f"{mk}*{qty or '1'}")
                out.append({
                    'part':part,'nameJa':r[0].strip(),'nameN':norm(r[0]),'nameKo':ko.strip(),
                    'rare':int(r[3]),'slots':int(r[4]),'gatherStar':int(r[5]),'villageStar':int(r[6]),
                    'defense':int(r[7]),'maxDefense':int(r[8]),
                    'gender':G_A[r[1]],'hunterType':H_A[r[2]],
                    'resistances':dict(zip(RES,map(int,r[9:14]))),'skillsJp':skills,'torsoUp':torso,
                    'materials':' · '.join(mats),'line':line
                })
    return out

def load_mh4u(dbpath):
    con=sqlite3.connect(dbpath); con.row_factory=sqlite3.Row
    rows=[]
    q='''select i._id,i.name,i.name_jp,i.rarity,a.slot,a.gender,a.hunter_type,a.num_slots from items i join armor a on i._id=a._id where i.name_jp is not null order by i._id'''
    for r in con.execute(q):
        p=PART_MH.get(r['slot'])
        if not p: continue
        rows.append({'id':int(r['_id']),'part':p,'nameEn':r['name'],'nameJa':r['name_jp'],'nameN':norm(r['name_jp']),
                     'rare':int(r['rarity']),'hunterType':{'Blade':'blade','Gunner':'gunner','Both':'both'}.get(r['hunter_type'],r['hunter_type'].lower()),
                     'gender':{'Male':'남','Female':'여','Both':''}.get(r['gender'],'')})
    con.close()
    # Detect contiguous five-piece blocks in MH4U order. This is only for set grouping/source identity.
    byid={r['id']:r for r in rows}; group={}
    ids=sorted(byid)
    slots=['head','body','arms','waist','legs']
    for i in ids:
        seq=[byid.get(i+j) for j in range(5)]
        if all(seq) and [x['part'] for x in seq]==slots:
            # Avoid starting in the middle of another block; head guarantees start.
            key=f"mh4u-set-{i}"
            for x in seq: group[x['id']]=key
    return rows,group

def set_name(names):
    if not names: return ''
    pref=names[0]
    for n in names[1:]:
        i=0
        while i<min(len(pref),len(n)) and pref[i]==n[i]: i+=1
        pref=pref[:i]
        if not pref: break
    return pref.rstrip('【[ ·-_') or names[0]

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--project',required=True); ap.add_argument('--athena',required=True); ap.add_argument('--mh4u-db',required=True)
    args=ap.parse_args(); root=Path(args.project)
    armors=json.loads((root/'data/armors.json').read_text(encoding='utf-8'))
    skills=json.loads((root/'data/skills.json').read_text(encoding='utf-8'))
    current={(a['part'],norm(a.get('nameJa'))):a for a in armors if a.get('nameJa')}
    current_ko={(a['part'],norm(a.get('name'))):a for a in armors}
    skill_id={norm(s.get('nameJa')):s['id'] for s in skills if s.get('nameJa')}
    for a,b in SKILL_ALIASES.items():
        if norm(b) in skill_id: skill_id[norm(a)]=skill_id[norm(b)]
    ath=load_athena(args.athena); mh,mh_group=load_mh4u(args.mh4u_db)
    mh_idx={(x['part'],x['nameN']):x for x in mh}

    missing=[]; unresolved=[]
    for a in ath:
        k=(a['part'],a['nameN']); m=mh_idx.get(k)
        if not m or k in current: continue
        if (a['part'],norm(a['nameKo'])) in current_ko:
            unresolved.append({'reason':'Korean-name collision','athena':a,'mh4u':m}); continue
        smap={}; bad=[]
        for jp,v in a['skillsJp'].items():
            sid=skill_id.get(norm(SKILL_ALIASES.get(jp,jp)))
            if not sid: bad.append(jp)
            else: smap[sid]=v
        if bad:
            unresolved.append({'reason':'Unmapped skills','nameJa':a['nameJa'],'skills':bad}); continue
        rank='g' if a['rare']>=8 else ('high' if a['rare']>=4 else 'low')
        source_group=mh_group.get(m['id'],f"mh4u-single-{m['id']}")
        rec={
            'id':stable_id('armor','athena_restore',a['part'],a['nameJa'],a['hunterType'],a['gender']),
            'name':a['nameKo'],'nameJa':a['nameJa'],'nameEn':m['nameEn'],'part':a['part'],'hunterType':a['hunterType'],
            'rank':rank,'rare':a['rare'],'gender':a['gender'],'price':'','defense':a['defense'],'upgradeDefense':[],
            'maxDefense':a['maxDefense'],'slots':a['slots'],'torsoUp':a['torsoUp'],'resistances':a['resistances'],
            'materials':a['materials'],'source':f"athena://restored/{source_group}",'sourceRow':PART_ORDER[a['part']]+1,
            'skills':smap,'rankBasis':'rare8-10' if rank=='g' else ('rare4-7' if rank=='high' else 'rare1-3'),
            'restoredFrom':{'athenaLine':a['line'],'mh4uItemId':m['id']}
        }
        missing.append(rec)

    if unresolved:
        raise SystemExit(f"Unsafe unresolved candidates: {len(unresolved)}; first={unresolved[0]}")
    if not missing: raise SystemExit('No missing armors found.')
    ids={a['id'] for a in armors}
    if any(x['id'] in ids for x in missing): raise SystemExit('ID collision')
    before=len(armors); armors.extend(missing)
    # deterministic display order: source rows first, then restored by rank/name/part is okay because UI sorts independently
    dump(root/'data/armors.json',armors)

    import sys
    sys.path.insert(0,str(root/'tools'))
    import build_database as bd
    sets=bd.derive_armor_sets(armors)
    # Supplement restored five-piece groups (derive_armor_sets cannot always combine a Both head with Blade/Gunner body pieces).
    existing_piece_sets={tuple(p['id'] for p in s.get('pieces',[])) for s in sets}
    restored_groups=defaultdict(list)
    for x in missing: restored_groups[x['source']].append(x)
    added_sets=[]
    for src,rows in restored_groups.items():
        if len(rows)!=5 or {r['part'] for r in rows}!=set(PART_ORDER): continue
        rows=sorted(rows,key=lambda r:PART_ORDER[r['part']])
        piece_ids=tuple(r['id'] for r in rows)
        if piece_ids in existing_piece_sets: continue
        nonboth={r['hunterType'] for r in rows if r['hunterType']!='both'}
        hunter=next(iter(nonboth)) if len(nonboth)==1 else ('both' if not nonboth else 'both')
        torso_count=sum(1 for r in rows if r.get('torsoUp'))
        sk={}
        for r in rows:
            mult=1+torso_count if r['part']=='body' else 1
            for sid,v in r.get('skills',{}).items(): sk[sid]=sk.get(sid,0)+v*mult
        names=[r['name'] for r in rows]
        s={
            'id':stable_id('armor_set',hunter,rows[0]['rank'],names[0]),'name':set_name(names),'hunterType':hunter,
            'rank':rows[0]['rank'],'rare':rows[0]['rare'],'pieces':[{'id':r['id'],'part':r['part'],'name':r['name']} for r in rows],
            'defense':sum(r['defense'] for r in rows),'maxDefense':sum(r['maxDefense'] for r in rows),'slots':sum(r['slots'] for r in rows),
            'skills':sk,'resistances':{k:sum(r['resistances'][k] for r in rows) for k in RES},'restored':True
        }
        sets.append(s); added_sets.append(s)
    dump(root/'data/armor_sets.json',sets)
    dump(root/'data/sim_armors.json',bd.compact_rows(armors,bd.SIM_ARMOR_KEYS),compact=True)
    dump(root/'data/sim_armor_sets.json',bd.compact_rows(sets,bd.SIM_ARMOR_SET_KEYS),compact=True)

    # Validation
    final_keys=[(a['part'],norm(a.get('nameJa'))) for a in armors if a.get('nameJa')]
    if len(final_keys)!=len(set(final_keys)):
        dup=[k for k,c in Counter(final_keys).items() if c>1][:10]; raise SystemExit('Duplicate part/nameJa after restore: '+repr(dup))
    ext_common={(a['part'],a['nameN']) for a in ath if (a['part'],a['nameN']) in mh_idx}
    final_set=set(final_keys)
    remaining=sorted(ext_common-final_set)
    gx=[x for x in missing if x['nameJa'].startswith('GX')]
    report={
        'version':'0.7.7','step':'missing armor restoration only','policy':{
            'target':'MH4G/Japanese data behavior','statsAndMaterials':'Athena Data.zip','existenceAndEnglishName':'MH4U DB cross-check',
            'questMonsterEventLinking':'deferred to next step'
        },
        'summary':{'beforeArmorCount':before,'restoredArmorCount':len(missing),'afterArmorCount':len(armors),'restoredGXCount':len(gx),
                   'restoredArmorSets':len(added_sets),'externalCommonRemainingMissing':len(remaining)},
        'byRank':dict(Counter(x['rank'] for x in missing)),'byPart':dict(Counter(x['part'] for x in missing)),
        'restoredGX':[{'name':x['name'],'nameJa':x['nameJa'],'part':x['part'],'hunterType':x['hunterType'],'slots':x['slots']} for x in gx],
        'restored':[{'id':x['id'],'name':x['name'],'nameJa':x['nameJa'],'nameEn':x.get('nameEn'),'part':x['part'],'hunterType':x['hunterType'],'rank':x['rank'],'rare':x['rare'],'defense':x['defense'],'maxDefense':x['maxDefense'],'slots':x['slots'],'materials':x['materials']} for x in missing],
        'restoredSets':[{'name':s['name'],'hunterType':s['hunterType'],'rank':s['rank'],'pieces':[p['name'] for p in s['pieces']]} for s in added_sets],
        'remainingExternalCommonMissing':[{'part':p,'nameJa':n} for p,n in remaining]
    }
    dump(root/'tools/missing_armor_restore_audit_v0.7.7.json',report)
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))

if __name__=='__main__': main()
