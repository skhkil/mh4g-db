#!/usr/bin/env python3
import json, sqlite3, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
QUESTS=ROOT/'data/quests.json'
META=ROOT/'data/meta.json'
MH4U=Path('/mnt/data/eventbuild/mh4u/mh4u.db')

# Localized English DLC list from Monster Hunter Wiki, cross-checked against the user-supplied MH4U DB.
# Korean titles/objectives are an unofficial translation for this project.
loc_ko={
'Arena':'격투장','Slayground':'입체투기장','Ancestral Steppe':'유적 평원','Sunken Hollow':'지저 동굴',
'Primal Forest':'원생림','Frozen Seaway':'빙해','Volcanic Hollow':'지저 화산',"Heaven's Mount":'천공산',
'Dunes (Day)':'구사막<낮>','Dunes (Night)':'구사막<밤>','Sanctuary':'금지된 땅','Great Sea':'대해',
'Great Desert':'대사막','Ingle Isle':'용암섬','Polar Field':'극권','Speartip Crag':'천검산','Tower Summit':'탑 꼭대기',
'Castle Schrade':'슈레이더성','Battlequarters':'전투 구역'
}

mon={
'Felyne':'아이루','Melynx':'메라루','Remobra':'가브라스','Tetsucabra':'테츠카브라','Yian Kut-Ku':'얀쿡크',
"Dah'ren Mohran":'다렌·모란','Rathalos':'리오레우스','Konchu':'쿤추','Seregios':'셀레기오스','Daimyo Hermitaur':'다이묘자자미',
'Cephadrome':'도스가레오','Basarios':'바살모스','Ruby Basarios':'바살모스 아종','Najarala':'가라라아자라','Kirin':'키린',
'Oroshi Kirin':'키린 아종','Gore Magala':'고어·마가라','Shagaru Magala':'샤가르마가라','Furious Rajang':'격앙 라잔','Rajang':'라잔',
'Dalamadur':'다라 아마듈라','Molten Tigrex':'티가렉스 희소종','Silver Rathalos':'리오레우스 희소종','Gold Rathian':'리오레이아 희소종',
'Fatalis':'밀라보레아스','Crimson Fatalis':'홍룡 밀라보레아스','Deviljho':'이블조','Congalala':'바바콩가','Emerald Congalala':'바바콩가 아종',
'Lagombi':'울크스스','Gravios':'그라비모스','Zamtrios':'자보아자길','Tigrex':'티가렉스','Brute Tigrex':'티가렉스 아종',
'Zinogre':'진오우거','Azure Rathalos':'리오레우스 아종','Kushala Daora':'크샬다오라','Berserk Tetsucabra':'테츠카브라 아종',
'Tigerstripe Zamtrios':'자보아자길 아종','Pink Rathian':'리오레이아 아종','Iodrome':'도스이오스','Purple Gypceros':'게리오스 아종',
'Nerscylla':'넬스큐라','Ash Kecha Wacha':'케차와차 아종','Kecha Wacha':'케차와차','Seltas':'알셀타스','Desert Seltas':'알셀타스 아종',
'Desert Seltas Queen':'게넬·셀타스 아종','Seltas Queen':'게넬·셀타스','Yian Garuga':'얀가루루가','Gypceros':'게리오스',
'Shrouded Nerscylla':'넬스큐라 아종','Khezu':'푸루푸루','Red Khezu':'푸루푸루 아종','Diablos':'디아블로스','Apex Diablos':'극한 상태 디아블로스',
'Teostra':'테오·테스카토르','Chameleos':'오오나즈치','White Fatalis':'조룡 밀라보레아스','Akantor':'아캄토름','Ukanlos':'우캄루바스',
'Shah Dalamadur':'다라 아마듈라 아종','Raging Brachydios':'맹폭 브라키디오스','Gogmazios':'고그마지오스','Savage Deviljho':'광폭 이블조',
'Brachydios':'브라키디오스','Cephalos':'가레오스','Bnahabra':'브나하브라','Velociprey':'람포스','Genprey':'게네포스',
'Blue Yian Kut-Ku':'얀쿡크 아종','Plum Daimyo Hermitaur':'다이묘자자미 아종','Velocidrome':'도스람포스',
'Stygian Zinogre':'진오우거 아종','Tidal Najarala':'가라라아자라 아종','Rathian':'리오레이아' 
}
item={
'Secret Stash':'비밀의 파우치','Fulgurbugs':'초전뇌광충','Fulgerbugs':'초전뇌광충','Fulgurbug':'초전뇌광충','Blue Marlin':'청새치',
'Giant Stags':'왕사슴벌레','Well-done Steaks':'잘 익은 고기','Rare Steaks':'설익은 고기','Large Wyvern Tear':'용의 큰눈물방울',
'Large Beast Tear':'아수의 큰눈물방울','Wyvern Tear':'용의 눈물방울','Paw Pass Ticket':'야옹택시 티켓'
}

def mko(s):
    s=s.strip()
    frenzy=False
    if s.startswith('Frenzied '): frenzy=True; s=s[len('Frenzied '):]
    apex=False
    if s.startswith('Apex '): apex=True; s=s[len('Apex '):]
    out=mon.get(s,s)
    if frenzy: out='광룡화 '+out
    if apex: out='극한 상태 '+out
    return out

def objective_ko(en):
    if not en or en in ('None','N/A'): return ''
    s=en.strip().rstrip('.')
    # exact specials first
    exact={
      'Slay 12 Felyne and 12 Melynx':'아이루 12마리와 메라루 12마리 토벌',
      'Slay 12 Remobras':'가브라스 12마리 토벌','Capture a Yian Kut-Ku':'얀쿡크 1마리 포획',
      "Slay Dah'ren Mohran or repel it":'다렌·모란 토벌 또는 격퇴','Hunt 2 Frenzied Rathalos':'광룡화 리오레우스 2마리 수렵',
      'Slay 12 Konchu':'쿤추 12마리 토벌','Deliver 1 Blue Marlin':'청새치 1마리 납품','Deliver 5 Giant Stags':'왕사슴벌레 5마리 납품',
      'Deliver 10 Well-done Steaks':'잘 익은 고기 10개 납품','Deliver 3 Rare Steaks':'설익은 고기 3개 납품',
      'Slay 2 Furious Rajang':'격앙 라잔 2마리 토벌','Slay Dalamadur':'다라 아마듈라 토벌','Slay 1 Akantor':'아캄토름 1마리 토벌',
      'Slay an Akantor':'아캄토름 토벌','Slay an Ukanlos':'우캄루바스 토벌','Slay Gore Magala':'고어·마가라 토벌',
      'Slay a Crimson Fatalis or repel it':'홍룡 밀라보레아스 토벌 또는 격퇴','Slay a Fatalis or repel it':'밀라보레아스 토벌 또는 격퇴',
      'Slay a White Fatalis or repel it':'조룡 밀라보레아스 토벌 또는 격퇴','Slay a Chameleos or repel it':'오오나즈치 토벌 또는 격퇴',
      'Slay Gogmazios':'고그마지오스 토벌','Slay a Shah Dalamadur':'다라 아마듈라 아종 토벌','Slay a Raging Brachydios':'맹폭 브라키디오스 토벌',
      'Slay 40 Remobra':'가브라스 40마리 토벌','Hunt 10 Desert Seltas':'알셀타스 아종 10마리 수렵',
      "Sever the Rathian's tail":'리오레이아의 꼬리 절단','Deliver 1 Large Wyvern Tear':'용의 큰눈물방울 1개 납품',
      'Deliver 1 Large Beast Tear':'아수의 큰눈물방울 1개 납품','Deliver 10 Secret Stash':'비밀의 파우치 10개 납품',
      'Deliver 3 Fulgurbugs':'초전뇌광충 3마리 납품','Deliver 3 Fulgerbugs':'초전뇌광충 3마리 납품',
      "Wound the Congalala's tail":'바바콩가의 꼬리 부위 파괴',
      "Wound the Kecha Wacha's ears and the Ash Kecha Wacha's ears":'케차와차와 케차와차 아종의 귀 부위 파괴',
      "Wound the Kecha Wacha's and Ash Kecha Wacha's ears":'케차와차와 케차와차 아종의 귀 부위 파괴',
      'Topple monster while mounted':'탑승 공격으로 몬스터 다운',
      'Slay 50 Bnahabra':'브나하브라 50마리 토벌','Slay 10 Velociprey and 10 Genprey':'람포스 10마리와 게네포스 10마리 토벌',
      'Hunt 2 Yian Kut-Ku before time expires or deliver Paw Pass Ticket':'제한 시간 내 얀쿡크 2마리 수렵 또는 야옹택시 티켓 납품',
    }
    if s in exact: return exact[s]
    body_parts={
      'jaw':'턱','comb':'볏','head':'머리','top fin':'등지느러미','back':'등','chest':'가슴','tail':'꼬리',
      'horns':'뿔','horn':'뿔','feelers':'촉각','blowhole':'분기공','belly':'배','front leg':'앞다리',
      'wingarms':'익각','legs':'다리','ears':'귀','chin':'턱'
    }
    def pko(x): return body_parts.get(x.strip().lower(),x.strip())
    def target_list(text):
      # Articles are syntax, not part of monster names.
      parts=re.split(r',\s*(?:and\s+)?|\s+and\s+',text.strip())
      return [re.sub(r'^(?:a|an)\s+','',x.strip()) for x in parts if x.strip()]
    # Hunt all X
    if s.startswith('Hunt all '): return mko(s[9:])+' 모두 수렵'
    # Hunt N X
    ma=re.fullmatch(r'Hunt (\d+) (.+)',s)
    if ma: return f"{mko(ma.group(2))} {ma.group(1)}마리 수렵"
    # Hunt one or more named targets
    if s.startswith('Hunt '):
      targets=target_list(s[5:])
      if targets and all(t for t in targets):
        return '와 '.join(f'{mko(t)} 1마리' for t in targets)+' 수렵'
    # Slay one or more named targets
    if s.startswith('Slay '):
      rest=s[5:]
      ma=re.fullmatch(r'(\d+) (.+)',rest)
      if ma: return f"{mko(ma.group(2))} {ma.group(1)}마리 토벌"
      targets=target_list(rest)
      if targets and all(t for t in targets):
        return '와 '.join(mko(t) for t in targets)+' 토벌'
    # common subquest verbs
    ma=re.fullmatch(r'Wound (?:the )?(.+?)[\'’]s (.+)',s)
    if ma: return f"{mko(ma.group(1))}의 {pko(ma.group(2))} 부위 파괴"
    ma=re.fullmatch(r'Break (?:the )?(.+?)[\'’]s (.+)',s)
    if ma: return f"{mko(ma.group(1))}의 {pko(ma.group(2))} 부위 파괴"
    ma=re.fullmatch(r'Sever (?:the )?(.+?)[\'’]s (.+)',s)
    if ma: return f"{mko(ma.group(1))}의 {pko(ma.group(2))} 절단"
    ma=re.fullmatch(r'Deliver (\d+) (.+)',s)
    if ma: return f"{item.get(ma.group(2),ma.group(2))} {ma.group(1)}개 납품"
    return s

def R(group,level,en,ko,ja,obj,loc,reward,hrp,fee,time=50,sub='',subreward=0,subhrp=0,mh4u=None):
    return dict(group=group,level=level,en=en,ko=ko,ja='' if ja=='n/a' else ja,obj=obj,loc=loc,reward=reward,hrp=hrp,fee=fee,time=time,sub=sub,subreward=subreward,subhrp=subhrp,mh4u=mh4u)

regular=[]
# Low rank localized DLC (6)
regular += [
R('low','★1','Uniqlo: Hunt for Inspiration','유니클로: 아이디어를 찾아서','ユニクロ・アイデアを求めて','Slay 12 Felyne and 12 Melynx','Arena',3300,120,400,mh4u=502),
R('low','★2','Fan Club: Remobra Removal','몬헌부: 가브라스 소탕전','モンハン部・ガブラス狩猟戦線','Slay 12 Remobras','Arena',3600,210,400,sub='Hunt a Tetsucabra',subreward=3600,subhrp=420,mh4u=503),
R('low','★3','The Poogie King','푸기의 왕','OP・イャンクックを追え！','Capture a Yian Kut-Ku','Arena',4200,290,500,mh4u=509),
R('low','★3','Sand Blasted','모래바람을 뚫고','砂漠に鳴らせ、勝ちどきの銅鑼',"Slay Dah'ren Mohran or repel it",'Great Desert',11100,840,1200,time=35,mh4u=501),
R('low','★3','USJ: High-fire Act','USJ: 화룡들의 뜨거운 무대','USJ・火竜達の集い','Hunt 2 Frenzied Rathalos',"Heaven's Mount",13800,810,1400,sub='Deliver 1 Wyvern Tear',subreward=1200,subhrp=40,mh4u=511),
R('low','★3',"Rollin' Rollin' Rollin'",'굴러라! 굴러라! 굴러라!','', 'Slay 12 Konchu','Arena',5400,560,600,mh4u=536),
]
# High rank localized DLC (27)
high=[
('A Lost Civilization','잃어버린 문명','カプ本・マスコット対決！',533),('Mario: Oh, Brothers!','마리오: 오, 형제들이여!','マリオ・キノコ好きブラザーズ',529),
('Fan Club: Two-Toned Titans','몬헌부: 두 빛깔의 거수','モンハン部・赤組白組応援歌',532),('Animal Crossing: Fisher King','동물의 숲: 낚시왕','どうぶつの森・つり大会開催！',513),
("Today's Special: Meat",'오늘의 특선: 고기','肉好きのための肉の宴',514),('Plain & Carefree','평원에서 유유자적','遺跡平原ののんき者',515),
('Heavy Metal','헤비 메탈','集まれ、鉱石好き達！',516),('Leaping Terror','도약하는 공포','旧砂漠の飛び出し合戦',517),
('Might and Melody','힘과 선율','大自然に響く狩猟讃歌',519),('Gravios May Cry','그라비모스 메이 크라이','JUMP・極小鎧竜大熱戦',548),
('USJ: Zamtrios 3D','USJ: 자보아자길 3D','USJ・ザボアザギル・3D',550),('Uniqlo: Material Needs','유니클로: 소재가 필요해','ユニクロ・果てしなき挑戦',540),
('Super Sonic Seregios','초음속 셀레기오스','ソニック・千刃竜への疾走',512),('Kirin Acquisition','키린 쟁탈전','かくもめでたきキリンかな',518),
('Three Virtues','세 가지 덕목','ゼルダの伝説・力と知恵と勇気',531),('Fire Fight','화염 결전','ゼルダの伝説・決戦の猛炎覇竜',530),
('Enter the Red Dragon','홍룡 강림','紅龍来降',527),("The Devil's Due",'공폭룡의 대가','総べてを屠り、喰らう者',528),
('Out of Time','시간을 넘어','時代を翔ける龍',520),('All The Rage','분노의 극치','金の仁王、並び立つ',521),('Pillar of Strength','힘의 기둥','邪王の怒りは天蓋を衝きて',522),
('Eye of the Tigrex','티가렉스의 눈','驚天轟地',523),('Tower of Trouble','탑의 재앙','塔の頂に銀陽は輝く',524),('Royal Restoration','왕가의 부흥','女王の座を賭けた戦い！',525),
('Return of the Dragon','흑룡의 귀환','よみがえる黒龍伝説',526),('The Steel Vanguard','강철의 선봉','マガジン・鋼龍飛翔！',544),('USJ: Hot Ticket','USJ: 뜨거운 티켓','USJ・蒼と金の熱き競演！',551),
]
con=sqlite3.connect(MH4U); con.row_factory=sqlite3.Row
for en,ko,ja,qid in high:
    d=dict(con.execute('select * from quests where _id=?',(qid,)).fetchone())
    star=d['stars']; obj=d['goal']; sub=d['sub_goal'] or ''
    # Correct known localized-source differences in the older comparison DB.
    if en=='Super Sonic Seregios': obj='Hunt a Frenzied Seregios'; d['sub_hrp']=70
    if en=='Fire Fight': d['hrp']=1200; sub="Sever Akantor's tail"; d['sub_hrp']=80
    if en=="Today's Special: Meat": d['sub_hrp']=20
    regular.append(R('high',f'★{star}',en,ko,ja,obj,{r['_id']:r['name'] for r in con.execute('select _id,name from locations')}[d['location_id']],d['reward'],d['hrp'],d['fee'],d['time_limit'],sub,d['sub_reward'],d['sub_hrp'],qid))

# G1/G2/G3 localized DLC, values transcribed from the localized DLC reference and checked against DB tuples where possible.
g1=[
('Fight for the Future','미래를 위한 싸움','n/a','Hunt a Lagombi','Arena',4200,300,500,'Wound the Lagombi\'s head',1500,20),
('Protector of Peace','평화를 지키는 자','ロックマン・平和を取り戻せ','Hunt a Tetsucabra and a Berserk Tetsucabra','Arena',10500,890,1100,'',0,0),
('Taiko: Big Bellied Bruisers','태고의 달인: 배북 난타전','太鼓の達人・太鼓腹だドン！','Hunt a Tigerstripe Zamtrios and a Congalala','Arena',13800,1050,1400,'',0,0),
('Ruby of my Eye','나의 루비','桃岩竜からの贈り物','Hunt a Ruby Basarios','Arena',11100,710,1100,'',0,0,25),
('The Brave Warrior','용감한 전사','一匹虫の男道！','Hunt a Seltas','Primal Forest',4200,260,500,'',0,0),
('Bewitching Blossoms','매혹의 벚꽃','桜散らすは魅せるため','Hunt a Pink Rathian','Dunes (Night)',11700,820,1200,"Wound the Pink Rathian's back",3000,80),
('Fan Club: Desert Training','몬헌부: 사막 응원 특훈','モンハン部・砂漠の応援特訓','Hunt a Cephadrome','Dunes (Day)',7200,530,800,'Hunt 8 Cephalos',1800,100),
('Poison Pinch','독의 협공','ドクターのドキ毒研究','Hunt an Iodrome, a Purple Gypceros, and a Nerscylla','Slayground',14100,1080,1500,'',0,0),
('Crouching Tiger, Hidden Shark','웅크린 호랑이, 숨은 상어','化け鮫と虎鮫の競演','Hunt a Zamtrios and a Tigerstripe Zamtrios','Arena',14400,1080,1500,'',0,0),
("Hunter's Log: Yian Kut-Ku",'헌터의 기록: 얀쿡크','n/a','Hunt 2 Yian Kut-Ku before time expires or deliver Paw Pass Ticket','Ancestral Steppe',9300,810,1000,'Hunt 10 Yian Kut-Ku',30000,2250),
('A Small Mountain to Scale','작은 산을 넘어서','小さな挑戦者たち','Hunt a Blue Yian Kut-Ku and a Berserk Tetsucabra','Arena',10500,880,1100,'',0,0),
('Fan Club: Ashes to Ashes','몬헌부: 재는 재로','モンハン部・闘技場の熱血特訓','Hunt an Ash Kecha Wacha','Arena',9600,700,1000,"Wound the Ash Kecha Wacha's tail",3000,70),
('Bug Hunters Inc.','벌레 사냥 주식회사','巨大飛甲虫討伐ノススメ','Slay 50 Bnahabra','Arena',7800,400,800,'Hunt a Seltas',2100,130),
("Hunter's Log: Small Fry",'헌터의 기록: 잔챙이들','n/a','Slay 10 Velociprey and 10 Genprey','Arena',7500,300,800,'Hunt a Yian Garuga',12600,800),
('Big Game Hunting','대물 사냥','ランポスたちの大親分！','Hunt a Velocidrome','Arena',6000,600,400,'Hunt a Deviljho',21000,1280),
('Little Big Hermitaur','작지만 큰 다이묘자자미','ダイショウ？ダイミョウ？','Hunt 3 Plum Daimyo Hermitaur','Arena',14400,1220,1500,'',0,0),
('Red, White, and You','붉음과 하양, 그리고 너','紅白狩り合戦！','Hunt a Khezu and a Red Khezu','Arena',15600,1270,1600,'',0,0),
]
for x in g1:
    en,ko,ja,obj,loc,reward,hrp,fee,sub,sr,sh,*tm=x
    regular.append(R('g','G★1',en,ko,ja,obj,loc,reward,hrp,fee,tm[0] if tm else 50,sub,sr,sh))

g2=[
('USJ: A Colorful Feast','USJ: 화려한 향연','USJ・蒼と金の響宴！','Hunt a Zinogre and a Seregios','Arena',27000,1830,2700,'',0,0),
('USJ: Tigrex 3D','USJ: 티가렉스 3D','USJ・ティガレックス3D','Hunt a Tigrex','Arena',19200,1140,2000,'',0,0),
('Metroid: Special Mission','메트로이드: 특수 임무','メトロイド・特殊任務','Hunt a Frenzied Yian Garuga','Arena',12600,800,1300,"Wound the Yian Garuga's back",3600,80),
('Metroid: Looming Shadows','메트로이드: 다가오는 그림자','メトロイド・迫りくる骸蜘蛛','Hunt all Shrouded Nerscylla','Arena',23400,1850,2400,'',0,0),
('The Candle of Darkness','어둠의 촛불','マギ・黒き蝕を打ち晴らせ！','Slay Gore Magala','Sanctuary',15900,950,1600,"Wound Gore Magala's feelers",3600,100),
('A Song of Extremes','극한의 사냥 찬가','2頭が織り成す狩猟賛歌','Hunt a Gypceros and a Stygian Zinogre','Arena',16800,1260,1700,'',0,0),
('Only the Strong Survive','강한 자만이 살아남는다','弱肉強食の世界','Hunt a Khezu and a Shrouded Nerscylla','Arena',14100,1140,1500,'',0,0),
('Super Smash Monsters','몬스터 대난투','落ち着きのない大乱闘！','Hunt a Tidal Najarala, a Lagombi, and a Desert Seltas Queen','Arena',20700,1530,2100,'',0,0),
("Hunter's Log: Rath",'헌터의 기록: 리오 부부','n/a','Hunt a Rathian and a Rathalos',"Heaven's Mount",18600,1370,800,'',0,0),
('Horn To Be Wild','야생의 뿔','範馬刃牙・大いなる角竜','Hunt a Diablos','Arena',19200,1140,2000,"Break the Diablos's horns",3600,110),
]
for x in g2: regular.append(R('g','G★2',*x[:3],x[3],x[4],x[5],x[6],x[7],50,x[8],x[9],x[10]))

g3=[
('Twilight of the Gods','신들의 황혼','n/a','Hunt an Apex Diablos','Arena',28200,1830,2900,'',0,0),
("The Silver King's Slumber",'은빛 왕의 잠','白銀の王者よ、頂きに眠れ','Hunt a Silver Rathalos','Tower Summit',27000,1480,2700,"Sever the Silver Rathalos's tail",3900,150),
('Foreboding Lightning','불길한 번개','ラージャン、次第に強い雷','Hunt a Rajang','Dunes (Day)',21000,1280,2100,"Wound the Rajang's tail",3900,130),
('Desert Strike','사막 공습','大砂漠の撃龍船祭り！',"Slay Dah'ren Mohran or repel it",'Great Desert',21900,1920,2200,"Wound Dah'ren Mohran's blowhole",3900,190,35),
('The Ultimate Gravios','궁극의 그라비모스','究極の甲鎧','Hunt an Apex Gravios','Arena',19500,1120,2000,"Wound the Gravios's head",4500,110),
('Take the Black','흑룡을 맞이하라','運命の黒龍','Slay a Fatalis or repel it','Castle Schrade',42000,2880,4200,'',0,0,35),
('To Victory and Beyond','승리를 넘어','朝に道を聞いて覇に向うとも','Slay an Akantor','Ingle Isle',25200,1600,2600,"Wound the Akantor's belly",3900,160),
('The Crimson Shah','진홍의 사룡왕','赤棘の帝冠','Slay a Shah Dalamadur','Speartip Crag',29400,2400,3000,"Sever the Shah Dalamadur's tail",3900,240),
('An Unstoppable Rage','멈출 수 없는 격앙','強き思いは猛りて爆ぜる','Slay a Raging Brachydios','Ingle Isle',27000,1760,2700,"Wound the Raging Brachydios's front leg",3600,180),
('A Feast for the Departed','종언의 연회','終焉に至る宴','Slay a Crimson Fatalis or repel it','Ingle Isle',48300,3200,4900,'',0,0,35),
('Bombs over Gogmazios','고그마지오스 포격전','巨戟砕くは砲撃の雨','Slay Gogmazios','Battlequarters',35400,2880,3600,"Wound the Gogmazios's wingarms",4200,290),
('Sacred Wind','성스러운 바람','氷の稀聖','Slay an Oroshi Kirin','Tower Summit',22200,1280,2300,"Break the Oroshi Kirin's horn",3900,130),
("The Speartip's King",'천검산의 왕','千剣の王冠','Slay Dalamadur','Speartip Crag',29400,2400,3000,"Wound Dalamadur's legs",3900,240),
('Hear No Evil, See No Evil','보지도 듣지도 말하지도 마라','見るも言うも聞くも申','Hunt an Emerald Congalala, a Kecha Wacha, and a Furious Rajang','Ancestral Steppe',25200,1850,2600,'Deliver 1 Large Beast Tear',3900,290),
('Bedeviled Deviljho','공폭룡의 악몽','狩られます、イビルジョーに…','Hunt a Savage Deviljho',"Heaven's Mount",25200,1440,2600,"Wound the Savage Deviljho's head",3900,140),
('The Apex Predator','극한의 포식자','喰慾の極限','Hunt a Deviljho','Primal Forest',28200,1830,2900,'Deliver 1 Large Wyvern Tear',3000,180),
('Primeval Slugfest','원시의 난타전','範馬刃牙・牙剥く金獅子','Hunt a Rajang','Arena',28200,1830,2900,'Topple monster while mounted',4500,180),
('Beyond the Crimson Veil','진홍의 장막 너머','紅の終焉','Hunt a Crimson Fatalis','Ingle Isle',57900,3840,5800,'',0,0),
]
for x in g3:
    en,ko,ja,obj,loc,reward,hrp,fee,sub,sr,sh,*tm=x
    regular.append(R('g','G★3',en,ko,ja,obj,loc,reward,hrp,fee,tm[0] if tm else 50,sub,sr,sh))

assert len(regular)==78, len(regular)

# Episodic DLC (18): local DB 700-717, with objective corrections from localized reference for mask quests and names for missing 715-717.
ep_meta={
700:('Down To Business','Bonus: Stash Grab','번외: 비밀의 파우치 회수','外伝：猫の手も借りたい配達'),
701:('Down To Business','Bonus: Net Profits','번외: 그물로 이익을','外伝：飛んで網に入る雷の虫'),
702:('Down To Business','Bonus: A Bigger Boat','번외: 더 큰 배가 필요해','外伝：乗りかかった輸送船'),
703:('Code 16010','Bonus: Code Purple','번외: 코드 퍼플','外伝：秘密指令～紫～'),704:('Code 16010','Bonus: Code Black','번외: 코드 블랙','外伝：秘密指令～黒～'),705:('Code 16010','Bonus: Code White','번외: 코드 화이트','外伝：秘密指令～白～'),
706:('Of Masks & Monsters','Bonus: Miracle Mask','번외: 기적의 가면','外伝：インパクトなお面ンバ！'),707:('Of Masks & Monsters','Bonus: Mystical Mask','번외: 신비한 가면','外伝：スッゴイお面っチャ！'),708:('Of Masks & Monsters','Bonus: Running With the Devil','번외: 공폭룡과 달리기','外伝：ほ～い、恐暴竜ですよ！'),
709:('Inimitable Instructor','Bonus: Awaken!','번외: 깨어나라!','外伝：我輩、目覚める！'),710:('Inimitable Instructor','Bonus: Take Flight!','번외: 날아올라라!','外伝：飛翔せよ、我輩！！'),711:('Inimitable Instructor','Bonus: Into Eternity!','번외: 영원히!','外伝：我輩よ、永遠に！！！'),
712:('Sweetheart Square Off',"Bonus: A Lady's Lament",'번외: 소녀의 탄식','外伝：少女の嘆息'),713:('Sweetheart Square Off',"Bonus: A Maiden's Mission",'번외: 소녀의 임무','外伝：乙女の発奮'),714:('Sweetheart Square Off',"Bonus: A Girl's Gumption",'번외: 숙녀의 반격','外伝：淑女の逆襲'),
715:('Lay of the Land','Bonus: A Spreading Scourge','번외: 번져가는 재앙','外伝：災厄覆天'),716:('Lay of the Land','Bonus: Mist Amid the Ruins','번외: 폐허를 감싼 안개','外伝：霞這古都'),717:('Lay of the Land','Bonus: Total Eclipse','번외: 개기일식','外伝：日輪沈蝕'),
}
loc_by_id={r['_id']:r['name'] for r in con.execute('select _id,name from locations')}
episodic=[]
for qid in range(700,718):
    d=dict(con.execute('select * from quests where _id=?',(qid,)).fetchone())
    series,en,ko,ja=ep_meta[qid]
    obj=d['goal']; sub=d['sub_goal'] or ''
    if qid==706: obj="Wound the Congalala's tail"
    if qid==707: obj="Wound the Kecha Wacha's ears and the Ash Kecha Wacha's ears"
    if qid==715: obj='Slay 40 Remobra'
    if qid==716: obj='Slay a Chameleos or repel it'
    if qid==717: obj='Slay a White Fatalis or repel it'
    episodic.append(dict(group='episodic',level=f"★{d['stars']}",en=en,ko=ko,ja=ja,obj=obj,loc=loc_by_id[d['location_id']],reward=d['reward'],hrp=d['hrp'],fee=d['fee'],time=d['time_limit'],sub=sub,subreward=d['sub_reward'],subhrp=d['sub_hrp'],mh4u=qid,series=series))
assert len(episodic)==18

# Downloaded Challenge quests in the supplied MH4U DB. The DB has no monster_to_arena rows, so only targets independently confirmed are filled.
known_targets={
22:'진오우거 토벌',23:'고어·마가라 토벌',24:'넬스큐라 토벌',25:'자보아자길 및 광룡화 티가렉스 토벌',27:'테츠카브라 토벌',
28:'알셀타스 및 게넬·셀타스 토벌',31:'자보아자길·넬스큐라·바바콩가 아종·넬스큐라 아종 토벌',32:'광폭 이블조 토벌',
33:'울크스스 및 리오레우스 토벌',34:'광룡화 바바콩가 및 광룡화 바바콩가 아종 토벌',35:'진오우거 토벌',
36:'셀레기오스 토벌',37:'혼돈에 신음하는 고어·마가라 토벌',38:'테오·테스카토르 토벌',39:'진오우거 토벌',40:'케차와차 아종 토벌',41:'자보아자길 아종 토벌'
}
challenges=[]
for d0 in con.execute('select * from arena_quests where _id>=20 and _id<=43 order by _id'):
    d=dict(d0); en=d['name']
    if en.startswith('Challenge Quest '): ko='챌린지 퀘스트 '+en.rsplit(' ',1)[-1]; series='Challenge Quest'
    elif en.startswith('Party Challenge '): ko='파티 챌린지 '+en.rsplit(' ',1)[-1]; series='Party Challenge'
    else: ko='몬스터 페스트 '+en.rsplit(' ',1)[-1]; series='Monster Fest'
    obj=known_targets.get(d['_id'],'대상 몬스터 정보 미수록')
    challenges.append({
      'id':f"challenge-{d['_id']}",'questType':'challenge','questTypeLabel':'다운로드 챌린지','eventGroup':'challenge','eventSeries':series,
      'level':'챌린지','key':False,'name':ko,'nameJa':'','nameEn':en,'objective':obj,'objectiveEn':'',
      'location':loc_ko.get(loc_by_id[d['location_id']],loc_by_id[d['location_id']]),'fee':'-','reward':f"{d['reward']:,}z",'hrp':'-',
      'time':'-','conditions':f"최대 {d['num_participants']}인 · 지정 장비/아이템",'subObjective':'','subReward':'-',
      'note':'',
      'source':'사용자 제공 MH4U DB arena_quests + Capcom MH4U 공식 매뉴얼'
    })
assert len(challenges)==24

# Try exact tuple matching for G records without explicit id, only to record cross-check confidence; don't use ambiguous candidates as truth.
def find_db_match(r):
    enloc=r['loc']; lid=next((k for k,v in loc_by_id.items() if v==enloc),None)
    stars={'G★1':8,'G★2':9,'G★3':10}.get(r['level'])
    if not lid or not stars: return []
    rows=con.execute('select _id,name,goal from quests where _id between 501 and 600 and stars=? and location_id=? and time_limit=? and fee=? and reward=?',(stars,lid,r['time'],r['fee'],r['reward'])).fetchall()
    return [dict(x) for x in rows]

out=[]
for i,r in enumerate(regular+episodic,1):
    matches=[] if r.get('mh4u') else find_db_match(r)
    note_parts=[]
    if r.get('series'): note_parts.append(f"에피소드: {r['series']}")
    if r.get('en')=='Kirin Acquisition': note_parts.append('해외판 게임 화면에는 Kirin Aquisition으로 오탈자 표기')
    if matches:
      ids=[x['_id'] for x in matches]
      pass
    out.append({
      'id':f"event-{r['group']}-{i:03d}",'questType':'event','questTypeLabel':'이벤트','eventGroup':r['group'],'eventSeries':r.get('series',''),
      'level':r['level'],'key':False,'name':r['ko'],'nameJa':r['ja'],'nameEn':r['en'],'objective':objective_ko(r['obj']),'objectiveEn':r['obj'],
      'location':loc_ko.get(r['loc'],r['loc']),'fee':f"{r['fee']:,}z",'reward':f"{r['reward']:,}z",'hrp':str(r['hrp']),
      'time':f"{r['time']}분",'conditions':'DLC 이벤트','subObjective':objective_ko(r['sub']),'subObjectiveEn':r['sub'],
      'subReward':f"{r['subreward']:,}z" if r['subreward'] else '-', 'subHrp':str(r['subhrp']) if r['subhrp'] else '-',
      'note':' · '.join(note_parts),'source':'Monster Hunter Wiki MH4U: Event Quests + 사용자 제공 MH4U DB 비교'
    })

base=json.loads(QUESTS.read_text(encoding='utf-8'))
base=[q for q in base if q.get('questType') not in ('event','challenge')]
allq=base+out+challenges
QUESTS.write_text(json.dumps(allq,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

meta=json.loads(META.read_text(encoding='utf-8'))
meta['version']='0.7.7'; meta.setdefault('counts',{})['quests']=len(allq)
meta['eventQuestUpdate']={
  'localizedEventRegular':len(regular),'episodic':len(episodic),'downloadChallenge':len(challenges),'added':len(out)+len(challenges),
  'baseQuestCount':len(base),'finalQuestCount':len(allq),
  'policy':'MH4U DLC event/episode/challenge data maintained for the project.',
  'sources':['user-supplied MH4U mh4u.db','Monster Hunter Wiki MH4U: Event Quests','Capcom MH4U Official Web Manual'],
  'athena':'User-supplied Athena Data.zip contains no quest dataset usable for event-quest cross-check.'
}
meta['note']='실제 MH4G 데이터. v0.7.7 이벤트 퀘스트 78개, 에피소드 18개, 다운로드 챌린지 24개 및 한국어 주표기 + 일본어/영어 보조표기를 포함함.'
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

report={
 'version':'0.7.7','baseQuests':len(base),'eventRegular':len(regular),'episodic':len(episodic),'challenge':len(challenges),'finalQuests':len(allq),
 'groups':{g:sum(1 for q in out if q['eventGroup']==g) for g in ['low','high','g','episodic']},
 'challengeConfirmedTargets':len(known_targets),'challengeUnconfirmedTargets':len(challenges)-len(known_targets),
 'screenshotsHighEnglishTitlesCovered':all(any(q.get('nameEn')==({'Kirin Aquisition':'Kirin Acquisition'}.get(x,x)) for q in out) for x in [
  'Bonus: Stash Grab','Super Sonic Seregios','Animal Crossing: Fisher King',"Today's Special: Meat",'Plain & Carefree','Heavy Metal','Leaping Terror','Kirin Aquisition',
  'Might and Melody','Out of Time','All The Rage','Pillar of Strength','Eye of the Tigrex','Tower of Trouble','Royal Restoration','Return of the Dragon','Enter the Red Dragon',
  "The Devil's Due",'Mario: Oh, Brothers!','Fire Fight','Three Virtues','Fan Club: Two-Toned Titans','A Lost Civilization','Uniqlo: Material Needs','The Steel Vanguard','Gravios May Cry','USJ: Zamtrios 3D','USJ: Hot Ticket']),
 'screenshotAliases':{'Kirin Aquisition':'Kirin Acquisition (canonical localized title)'},
 'knownSourceConflicts':[
  'Fan Club: Remobra Removal sub HRP: localized reference 420 vs supplied MH4U DB 240 -> localized reference used',
  'Sand Blasted: localized reference has no subquest vs supplied MH4U DB horn-break subquest -> localized reference used',
  "Today's Special: Meat sub HRP: localized reference 20 vs supplied MH4U DB 300 -> localized reference used",
  'Super Sonic Seregios: localized reference target is Frenzied Seregios and sub HRP 70; supplied DB omits Frenzied and has sub HRP 0 -> localized reference used',
  'Fire Fight: localized reference HRP 1200 + tail subquest; supplied DB has HRP 1800 and missing sub goal -> localized reference used',
  'Twilight of the Gods: localized reference reward 28200/fee2900; supplied named DB row conflicts (19200/2000) -> localized reference used'
 ]
}
(ROOT/'tools/event_quests_v0.7.7.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
