import json,re,datetime
from pathlib import Path
P=Path('.')
def load(name): return json.load(open(P/'data'/name,encoding='utf-8'))
items=load('items.json'); weapons=load('weapons.json'); armors=load('armors.json'); decos=load('decorations.json'); quests=load('quests.json'); rewards=load('monster_rewards.json'); comps=load('compositions.json'); exch=load('dragon_exchange.json'); sell=load('dragon_sell.json'); inc=load('dragon_increase.json')
by_name={x['name']:x for x in items if x.get('name')}
names=sorted(by_name,key=len,reverse=True)
refs={x['id']:{'name':x['name'],'acquire':[],'uses':[]} for x in items}
seen={x['id']:{'acquire':set(),'uses':set()} for x in items}
def add(name,kind, rec):
    it=by_name.get(name)
    if not it:return
    bucket='acquire' if kind=='acquire' else 'uses'
    sig=json.dumps(rec,ensure_ascii=False,sort_keys=True)
    if sig in seen[it['id']][bucket]: return
    seen[it['id']][bucket].add(sig); refs[it['id']][bucket].append(rec)
def material_matches(text):
    text=str(text or '')
    matches=[]
    occupied=[]
    for name in names:
        start=0
        while True:
            i=text.find(name,start)
            if i<0:break
            j=i+len(name)
            if not any(i<e and j>s for s,e in occupied):
                # Avoid matching a base item where the source clearly has a + suffix and a + item exists.
                if j<len(text) and text[j]=='+' and name+'+' in by_name:
                    start=j; continue
                occupied.append((i,j))
                tail=text[j:j+8]
                m=re.match(r'\s*[×xX*]\s*(\d+)',tail)
                matches.append((i,name,int(m.group(1)) if m else None))
            start=j
    return [(n,c) for _,n,c in sorted(matches)]
# Acquisitions: monster rewards
for r in rewards:
    add(r.get('item'),'acquire',{'type':'monster','monster':r.get('monster',''),'method':r.get('method',''),'rank':r.get('rank',''),'probability':r.get('probability',''),'count':r.get('count','')})
# Acquisitions + usage: combinations
for c in comps:
    add(c.get('result'),'acquire',{'type':'compose','no':c.get('no'),'materialA':c.get('materialA',''),'materialB':c.get('materialB',''),'successRate':c.get('successRate',''),'yield':c.get('yield','')})
    for field in ('materialA','materialB'):
        add(c.get(field),'uses',{'type':'compose','result':c.get('result',''),'no':c.get('no'),'successRate':c.get('successRate','')})
# Dragon exchange / sell / increase
for x in exch:
    add(x.get('result'),'acquire',{'type':'exchange','required':x.get('required',''),'unlock':x.get('unlock','')})
    add(x.get('required'),'uses',{'type':'exchange','result':x.get('result',''),'unlock':x.get('unlock','')})
for x in sell:
    add(x.get('name'),'acquire',{'type':'dragonSell','line':x.get('line',''),'points':x.get('points','')})
for x in inc:
    add(x.get('name'),'acquire',{'type':'dragonIncrease','market':x.get('market',''),'rare':x.get('rare'),'successRate':x.get('successRate',''),'points':x.get('points','')})
# Usage: equipment materials
for w in weapons:
    for craft in w.get('craft') or []:
        for name,count in material_matches(craft.get('materials','')):
            add(name,'uses',{'type':'weapon','id':w.get('id'),'name':w.get('name',''),'weaponType':w.get('weaponType',''),'method':craft.get('method',''),'count':count,'materials':craft.get('materials','')})
for a in armors:
    for name,count in material_matches(a.get('materials','')):
        add(name,'uses',{'type':'armor','id':a.get('id'),'name':a.get('name',''),'part':a.get('part',''),'hunterType':a.get('hunterType',''),'count':count,'materials':a.get('materials','')})
for d in decos:
    for name,count in material_matches(d.get('materials','')):
        add(name,'uses',{'type':'decoration','id':d.get('id'),'name':d.get('name',''),'slots':d.get('slots'),'count':count,'materials':d.get('materials','')})
# Event/episode quest notes: only parse the declared 주요 보수 segment, never the old 사용처 text.
for q in quests:
    note=str(q.get('note') or '')
    m=re.search(r'주요\s*보수\s*:\s*([^/]+)',note)
    if not m: continue
    segment=m.group(1).strip()
    found=material_matches(segment)
    if not found and segment in by_name: found=[(segment,None)]
    for name,_ in found:
        add(name,'acquire',{'type':'quest','id':q.get('id'),'name':q.get('name',''),'questType':q.get('questType',''),'level':q.get('level',''),'location':q.get('location',''),'objective':q.get('objective','')})
# Keep only useful entries, sort stable for UI.
for rid,v in refs.items():
    v['acquire'].sort(key=lambda x:(x.get('type',''),x.get('monster',''),x.get('name',''),str(x.get('no',''))))
    v['uses'].sort(key=lambda x:(x.get('type',''),x.get('weaponType',''),x.get('name',''),x.get('result','')))
useful={k:v for k,v in refs.items() if v['acquire'] or v['uses']}
out={'version':'0.7.7-chat4-itemxref1','generated':'2026-09-15','itemCount':len(items),'indexedCount':len(useful),'items':useful}
json.dump(out,open(P/'data/item_references.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
# Runtime performance: keep the monolithic audit/source file, but serve one small reference file per item.
shard_dir=P/'data'/'item_refs'; shard_dir.mkdir(exist_ok=True)
for old_file in shard_dir.glob('*.json'): old_file.unlink()
index={'version':'0.7.7-chat4-itemxref4-perf','generated':'2026-09-15','items':{}}
for iid,v in useful.items():
    payload={'id':iid,'acquire':v['acquire'],'uses':v['uses']}
    json.dump(payload,open(shard_dir/f'{iid}.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    index['items'][iid]={'acquire':len(v['acquire']),'uses':len(v['uses'])}
json.dump(index,open(P/'data/item_reference_index.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(f"item references: {len(useful)}/{len(items)} items indexed")
print(f"acquire references: {sum(len(v['acquire']) for v in useful.values())}")
print(f"usage references: {sum(len(v['uses']) for v in useful.values())}")
