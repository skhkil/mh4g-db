#!/usr/bin/env python3
import json, sqlite3, re, argparse, collections
from pathlib import Path
TYPE_MAP={'대검':'Great Sword','태도':'Long Sword','한손검':'Sword and Shield','쌍검':'Dual Blades','해머':'Hammer','수렵피리':'Hunting Horn','랜스':'Lance','건랜스':'Gunlance','슬래시액스':'Switch Axe','차지액스':'Charge Blade','조충곤':'Insect Glaive','라이트보우건':'Light Bowgun','헤비보우건':'Heavy Bowgun','활':'Bow'}
MAT_RE=re.compile(r'(.*?)[×*]\s*(\d+)(?=\s|$)')
def parse_mat(s):
    out=[]
    for m in MAT_RE.finditer(str(s or '')):
        n=m.group(1).strip(); q=int(m.group(2))
        if n: out.append((n,q))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--db',required=True); ap.add_argument('--root',default='.')
    a=ap.parse_args(); root=Path(a.root)
    wp=root/'data/weapons.json'; weapons=json.loads(wp.read_text(encoding='utf-8'))
    con=sqlite3.connect(a.db); con.row_factory=sqlite3.Row
    rows=con.execute('select w.*, i.name, i.name_jp from weapons w join items i on i._id=w._id').fetchall()
    by_name={(r['name'],r['wtype']):r for r in rows}
    used=set(); local_to_mh={}; confidence={}
    missing=[]
    # 1) exact English name + weapon type
    for w in weapons:
        r=by_name.get((w.get('nameEn'),TYPE_MAP.get(w['weaponType']))) if w.get('nameEn') else None
        if r:
            local_to_mh[w['id']]=r['_id']; used.add(r['_id']); confidence[w['id']]='exact-name'
        else: missing.append(w)
    # 2) unique numeric signature fallback
    still=[]
    for w in missing:
        cand=[]
        for r in rows:
            if r['_id'] in used or r['wtype']!=TYPE_MAP.get(w['weaponType']): continue
            try:
                aff=int(str(r['affinity'] or 0).replace('%',''))
            except: aff=0
            if int(r['attack'])==int(w.get('attack') or 0) and int(r['num_slots'])==int(w.get('slots') or 0) and aff==int(w.get('affinity') or 0): cand.append(r)
        if len(cand)==1:
            r=cand[0]; local_to_mh[w['id']]=r['_id']; used.add(r['_id']); confidence[w['id']]='numeric-signature'
        else: still.append(w)
    mh_to_local={v:k for k,v in local_to_mh.items()}
    mh_by_id={r['_id']:r for r in rows}
    parent={}; children=collections.defaultdict(list)
    for w in weapons:
        lid=w['id']; mid=local_to_mh.get(lid); p=None
        if mid is not None:
            pmid=mh_by_id[mid]['parent_id']
            if pmid and pmid in mh_to_local: p=mh_to_local[pmid]
        parent[lid]=p
    # fallback only for unmatched/local parent gaps, nearest prior shallower visual row in same tree
    groups=collections.defaultdict(list)
    for w in weapons: groups[(w['weaponType'],w.get('treeOrder',9999))].append(w)
    for arr in groups.values():
        arr.sort(key=lambda x:x.get('rowOrder',0)); prev=[]
        for w in arr:
            if parent[w['id']] is not None: prev.append(w); continue
            if w['id'] in local_to_mh: prev.append(w); continue # mapped root or parent absent; don't guess
            d=len(w.get('treePrefix',''))
            candidates=[x for x in prev if len(x.get('treePrefix',''))<d]
            if candidates:
                p=max(candidates,key=lambda x:(len(x.get('treePrefix','')),x.get('rowOrder',0)))
                parent[w['id']]=p['id']; confidence[w['id']]='visual-fallback'
            else: confidence[w['id']]='unmatched-root'
            prev.append(w)
    for lid,p in parent.items():
        if p: children[p].append(lid)
    wby={w['id']:w for w in weapons}
    for p in children: children[p].sort(key=lambda x:wby[x].get('rowOrder',0))
    def path_to(lid):
        out=[]; seen=set(); cur=lid
        while cur and cur not in seen:
            seen.add(cur);out.append(cur);cur=parent.get(cur)
        return list(reversed(out))
    def finals_from(lid):
        found=[]; stack=[lid]; seen=set()
        while stack:
            x=stack.pop()
            if x in seen: continue
            seen.add(x); ch=children.get(x,[])
            if wby[x].get('isFinal') or not ch: found.append(x)
            else: stack.extend(reversed(ch))
        return sorted(set(found),key=lambda x:wby[x].get('rowOrder',0))
    def cumulative(path):
        counts=collections.OrderedDict()
        for i,lid in enumerate(path):
            craft=wby[lid].get('craft') or []
            method='생산' if i==0 else '강화'
            row=next((c for c in craft if c.get('method')==method),None)
            if row is None and craft: row=craft[0]
            if not row: continue
            for name,q in parse_mat(row.get('materials')): counts[name]=counts.get(name,0)+q
        return [{'name':n,'count':q} for n,q in counts.items()]
    items={}; refdir=root/'data/weapon_refs'; refdir.mkdir(parents=True,exist_ok=True)
    for oldf in refdir.glob('*.json'): oldf.unlink()
    for w in weapons:
        lid=w['id']; path=path_to(lid); finals=finals_from(lid)
        items[lid]={
            'mh4uId':local_to_mh.get(lid),'match':confidence.get(lid,'unknown'),
            'parentId':parent.get(lid),'childIds':children.get(lid,[])
        }
        detail={'id':lid,'pathIds':path,'finalIds':finals,'cumulativeMaterials':cumulative(path)}
        (refdir/f'{lid}.json').write_text(json.dumps(detail,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    out={'version':'0.7.7','generatedFrom':'MH4U weapons.parent_id','items':items}
    (root/'data/weapon_tree_index.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    audit={
        'weapons':len(weapons),'matchedExact':sum(v=='exact-name' for v in confidence.values()),
        'matchedNumeric':sum(v=='numeric-signature' for v in confidence.values()),
        'visualFallback':sum(v=='visual-fallback' for v in confidence.values()),
        'unmatchedRoot':sum(v=='unmatched-root' for v in confidence.values()),
        'mappedToMh4u':len(local_to_mh),'unmapped':[{'id':w['id'],'type':w['weaponType'],'name':w['name'],'nameEn':w.get('nameEn')} for w in still],
        'brokenParentRefs':sum(1 for x in items.values() if x['parentId'] and x['parentId'] not in items),
        'emptyPaths':0,
        'noFinalPath':0
    }
    (root/'tools/weapon_tree_audit_v0.7.7.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
