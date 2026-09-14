#!/usr/bin/env python3
import argparse,csv,io,json,re,sqlite3,unicodedata,zipfile
from collections import Counter
from pathlib import Path

PART_FILES={'head':'head.txt','body':'body.txt','arms':'arms.txt','waist':'waist.txt','legs':'legs.txt'}
PART_MH={'Head':'head','Body':'body','Arms':'arms','Waist':'waist','Legs':'legs'}
G_A={'0':'','1':'남','2':'여'}; H_A={'0':'both','1':'blade','2':'gunner'}
G_M={'Both':'','Male':'남','Female':'여'}; H_M={'Both':'both','Blade':'blade','Gunner':'gunner'}
RES=['fire','water','thunder','ice','dragon']
SKILL_ALIASES={'気術':'体術','徹甲榴弾追加':'榴弾追加'}

def norm(s): return re.sub(r'\s+','',unicodedata.normalize('NFKC',s or ''))
def dump(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')

def load_athena(zpath):
    out=[]; ko_idx={}
    with zipfile.ZipFile(zpath) as z:
        for part,fn in PART_FILES.items():
            rows=list(csv.reader(io.StringIO(z.read('Data/'+fn).decode('utf-8-sig'))))[1:]
            ko=z.read('Data/Languages/╟╤▒╣╛ε/'+fn).decode('utf-8-sig').splitlines()
            for lineno,(r,kname) in enumerate(zip(rows,ko),2):
                skills={}; torso=False
                for j in range(14,24,2):
                    sn=norm(r[j]); sv=r[j+1].strip()
                    if not sn: continue
                    if sn=='胴系統倍加': torso=True; continue
                    if sv: skills[sn]=int(sv)
                rec={'part':part,'nameJa':r[0],'nameN':norm(r[0]),'nameKo':kname,'rare':int(r[3]),'slots':int(r[4]),'defense':int(r[7]),
                     'gender':G_A[r[1]],'hunterType':H_A[r[2]],'resistances':dict(zip(RES,map(int,r[9:14]))),'skillsJp':skills,'torsoUp':torso,'line':lineno}
                out.append(rec); ko_idx[(part,norm(kname))]=rec
    return out,ko_idx

def load_mh4u(dbpath):
    con=sqlite3.connect(dbpath); con.row_factory=sqlite3.Row
    out=[]
    q='''select i._id,i.name_jp,i.rarity,a.slot,a.defense,a.fire_res,a.water_res,a.thunder_res,a.ice_res,a.dragon_res,a.gender,a.hunter_type,a.num_slots from items i join armor a on i._id=a._id'''
    for r in con.execute(q):
        if r['slot'] not in PART_MH or not r['name_jp']: continue
        skills={}; torso=False
        for sr in con.execute('''select st.name_jp,ist.point_value from item_to_skill_tree ist join skill_trees st on st._id=ist.skill_tree_id where ist.item_id=?''',(r['_id'],)):
            sn=norm(sr['name_jp'])
            if sn=='胴系統倍加': torso=True
            else: skills[sn]=int(sr['point_value'])
        out.append({'id':r['_id'],'part':PART_MH[r['slot']],'nameJa':r['name_jp'],'nameN':norm(r['name_jp']),'rare':int(r['rarity']),'slots':int(r['num_slots'] or 0),'defense':int(r['defense']),
                    'gender':G_M.get(r['gender'],r['gender']),'hunterType':H_M.get(r['hunter_type'],r['hunter_type']),
                    'resistances':{'fire':r['fire_res'],'water':r['water_res'],'thunder':r['thunder_res'],'ice':r['ice_res'],'dragon':r['dragon_res']},'skillsJp':skills,'torsoUp':torso})
    con.close(); return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project',required=True); ap.add_argument('--athena',required=True); ap.add_argument('--mh4u-db',required=True); args=ap.parse_args()
    root=Path(args.project); arm_path=root/'data/armors.json'; skills_path=root/'data/skills.json'
    armors=json.loads(arm_path.read_text(encoding='utf-8')); skills=json.loads(skills_path.read_text(encoding='utf-8'))
    before={a['id']:{'maxDefense':a.get('maxDefense'),'upgradeDefense':a.get('upgradeDefense')} for a in armors}
    ath,ko_idx=load_athena(args.athena); mh=load_mh4u(args.mh4u_db)
    ath_idx={(x['part'],x['nameN']):x for x in ath}; mh_idx={(x['part'],x['nameN']):x for x in mh}
    common={k:(a,mh_idx[k]) for k,a in ath_idx.items() if k in mh_idx}

    skill_id={}; id_jp={}
    for s in skills:
        j=norm(s.get('nameJa')); j=norm(SKILL_ALIASES.get(j,j)); skill_id[j]=s['id']; id_jp[s['id']]=j
    def cur_sk(a): return {id_jp[sid]:int(v) for sid,v in (a.get('skills') or {}).items() if sid in id_jp}

    changes=[]; name_fill=name_fix=0
    # Korean Athena row name is only used as a row locator; MH4U must independently confirm the same JP name+part.
    for x in armors:
        ar=ko_idx.get((x['part'],norm(x['name'])))
        if not ar or (x['part'],ar['nameN']) not in mh_idx: continue
        old=x.get('nameJa','')
        if not norm(old):
            x['nameJa']=ar['nameJa']; name_fill+=1; changes.append({'id':x['id'],'name':x['name'],'field':'nameJa','old':old,'new':ar['nameJa'],'basis':'Athena Korean row + MH4U JP/part confirmation'})
        elif norm(old)!=ar['nameN']:
            x['nameJa']=ar['nameJa']; name_fix+=1; changes.append({'id':x['id'],'name':x['name'],'field':'nameJa','old':old,'new':ar['nameJa'],'basis':'Athena Korean row + MH4U JP/part confirmation'})

    field_counts=Counter(); mapped=0; external_disagreements=Counter()
    for x in armors:
        k=(x['part'],norm(x.get('nameJa')))
        if k not in common: continue
        mapped+=1; a,m=common[k]
        checks={'defense':(x.get('defense'),a['defense'],m['defense']),'slots':(x.get('slots'),a['slots'],m['slots']),'rare':(x.get('rare'),a['rare'],m['rare']),
                'gender':(x.get('gender',''),a['gender'],m['gender']),'hunterType':(x.get('hunterType'),a['hunterType'],m['hunterType']),'torsoUp':(bool(x.get('torsoUp')),a['torsoUp'],m['torsoUp'])}
        for rr in RES: checks['resistances.'+rr]=((x.get('resistances') or {}).get(rr),a['resistances'][rr],m['resistances'][rr])
        for f,(cur,av,mv) in checks.items():
            if av!=mv: external_disagreements[f]+=1; continue
            if cur==av: continue
            if f.startswith('resistances.'):
                rr=f.split('.',1)[1]; x.setdefault('resistances',{})[rr]=av
            else: x[f]=av
            field_counts[f]+=1; changes.append({'id':x['id'],'name':x['name'],'field':f,'old':cur,'new':av,'basis':'Athena == MH4U'})
        if a['skillsJp']!=m['skillsJp']:
            external_disagreements['skills']+=1
        elif cur_sk(x)!=a['skillsJp'] and all(j in skill_id for j in a['skillsJp']):
            old=dict(x.get('skills') or {})
            x['skills']={skill_id[j]:v for j,v in a['skillsJp'].items()}
            field_counts['skills']+=1; changes.append({'id':x['id'],'name':x['name'],'field':'skills','old':old,'new':x['skills'],'basis':'Athena == MH4U'})

    # Second pass: remaining JP names can be repaired only when the full non-max-defense signature
    # uniquely identifies the same JP armor in both independent external sources.
    def sig_cur(x):
        return (x['part'],x.get('hunterType'),x.get('gender',''),int(x.get('rare') or 0),int(x.get('defense') or 0),int(x.get('slots') or 0),bool(x.get('torsoUp')),
                tuple((x.get('resistances') or {}).get(r) for r in RES),tuple(sorted(cur_sk(x).items())))
    def sig_ext(x):
        return (x['part'],x['hunterType'],x['gender'],x['rare'],x['defense'],x['slots'],x['torsoUp'],tuple(x['resistances'][r] for r in RES),tuple(sorted(x['skillsJp'].items())))
    from collections import defaultdict
    ath_sig=defaultdict(list); mh_sig=defaultdict(list)
    for a in ath: ath_sig[sig_ext(a)].append(a)
    for m in mh: mh_sig[sig_ext(m)].append(m)
    sig_fill=sig_fix=0
    for x in armors:
        if (x['part'],norm(x.get('nameJa'))) in common: continue
        aa=ath_sig.get(sig_cur(x),[]); mm=mh_sig.get(sig_cur(x),[])
        if len(aa)!=1 or len(mm)!=1 or not aa[0]['nameN'] or aa[0]['nameN']!=mm[0]['nameN']: continue
        old=x.get('nameJa',''); new=aa[0]['nameJa']
        if norm(old)==aa[0]['nameN']: continue
        x['nameJa']=new
        if not norm(old): name_fill+=1; sig_fill+=1
        else: name_fix+=1; sig_fix+=1
        changes.append({'id':x['id'],'name':x['name'],'field':'nameJa','old':old,'new':new,'basis':'Unique full signature in Athena + MH4U'})

    # skill Japanese metadata corrections independently agreed by Athena/MH4U
    skill_meta=[]
    for s in skills:
        if s.get('name')=='체술' and norm(s.get('nameJa'))!='体術':
            old=s.get('nameJa'); s['nameJa']='体術'; skill_meta.append({'id':s['id'],'name':s['name'],'old':old,'new':'体術'})
        elif s.get('name')=='유탄추가' and norm(s.get('nameJa'))!='榴弾追加':
            old=s.get('nameJa'); s['nameJa']='榴弾追加'; skill_meta.append({'id':s['id'],'name':s['name'],'old':old,'new':'榴弾追加'})

    # Explicitly assert protected fields untouched.
    protected_changed=[]
    for x in armors:
        b=before[x['id']]
        if x.get('maxDefense')!=b['maxDefense'] or x.get('upgradeDefense')!=b['upgradeDefense']:
            protected_changed.append(x['id'])
    if protected_changed: raise SystemExit('Protected defense progression fields changed: '+str(protected_changed[:5]))

    dump(arm_path,armors); dump(skills_path,skills)
    # Rebuild derived set/sim data from corrected armor rows.
    import sys
    sys.path.insert(0,str(root/'tools'))
    import build_database as bd
    sets=bd.derive_armor_sets(armors)
    dump(root/'data/armor_sets.json',sets)
    dump(root/'data/sim_armors.json',bd.compact_rows(armors,bd.SIM_ARMOR_KEYS))
    dump(root/'data/sim_armor_sets.json',bd.compact_rows(sets,bd.SIM_ARMOR_SET_KEYS))

    mapped_final=sum((x['part'],norm(x.get('nameJa'))) in common for x in armors)
    unresolved=[{'id':x['id'],'name':x['name'],'nameJa':x.get('nameJa',''),'part':x['part']} for x in armors if (x['part'],norm(x.get('nameJa'))) not in common]
    report={'version':'0.7.5','policy':{'protected':['maxDefense','upgradeDefense'],'autoFix':'Only fields where Athena and MH4U independently agree; Korean display names/materials unchanged.'},
            'sources':{'athena':'user-supplied Athena Data.zip','mh4u':'MonsterHunter4UDatabase mh4u.db'},
            'summary':{'armorCount':len(armors),'externalCommonArmors':len(common),'mappedAfterNameRepair':mapped_final,'nameJaFilled':name_fill,'nameJaCorrected':name_fix,'signatureNameJaFilled':sig_fill,'signatureNameJaCorrected':sig_fix,'valueChangesByField':dict(field_counts),'skillMetadataCorrections':len(skill_meta),'protectedDefenseProgressionChanges':0,'remainingUnresolved':len(unresolved)},
            'skillMetadataCorrections':skill_meta,'externalDisagreementsSkipped':dict(external_disagreements),'changes':changes,'unresolved':unresolved}
    dump(root/'tools/armor_crosscheck_merge_v0.7.5.json',report)
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))

if __name__=='__main__': main()
