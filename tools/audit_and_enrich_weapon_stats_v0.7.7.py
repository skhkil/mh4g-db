#!/usr/bin/env python3
import json, sqlite3, re, difflib, argparse
from pathlib import Path
from collections import Counter
from scipy.optimize import linear_sum_assignment
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
TYPE={'대검':'Great Sword','태도':'Long Sword','한손검':'Sword and Shield','쌍검':'Dual Blades','해머':'Hammer','수렵피리':'Hunting Horn','랜스':'Lance','건랜스':'Gunlance','슬래시액스':'Switch Axe','차지액스':'Charge Blade','조충곤':'Insect Glaive','라이트보우건':'Light Bowgun','헤비보우건':'Heavy Bowgun','활':'Bow'}
KO={'Fire':'불','Water':'물','Thunder':'번개','Ice':'얼음','Dragon':'용','Poison':'독','Paralysis':'마비','Sleep':'수면','Blastblight':'폭파','Blast':'폭파'}
def norm(s): return re.sub(r'[\s・·=＝「」『』【】\[\]()（）+＋]','',(s or '').lower().replace('�',''))
def sim(a,b): return difflib.SequenceMatcher(None,norm(a),norm(b)).ratio() if a and b else 0
def fmt_prop(t,v): return f"{KO.get(t,t)} {int(v)}" if t and v not in (None,'') else ''
def make_display(r):
    bits=[]
    if r.get('element'): bits.append(fmt_prop(r['element'],r.get('element_attack')))
    if r.get('element_2'): bits.append(fmt_prop(r['element_2'],r.get('element_2_attack')))
    if r.get('awaken'): bits.append(f"각성 {fmt_prop(r['awaken'],r.get('awaken_attack'))}")
    if int(r.get('defense') or 0): bits.append(f"방어+{int(r['defense'])}")
    return ' · '.join(x for x in bits if x)
def source_only_fields(o):
    s=str(o.get('element') or '')
    def find(names):
        for n in names:
            m=re.search(re.escape(n)+r'\s*([0-9]+)',s)
            if m:return n,int(m.group(1))
    hit=find(['불','화','물','번개','뇌','얼음','빙','용','독','마비','수면','폭파'])
    d=re.search(r'방어\s*[+＋]\s*([0-9 ]+)',s)
    return {'elementPrimary': {'type':hit[0],'value':hit[1]} if hit and '(' not in s else None,'elementSecondary':None,'awakenElement': {'type':hit[0],'value':hit[1]} if hit and '(' in s else None,'defenseBonus':int((d.group(1) or '0').replace(' ','')) if d else 0,'affinityText':str(o.get('affinity',0))}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--db',required=True); ap.add_argument('--write',action='store_true'); a=ap.parse_args()
    wp=ROOT/'data/weapons.json'; sp=ROOT/'data/sim_weapons.json'
    ours=json.loads(wp.read_text(encoding='utf-8'))
    con=sqlite3.connect(a.db);con.row_factory=sqlite3.Row
    refs=[dict(r) for r in con.execute('select i._id,i.name,i.name_jp,i.rarity,w.* from weapons w join items i on i._id=w._id')]
    maps=[]; unmatched=[]
    for kot,ent in TYPE.items():
        O=[o for o in ours if o['weaponType']==kot]; R=[r for r in refs if r['wtype']==ent]
        cost=np.zeros((len(O),len(R))); scores=np.zeros_like(cost)
        for i,o in enumerate(O):
            for j,r in enumerate(R):
                jp=sim(o.get('nameJa'),r.get('name_jp')); en=sim(o.get('nameEn'),r.get('name')) if o.get('nameEn') else 0
                ao,ar=int(o.get('attack') or 0),int(r.get('attack') or 0); atk=1 if ao==ar else max(0,1-abs(ao-ar)/max(100,ar)); sl=1 if int(o.get('slots') or 0)==int(r.get('num_slots') or 0) else 0
                sc=2.2*jp+.9*en+.55*atk+.12*sl; scores[i,j]=sc; cost[i,j]=-sc
        ri,cj=linear_sum_assignment(cost); mi=set(ri)
        maps += [(O[i],R[j],float(scores[i,j])) for i,j in zip(ri,cj)]
        unmatched += [O[i] for i in range(len(O)) if i not in mi]
    counts=Counter(); audit=[]; byid={o['id']:(o,r,s) for o,r,s in maps}
    for o in ours:
        old={k:o.get(k) for k in ['attack','element','affinity','slots']}
        if o['id'] not in byid:
            f=source_only_fields(o);o.update(f);o['statReference']='source-only';audit.append({'id':o['id'],'name':o['name'],'match':'source-only'});continue
        _,r,score=byid[o['id']]
        if int(o.get('attack') or 0)!=int(r['attack'] or 0): counts['attack']+=1;o['sourceAttack']=o.get('attack');o['attack']=int(r['attack'] or 0)
        if int(o.get('slots') or 0)!=int(r['num_slots'] or 0): counts['slots']+=1;o['sourceSlots']=o.get('slots');o['slots']=int(r['num_slots'] or 0)
        afftxt=str(r.get('affinity') or '0')
        if afftxt!=str(o.get('affinityText',o.get('affinity',0))): counts['affinity']+=1;o['sourceAffinity']=o.get('affinity')
        o['affinityText']=afftxt
        try:o['affinity']=int(afftxt)
        except:
            nums=[int(x) for x in re.findall(r'-?\d+',afftxt)];o['affinity']=max(nums) if nums else 0
        ep={'type':KO.get(r['element'],r['element']),'value':int(r['element_attack'] or 0)} if r.get('element') else None
        es={'type':KO.get(r['element_2'],r['element_2']),'value':int(r['element_2_attack'] or 0)} if r.get('element_2') else None
        aw={'type':KO.get(r['awaken'],r['awaken']),'value':int(r['awaken_attack'] or 0)} if r.get('awaken') else None
        defense=int(r['defense'] or 0); disp=make_display(r)
        if str(o.get('element') or '')!=disp: counts['propertyDisplay']+=1;o['sourceElement']=o.get('element','')
        o.update({'element':disp,'elementPrimary':ep,'elementSecondary':es,'awakenElement':aw,'defenseBonus':defense,'rarityRef':int(r['rarity'] or 0),'statReference':'MH4U DB','mh4uWeaponId':int(r['_id']),'mh4uName':r['name'],'mh4uNameJa':r['name_jp']})
        # canonical weapon-specific reference stats, kept separate from localized source fields
        for src,dst in [('horn_notes','refHornNotes'),('shelling_type','refShelling'),('phial','refPhial'),('charges','refCharges'),('coatings','refCoatings'),('recoil','refRecoil'),('reload_speed','refReloadSpeed'),('rapid_fire','refRapidFire'),('deviation','refDeviation'),('ammo','refAmmo'),('special_ammo','refSpecialAmmo')]:
            if r.get(src) not in (None,''): o[dst]=r[src]
        audit.append({'id':o['id'],'name':o['name'],'weaponType':o['weaponType'],'score':round(score,4),'mh4uId':r['_id'],'mh4uName':r['name'],'changes':{k:[old.get(k),o.get(k)] for k in old if old.get(k)!=o.get(k)},'properties':{'primary':ep,'secondary':es,'awaken':aw,'defenseBonus':defense,'affinityText':afftxt}})
    report={'totalProjectWeapons':len(ours),'mh4uMatched':len(maps),'sourceOnly':len(unmatched),'sourceOnlyWeapons':[{'id':x['id'],'name':x['name'],'weaponType':x['weaponType']} for x in unmatched],'changedCounts':dict(counts),'note':'Athena Data.zip에는 무기 스탯 테이블이 없어 무기 수치 교차검증에는 사용하지 않음.'}
    if a.write:
        wp.write_text(json.dumps(ours,ensure_ascii=False,indent=2),encoding='utf-8')
        simkeys=['id','name','nameJa','nameEn','weaponType','attack','element','elementPrimary','elementSecondary','awakenElement','defenseBonus','affinity','affinityText','slots','rank','tree','statReference','sharpness','phial','shelling','notes','melody','melodyEffects','kinsect','arcShot','specialFire','chargeLevels','coatings','reloadRecoilDrift']
        sp.write_text(json.dumps([{k:o.get(k) for k in simkeys} for o in ours],ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        (ROOT/'data/weapon_stat_audit.json').write_text(json.dumps({'summary':report,'items':audit},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
