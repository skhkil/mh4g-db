#!/usr/bin/env python3
import csv, io, json, re, sqlite3, zipfile, os, shutil
from pathlib import Path
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
ATHENA=Path(os.environ.get('MH4G_ATHENA_DATA_ZIP','/mnt/data/Data.zip'))
MH4U=Path(os.environ.get('MH4U_DB','/mnt/data/mh4u.db'))

# Japanese MH4G-exclusive/event reward tickets that MH4U quest_rewards does not reliably encode.
# Project quest IDs are used when that quest is already present in the project DB.
SPECIAL_QUESTS={
    '強欲チケット':[('event-g-076','event','GX그리드 제작 핵심 티켓')],
    '嵐龍チケット':[('event-g-071','event','GX황천/GX창천 제작 핵심 티켓')],
    '紅龍チケット':[('event-g-078','event','GX밀라발Z 제작 핵심 티켓')],
    '大長老チケットＳ':[
        ('event-g-071','event','확정 입수 가능한 G★3 이벤트'),
        ('event-g-076','event','G★3 이벤트 보수'),
        ('event-g-078','event','G★3 이벤트 보수'),
    ],
    '刃牙道の証':[('event-g-077','event','격앙 라잔 이벤트 보수')],
}
# Known MH4G event quests not currently present in project quest DB. Keep the exact Japanese title so users know what to run.
SPECIAL_TEXT_QUESTS={
    '反逆Ｊチケット':[{'type':'quest','questType':'event','name':'JUMP・작열열투!','nameJa':'JUMP・灼熱燃闘！','level':'G★3','objective':'테오·테스카토르 토벌 또는 격퇴','location':'구 사막(낮)','note':'반역J티켓 기본 보수'}],
    '刃牙道の証':[{'type':'quest','questType':'event','name':'한마 바키・송곳니 드러낸 금사자','nameJa':'範馬刃牙・牙剥く金獅子','level':'G★3','objective':'라잔 1마리 수렵','location':'격투장','note':'刃牙道의 증표 보수'}],
}

PART_FILES=['Data/head.txt','Data/body.txt','Data/arms.txt','Data/waist.txt','Data/legs.txt']


def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save_json(p,obj): Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def norm(s): return re.sub(r'\s+','',str(s or '')).replace('Ｇ','G').replace('Ｓ','S').replace('Ｊ','J').lower()

def parse_korean_materials(text):
    """Parse the project's armor material string without treating literal '+' in item names as a separator.
    Existing armor rows are mostly space-separated (e.g. A*2 B*3), while restored rows may use middots.
    """
    text=str(text or '').strip()
    if not text: return []
    out=[]
    for m in re.finditer(r'(.+?)[×*]\s*(\d+)', text):
        name=re.sub(r'^[·,、\s]+','',m.group(1)).strip()
        if name: out.append((name,int(m.group(2))))
    if out: return out
    return [(text,1)]

def rank_ko(rank):
    return {'LR':'하위','HR':'상위','G':'G급','Low':'하위','High':'상위'}.get(str(rank),str(rank or ''))

def main():
    armors=load_json(DATA/'armors.json')
    items=load_json(DATA/'items.json')
    quests=load_json(DATA/'quests.json')
    qindex=load_json(DATA/'quest_reference_index.json')
    targets=armors

    # Athena armor -> exact Japanese material names/order.
    athena_rows={}
    with zipfile.ZipFile(ATHENA) as z:
        for fn in PART_FILES:
            text=z.read(fn).decode('utf-8-sig')
            for r in csv.reader(io.StringIO(text)):
                if not r or r[0].startswith('#'): continue
                mats=[]
                for i in (24,26,28,30):
                    if i<len(r) and r[i]: mats.append((r[i],int(r[i+1] or 1)))
                athena_rows[norm(r[0])]=mats

    con=sqlite3.connect(MH4U); con.row_factory=sqlite3.Row
    mh_items_by_jp={r['name_jp']:dict(r) for r in con.execute('select * from items where name_jp is not null and name_jp<>""')}
    mh_monsters={r['_id']:dict(r) for r in con.execute('select * from monsters')}
    # project monster mapping by EN name
    monsters=load_json(DATA/'monster_summary.json')
    dragon_exchange=load_json(DATA/'dragon_exchange.json')
    dragon_by_result={norm(x.get('result')):x for x in dragon_exchange if x.get('result')}
    dragon_by_jp={norm(x.get('resultJa')):x for x in dragon_exchange if x.get('resultJa')}
    proj_mon_by_en={norm(m.get('nameEn')):m for m in monsters if m.get('nameEn')}
    small_monster_ko={
        'Zamite':'스쿠아길','Delex':'델쿠스','Konchu':'쿤추','Melynx':'메라루','Felyne':'아이루'
    }
    def localized_monster(mon_name):
        pm=proj_mon_by_en.get(norm(mon_name))
        if pm:return pm.get('name') or mon_name, pm.get('name') or ''
        if str(mon_name).startswith('Apex '):
            base=str(mon_name)[5:]
            bpm=proj_mon_by_en.get(norm(base))
            if bpm:
                return f"극한상태 {bpm.get('name') or base}", bpm.get('name') or ''
        if mon_name in small_monster_ko:return small_monster_ko[mon_name], ''
        return mon_name, ''
    # project quest mapping by EN name / exact JP title
    proj_q_by_en={norm(q.get('nameEn')):q for q in quests if q.get('nameEn')}
    proj_q_by_jp={q.get('nameJa'):q for q in quests if q.get('nameJa')}
    proj_q_by_id={q['id']:q for q in quests}

    items_by_mh={int(x['mh4uId']):x for x in items if x.get('mh4uId') is not None}
    items_by_name={x['name']:x for x in items}
    for x in items:
        for alias in x.get('aliases',[]) or []:
            items_by_name.setdefault(alias,x)
    # ensure aliases list on demand; add missing restored-material items from MH4U when needed.
    added_items=[]; alias_adds=[]

    def project_item_for(korean_name,jp_name):
        # Prefer the existing Korean project item. Most legacy armor rows already reference a valid item name.
        p=items_by_name.get(korean_name)
        if p and p.get('mh4uId') is not None:
            iid=int(p['mh4uId'])
            mhrow=con.execute('select * from items where _id=?',(iid,)).fetchone()
            return p,dict(mhrow) if mhrow else None
        mh=mh_items_by_jp.get(jp_name) or mh_items_by_jp.get(str(jp_name).replace('靭','靱')) or mh_items_by_jp.get(str(jp_name).replace('靱','靭'))
        if not mh:
            return p,None
        iid=int(mh['_id'])
        p=items_by_mh.get(iid)
        if p:
            if p.get('name')!=korean_name and korean_name not in p.get('aliases',[]):
                p.setdefault('aliases',[]).append(korean_name); alias_adds.append((p['name'],korean_name))
            return p,mh
        # Add an item row so armor material links can be opened.
        pid=f'item_mh4u_{iid:04d}'
        p={
            'id':pid,'name':korean_name,'nameJa':jp_name,'rare':mh.get('rarity') or '',
            'maxStack':mh.get('carry_capacity') or '','buyPrice':('-' if not mh.get('buy') else f"{mh.get('buy')}z"),
            'sellPrice':('-' if not mh.get('sell') else f"{mh.get('sell')}z"),
            'acquire':'몬스터·퀘스트' if mh.get('type')!='Coin/Ticket' else '퀘스트·투기대회 보수',
            'availability':'','note':'','source':'Arena DB + MH4U DB','nameEn':mh.get('name') or '',
            'mh4uId':iid,'itemType':mh.get('type') or '','itemSubType':mh.get('sub_type') or ''
        }
        items.append(p); items_by_mh[iid]=p; items_by_name[korean_name]=p; added_items.append(p)
        return p,mh

    # Add special quest reward names into quest reference index.
    qrefs=qindex.setdefault('quests',{})
    special_reward_names={
        'event-g-076':['강욕티켓','대장로티켓S'],
        'event-g-071':['폭풍룡티켓','대장로티켓S'],
        'event-g-078':['홍룡티켓','대장로티켓S'],
        'event-g-077':['인아도의 증표'],
    }
    for qid,names in special_reward_names.items():
        if qid not in proj_q_by_id: continue
        row=qrefs.setdefault(qid,{'monsters':[],'rewardItems':[],'rewardDetails':[],'tags':['event'],'location':proj_q_by_id[qid].get('location',''),'level':proj_q_by_id[qid].get('level',''),'questType':'event'})
        row.setdefault('rewardItems',[])
        row.setdefault('rewardDetails',[])
        for n in names:
            if n not in row['rewardItems']: row['rewardItems'].append(n)
            if not any(d.get('name')==n for d in row['rewardDetails']): row['rewardDetails'].append({'name':n,'source':'MH4G event cross-reference'})

    coverage={'materials':0,'withMonster':0,'withQuest':0,'withArena':0,'withAcquireText':0,'unresolved':0}
    unresolved=[]
    progression_audit=[]

    for a in targets:
        kmats=parse_korean_materials(a.get('materials',''))
        jmats=athena_rows.get(norm(a.get('nameJa','')),[])
        mats=[]
        for idx,(kname,count) in enumerate(kmats):
            jp=jmats[idx][0] if idx<len(jmats) else ''
            # Correct count from Athena if parser and source differ.
            if idx<len(jmats): count=jmats[idx][1]
            pitem,mh=project_item_for(kname,jp)
            sources=[]
            source_kinds=set()
            if kname=='※상점판매' or jp=='※店売り':
                sources.append({'type':'shop','label':'상점에서 직접 구입'});source_kinds.add('shop')
            if mh:
                iid=int(mh['_id'])
                # Monster carve/capture/break rewards.
                mrows=con.execute('select * from hunting_rewards where item_id=? order by percentage desc',(iid,)).fetchall()
                grouped={}
                for rr in mrows:
                    mon=mh_monsters.get(rr['monster_id']);
                    if not mon: continue
                    label,nav_mon=localized_monster(mon.get('name') or '')
                    key=label
                    rec=grouped.setdefault(key,{'type':'monster','name':label,'navMonster':nav_mon,'nameEn':mon.get('name') or '', 'rank':rank_ko(rr['rank']),'methods':[]})
                    method=' · '.join(x for x in [rr['condition'],f"{rr['percentage']}%" if rr['percentage'] is not None else '',f"×{rr['stack_size']}" if rr['stack_size'] else ''] if x)
                    if method and method not in rec['methods']: rec['methods'].append(method)
                if grouped:
                    sources.extend(grouped.values());source_kinds.add('monster')
                # Quest rewards from MH4U DB (map to project quest when possible).
                qrows=con.execute('''select q.*,qr.reward_slot,qr.percentage,qr.stack_size from quest_rewards qr join quests q on q._id=qr.quest_id where qr.item_id=? order by qr.percentage desc''',(iid,)).fetchall()
                seenq=set()
                for rr in qrows:
                    pq=proj_q_by_en.get(norm(rr['name']))
                    key=(pq['id'] if pq else f"mh4u:{rr['_id']}")
                    if key in seenq: continue
                    seenq.add(key)
                    rec={'type':'quest','id':pq['id'] if pq else '', 'name':pq['name'] if pq else rr['name'], 'nameEn':rr['name'],'level':pq.get('level','') if pq else f"{rr['hub']}★{rr['stars']}", 'questType':pq.get('questType','') if pq else rr['hub'], 'location':pq.get('location','') if pq else '', 'objective':pq.get('objective','') if pq else rr['goal'], 'probability':rr['percentage'], 'count':rr['stack_size']}
                    sources.append(rec);source_kinds.add('quest')
                # Wyporium exchange (materials from monsters not directly huntable in MH4G).
                wrows=con.execute('select * from wyporium where item_out_id=?',(iid,)).fetchall()
                for wr in wrows:
                    in_item=con.execute('select * from items where _id=?',(wr['item_in_id'],)).fetchone()
                    uq=con.execute('select * from quests where _id=?',(wr['unlock_quest_id'],)).fetchone() if wr['unlock_quest_id'] else None
                    pin=items_by_mh.get(int(wr['item_in_id'])) if wr['item_in_id'] else None
                    pq=proj_q_by_en.get(norm(uq['name'])) if uq else None
                    sources.append({'type':'exchange','required':pin['name'] if pin else (in_item['name'] if in_item else ''),'requiredItemId':pin['id'] if pin else '', 'unlockQuestId':pq['id'] if pq else '', 'unlockQuest':pq['name'] if pq else (uq['name'] if uq else ''), 'unlockLevel':pq.get('level','') if pq else '', 'label':'용인족 도매상 소재교환'})
                    source_kinds.add('exchange')
                # Arena rewards.
                arows=con.execute('''select aq.*,ar.percentage,ar.stack_size from arena_rewards ar join arena_quests aq on aq._id=ar.arena_id where ar.item_id=? order by ar.percentage desc''',(iid,)).fetchall()
                seena=set()
                for rr in arows:
                    if rr['_id'] in seena: continue
                    seena.add(rr['_id'])
                    sources.append({'type':'arena','name':rr['name'],'level':'투기대회','probability':rr['percentage'],'count':rr['stack_size']});source_kinds.add('arena')
            # Facility-only Green Plesioth G-rank materials: unlocked by a specific G★1 quest, then obtained from the Sunsnug Isle casting machine.
            if jp in {'翠水竜の厚鱗','翠水竜の特上ビレ'}:
                pq=proj_q_by_jp.get('高難度：化け鮫達、釣場に 参 上') or proj_q_by_jp.get('高難度：化け鮫達、釣場に参上')
                sources.append({'type':'facility','label':'따끈따끈섬 투망 머신 Lv4 · 가노토토스 아종','unlockQuestId':pq['id'] if pq else '', 'unlockQuest':pq['name'] if pq else '고난도: 괴상어, 낚시터 난입','unlockLevel':pq.get('level','G★1') if pq else 'G★1','note':'해당 퀘스트 클리어 후 가노토토스 아종이 투망 머신에 출현'})
                source_kinds.add('facility')
            # Project Wyporium/Dragon Elder exchange data is more localized and complete for MH4G-only materials.
            dx=dragon_by_result.get(norm(kname)) or dragon_by_jp.get(norm(jp))
            if dx and not any(s.get('type')=='exchange' for s in sources):
                # Try to identify an existing quest by the Korean/Japanese text embedded in the unlock description.
                unlock=str(dx.get('unlock') or '')
                pq=None
                for q in quests:
                    if (q.get('name') and q['name'] in unlock) or (q.get('nameJa') and norm(q['nameJa']) in norm(unlock)):
                        pq=q;break
                req_item=items_by_name.get(dx.get('required',''))
                sources.append({'type':'exchange','required':dx.get('required',''),'requiredItemId':req_item.get('id','') if req_item else '', 'unlockQuestId':pq['id'] if pq else '', 'unlockQuest':pq['name'] if pq else unlock, 'unlockLevel':pq.get('level','') if pq else '', 'label':'용인족 도매상 소재교환'})
                source_kinds.add('exchange')
            # Project-specific event quest links.
            for qid,qtype,note in SPECIAL_QUESTS.get(jp,[]):
                pq=proj_q_by_id.get(qid)
                if pq:
                    if not any(s.get('type')=='quest' and s.get('id')==qid for s in sources):
                        sources.insert(0,{'type':'quest','id':qid,'name':pq['name'],'nameJa':pq.get('nameJa',''),'nameEn':pq.get('nameEn',''),'level':pq.get('level',''),'questType':pq.get('questType','event'),'location':pq.get('location',''),'objective':pq.get('objective',''),'note':note})
                    source_kinds.add('quest')
            for rec in SPECIAL_TEXT_QUESTS.get(jp,[]):
                if not any(s.get('type')=='quest' and (s.get('nameJa')==rec.get('nameJa') or s.get('name')==rec.get('name')) for s in sources):
                    sources.insert(0,dict(rec));source_kinds.add('quest')
            # Known non-huntable MH4G material routes that are not represented by MH4U reward tables.
            if not sources and (jp in {'水竜の鱗','水竜のヒレ','エビの小殻','エビの尾扇'} or kname in {'수룡 비늘','수룡 지느러미','새우작은껍질','새우부채꼬리'}):
                sources.append({'type':'facility','label':'따끈따끈섬 투망 머신 · 가노토토스 계열','note':'투망 머신에서 가노토토스 및 관련 보너스 소재를 획득'});source_kinds.add('facility')
            if not sources and (kname=='팍튀호두' or jp=='はじけクルミ'):
                sources.append({'type':'gather','label':'필드 채집','note':'채집 포인트에서 획득하는 일반 소재'});source_kinds.add('acquire')
            if not sources and kname=='헌터모집공지':
                sources.append({'type':'quest','id':'','name':'헌터 일지 괴조 편','nameJa':'ハンター日誌　怪鳥の回','level':'G★1','questType':'event','location':'유적평원','objective':'얀쿡 2마리 이상 수렵 후 귀환 또는 네코택 티켓 납품','note':'기본 보수에서 헌터모집공지를 획득'});source_kinds.add('quest')
            if not sources and kname=='은백의 갈기':
                sources.append({'type':'quest','id':'','name':'키린 토벌','nameJa':'キリンの討伐','level':'길드퀘 Lv116~125','questType':'guildquest','location':'','objective':'키린 토벌','note':'고레벨 G급 길드 퀘스트 기본 보수에서 확인'});source_kinds.add('quest')
            if not sources and kname=='여신의 포옹':
                pq=proj_q_by_id.get('event-g-061')
                if pq:
                    sources.append({'type':'quest','id':pq['id'],'name':pq['name'],'nameJa':pq.get('nameJa',''),'nameEn':pq.get('nameEn',''),'level':pq.get('level','G★3'),'questType':'event','location':pq.get('location',''),'objective':pq.get('objective',''),'note':'여신의 포옹 보수'});source_kinds.add('quest')
                else:
                    sources.append({'type':'quest','id':'','name':'신들의 황혼','nameEn':'Twilight of the Gods','level':'G★3','questType':'event','note':'여신의 포옹 이벤트 보수'});source_kinds.add('quest')
            # Non-crafting unlock conditions are still valid progression information.
            if not sources and (str(jp).startswith('※') or '클리어' in kname or '특수조건' in kname):
                sources.append({'type':'special','label':kname,'note':'제작 소재가 아니라 장비 출현/해금 조건'});source_kinds.add('acquire')
            # Fallback to project item's general acquisition text.
            if pitem and pitem.get('acquire') and not sources:
                sources.append({'type':'acquire','label':pitem.get('acquire')});source_kinds.add('acquire')
            # Keep a visible unresolved marker instead of leaving the detail panel blank.
            if not sources:
                sources.append({'type':'unknown','label':'입수 경로 추가 확인 필요','note':kname});source_kinds.add('unknown')
            # Keep sources concise: preferred event quest first, then top 3 monster and top 3 quests, arena top 3, fallback.
            eventq=[s for s in sources if s.get('type')=='quest' and (s.get('questType')=='event' or str(s.get('id','')).startswith('event-'))]
            normalq=[s for s in sources if s.get('type')=='quest' and s not in eventq]
            mons=[s for s in sources if s.get('type')=='monster']
            arenas=[s for s in sources if s.get('type')=='arena']
            exchanges=[s for s in sources if s.get('type')=='exchange']
            other=[s for s in sources if s.get('type') not in {'quest','monster','arena','exchange'}]
            sources=(eventq[:3]+mons[:3]+normalq[:3]+exchanges[:2]+arenas[:3]+other[:2])
            mat={'name':kname,'count':count,'nameJa':jp,'itemId':pitem['id'] if pitem else '', 'mh4uId':int(mh['_id']) if mh else None,'sources':sources}
            mats.append(mat)
            coverage['materials']+=1
            if 'monster' in source_kinds:coverage['withMonster']+=1
            if 'quest' in source_kinds:coverage['withQuest']+=1
            if 'arena' in source_kinds:coverage['withArena']+=1
            if 'exchange' in source_kinds:coverage.setdefault('withExchange',0);coverage['withExchange']+=1
            if 'facility' in source_kinds:coverage.setdefault('withFacility',0);coverage['withFacility']+=1
            if 'acquire' in source_kinds or 'shop' in source_kinds:coverage['withAcquireText']+=1
            if 'unknown' in source_kinds:
                coverage['unresolved']+=1;unresolved.append({'armor':a['name'],'material':kname,'nameJa':jp})
        # Build top-level unique targets for quick summary.
        monsters_u=[]; quests_u=[]; arenas_u=[]
        for m in mats:
            for s in m['sources']:
                if s['type']=='monster':
                    key=s.get('name') or ''
                    if key and not any(x.get('name')==key for x in monsters_u):
                        monsters_u.append({'name':key,'navMonster':s.get('navMonster','')})
                elif s['type']=='quest':
                    key=s.get('id') or s.get('name')
                    if key and not any((x.get('id') or x.get('name'))==key for x in quests_u):quests_u.append({k:s.get(k,'') for k in ['id','name','nameJa','level','questType','location','objective','note']})
                elif s['type']=='arena' and s['name'] not in [x['name'] for x in arenas_u]:arenas_u.append({k:s.get(k,'') for k in ['name','level','probability']})
        a['progression']={'materials':mats,'targets':{'monsters':monsters_u,'quests':quests_u,'arena':arenas_u},'source':'Athena armor materials + MH4U reward DB + MH4G event cross-reference'}
        progression_audit.append({'id':a['id'],'name':a['name'],'materialCount':len(mats),'monsters':len(monsters_u),'quests':len(quests_u),'arena':len(arenas_u)})

    # Keep the main armor DB light: progression is lazy-loaded per armor row.
    prog_dir=DATA/'armor_progressions'
    if prog_dir.exists(): shutil.rmtree(prog_dir)
    prog_dir.mkdir(parents=True,exist_ok=True)
    prog_index={}
    for a in armors:
        prog=a.pop('progression',None)
        if not prog: continue
        save_json(prog_dir/f"{a['id']}.json",prog)
        prog_index[a['id']]={'materials':len(prog.get('materials') or []),'monsters':len((prog.get('targets') or {}).get('monsters') or []),'quests':len((prog.get('targets') or {}).get('quests') or [])}
    save_json(DATA/'armor_progression_index.json',{'version':'0.7.7-chat4-research2-hotfix18','count':len(prog_index),'armors':prog_index})
    # Rebuild item reverse references using the existing project builder so aliases/items are reflected.
    save_json(DATA/'armors.json',armors)
    save_json(DATA/'items.json',items)
    save_json(DATA/'quest_reference_index.json',qindex)
    report={
        'version':'0.7.7-chat4-research2-hotfix18','step':'all armor acquisition progression',
        'summary':{'armors':len(targets),'addedItems':len(added_items),'aliasAdds':len(alias_adds),**coverage},
        'addedItems':[{'id':x['id'],'name':x['name'],'nameJa':x.get('nameJa',''),'mh4uId':x.get('mh4uId')} for x in added_items],
        'aliasAdds':[{'item':a,'alias':b} for a,b in alias_adds],
        'unresolved':unresolved,'armors':progression_audit,
        'specialEventMappings':{
            '강욕티켓':'이벤트 G★3 극한의 포식자 (喰慾の極限)',
            '폭풍룡티켓':'이벤트 G★3 고그마지오스 포격전 (巨戟砕くは砲撃の雨)',
            '홍룡티켓':'이벤트 G★3 진홍의 장막 너머 (紅の終焉)',
            '대장로티켓S':'고그마지오스 포격전 등 G★3 이벤트 보수'
        }
    }
    save_json(ROOT/'tools'/'armor_progression_audit_v0.7.7.json',report)
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
    if unresolved:
        print('UNRESOLVED',len(unresolved))
        for x in unresolved[:60]: print(x)

if __name__=='__main__': main()
