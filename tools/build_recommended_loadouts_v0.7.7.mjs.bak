import fs from 'fs';
import {searchBuilds} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(new URL(`../${p}`,import.meta.url),'utf8'));
const skills=read('data/skills.json'), simArmors=read('data/sim_armors.json'), fullArmors=read('data/armors.json'), decorations=read('data/decorations.json');
const rareById=new Map(fullArmors.map(a=>[a.id,Number(a.rare||0)]));
const fullById=new Map(fullArmors.map(a=>[a.id,a]));
const baseData={skills,armors:simArmors.map(a=>({...a,rare:rareById.get(a.id)||0,materials:fullById.get(a.id)?.materials||''})),decorations};
const activationByName={}; for(const s of skills) for(const a of s.activations||[]) if(Number(a.points)>0) activationByName[a.name]={id:a.id,skillId:s.id,name:a.name,points:Number(a.points)};
const gunner=new Set(['라이트보우건','헤비보우건','활']);
const rareRe=/(티켓|코인|증표|보옥|천린|대보옥|홍옥|역린|천각|천갑|천인|희소)/g;
const SOURCES={
 low:{type:'커뮤니티 진행 조언',title:'MH4U Low Rank armor discussion',url:'https://www.reddit.com/r/mh4u/comments/1kpkkdq/',note:'하위는 Velociprey/Kut-Ku 공격형, Tetsucabra 방어형처럼 제작이 쉬운 진행 장비를 쓰고 빠르게 상위로 넘어가는 의견이 반복됨.'},
 highbm:{type:'커뮤니티 진행 조언',title:'High Rank armor / Double Gore discussion',url:'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71266787',note:'상위 검사에서 Double Gore, Rath Soul, Garuga S 등 Sharpness/Challenger 계열 진행 세트가 반복 추천됨.'},
 gs:{type:'커뮤니티 정석',title:'GS progression / G-rank skill discussions',url:'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71393054',note:'대검은 Focus + Critical Draw가 핵심이고 Sharpness+1, Quick Sheathe/Punishing Draw 등이 자주 조합됨.'},
 ls:{type:'커뮤니티 정석',title:'MH4U Long Sword skills',url:'https://www.reddit.com/r/mh4u/comments/11y0igr/',note:'G급 태도는 Challenger+2를 중심으로 Sharpness+1 또는 Razor Sharp를 조합하는 방향이 반복 추천됨.'},
 sns:{type:'커뮤니티 정석',title:'MH4U Sword and Shield skills',url:'https://www.reddit.com/r/mh4u/comments/rim5d2/',note:'G급 한손검은 Honed Blade/Sharpness+1, Challenger+2, Razor Sharp, Weakness Exploit 등이 범용 핵심으로 언급됨.'},
 db:{type:'커뮤니티 기반',title:'MH4U blademaster skill consensus',url:'https://www.reddit.com/r/mh4u/comments/rim5d2/',note:'쌍검은 일반 검사 화력 스킬에 예리도 유지와 스태미나 편의 스킬을 더하는 방향으로 구성.'},
 hammer:{type:'커뮤니티 정석',title:'MH4U Hammer / Lance skill discussion',url:'https://www.reddit.com/r/mh4u/comments/rvvwuo/',note:'해머는 Weakness Exploit, Handicraft, Evasion, Attack, KO 등이 추천되며 G급에서는 예리도/화력 우선.'},
 hh:{type:'커뮤니티 정석',title:'MH4U Hunting Horn HR/G skill discussion',url:'https://www.reddit.com/r/mh4u/comments/143i544/',note:'피리명인과 Challenger+2/Sharpness+1 또는 Razor Sharp 조합이 반복 추천됨.'},
 lance:{type:'커뮤니티 정석',title:'MH4U Lance style discussion',url:'https://www.reddit.com/r/mh4u/comments/vusjpr/',note:'가드형과 회피형이 모두 쓰이며, 매치업에 따라 Guard+2 또는 Evasion을 넣고 예리도/화력 스킬을 병행.'},
 gl:{type:'커뮤니티 정석',title:'MH4U Gunlance progression',url:'https://www.reddit.com/r/mh4u/comments/c0tkxw/',note:'상위는 Razor Sharp/Artillery/Attack, G급은 Sharpness+1/Honed Blade, Razor Sharp, Challenger+2와 상황별 Guard/Evasion이 언급됨.'},
 sa:{type:'커뮤니티 정석',title:'MH4U Switch Axe HR skills',url:'https://www.reddit.com/r/mh4u/comments/1km37l8/',note:'상위 이후 Sharpness+1 + Challenger+2가 강한 범용 검사 조합으로 반복 언급됨.'},
 cb:{type:'커뮤니티 정석',title:'MH4U Charge Blade endgame builds',url:'https://www.reddit.com/r/mh4u/comments/137ze8a/',note:'Impact phial은 Artillery Novice가 효율적이며 Honed Blade/Challenger+2, Razor Sharp, Guard 계열을 조합.'},
 ig:{type:'커뮤니티 정석',title:'MH4U Insect Glaive armor discussion',url:'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71432544',note:'G급에서는 Seregios 계열을 거쳐 Star Knight가 범용 IG 세트로 널리 언급되며, Sharpness/Honed Blade/Challenger 계열이 핵심.'},
 lbg:{type:'커뮤니티 정석',title:'MH4U LBG low/high skill advice',url:'https://www.reddit.com/r/mh4u/comments/pfaf88/',note:'속사는 Bonus Shot + 주력 탄 강화가 기본이고 속성탄이면 해당 속성 강화, 이후 Challenger/회피거리 등을 추가.'},
 hbg:{type:'커뮤니티 정석',title:'MH4U HBG Pierce advice',url:'https://www.reddit.com/r/mh4u/comments/1vdfpk7/',note:'관통 HBG는 Pierce Up, Recoil 조절, Evade Extender가 핵심으로 반복 언급됨.'},
 bow:{type:'커뮤니티 정석',title:'MH4U Bow skill discussion',url:'https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/71716510',note:'연사활은 Focus + Normal/Rapid Up, 특정 활에서는 Load Up이 핵심으로 언급됨.'}
};
const profiles={
'대검':{source:'gs',note:'발도 차지 중심. 집중과 발도술【기술】을 우선.',low:{attack:['공격력UP【중】'],defense:['방어력UP【중】'],balance:['집중']},high:{attack:['집중','발도술【기술】'],defense:['집중','납도술'],balance:['집중','발도술【기술】']},g:[['발도 집중 정석',['집중','발도술【기술】','예리도레벨+1'],'커뮤니티 핵심스킬 기반'],['안정 발도',['집중','발도술【기술】','납도술'],'안정형'],['화력 집중',['집중','발도술【기술】','공격력UP【대】'],'화력형'],['커스텀 믹스',['집중','발도술【기술】','발도술【힘】'],'프로젝트 커스텀']]},
'태도':{source:'ls',note:'지속 화력과 예리도 유지 중심.',low:{attack:['공격력UP【중】'],defense:['회피성능+1'],balance:['숫돌사용고속화']},high:{attack:['예리도레벨+1','도전자+2'],defense:['예리','회피성능+1'],balance:['예리','도전자+1']},g:[['도전자 예리도',['도전자+2','예리도레벨+1'],'커뮤니티 정석'],['도전자 업물',['도전자+2','예리'],'커뮤니티 정석'],['약점 공략',['약점특효','예리도레벨+1'],'화력형'],['안정 사냥',['고급귀마개','예리도레벨+1'],'안정형']]},
'한손검':{source:'sns',note:'범용 검사 스킬과 상황 대응력이 강점.',low:{attack:['공격력UP【중】'],defense:['회피성능+1'],balance:['숫돌사용고속화']},high:{attack:['예리도레벨+1','도전자+2'],defense:['예리','회피성능+1'],balance:['예리','약점특효']},g:[['진타 기반',['명검'],'커뮤니티 정석'],['예리 약특',['예리','약점특효'],'커뮤니티 정석'],['예리도 도전자',['예리도레벨+1','도전자+2'],'화력형'],['귀마개 범용',['고급귀마개','예리'],'안정형']]},
'쌍검':{source:'db',note:'예리도 소모와 스태미나를 함께 관리.',low:{attack:['공격력UP【중】'],defense:['러너'],balance:['숫돌사용고속화']},high:{attack:['예리','도전자+1'],defense:['스태미나급속회복','회피성능+1'],balance:['예리','스태미나급속회복']},g:[['업물 도전자',['예리','도전자+2'],'커뮤니티 기반'],['예리도 스태미나',['예리도레벨+1','스태미나급속회복'],'지속전'],['약점 업물',['약점특효','예리'],'화력형'],['회피 지속전',['회피성능+2','스태미나급속회복'],'안정형']]},
'해머':{source:'hammer',note:'머리 약점 타격과 차지 운영 중심.',low:{attack:['공격력UP【중】'],defense:['회피성능+1'],balance:['KO술']},high:{attack:['예리도레벨+1','도전자+1'],defense:['회피성능+1'],balance:['약점특효','KO술']},g:[['약점 예리도',['약점특효','예리도레벨+1'],'커뮤니티 정석'],['도전자 화력',['도전자+2','예리도레벨+1'],'화력형'],['KO 안정형',['KO술','고급귀마개'],'안정형'],['회피 해머',['회피성능+2','예리도레벨+1'],'커스텀']]},
'수렵피리':{source:'hh',note:'피리명인을 유지하면서 공격 기회를 늘리는 구성.',low:{attack:['공격력UP【중】'],defense:['귀마개'],balance:['피리명인']},high:{attack:['피리명인','예리도레벨+1'],defense:['피리명인','고급귀마개'],balance:['피리명인','예리도레벨+1']},g:[['피리 도전자',['피리명인','도전자+2'],'커뮤니티 정석'],['피리 예리도',['피리명인','예리도레벨+1'],'커뮤니티 정석'],['피리 귀마개',['피리명인','고급귀마개'],'안정형'],['피리 약점',['피리명인','약점특효'],'커스텀']]},
'랜스':{source:'lance',note:'가드형과 회피형을 모두 지원.',low:{attack:['공격력UP【중】'],defense:['가드성능+1'],balance:['가드성능+1']},high:{attack:['예리도레벨+1','도전자+1'],defense:['가드성능+2'],balance:['가드성능+1','예리']},g:[['가드 랜스',['가드성능+2','예리도레벨+1'],'커뮤니티 정석'],['철벽 매치업',['가드성능+2','가드강화'],'상황특화'],['회피 랜스',['회피성능+3','회피거리UP'],'커뮤니티 플레이스타일'],['화력 랜스',['도전자+2','예리'],'화력형']]},
'건랜스':{source:'gl',note:'포격형/찌르기형에 따라 우선순위가 달라짐.',low:{attack:['포술사'],defense:['가드성능+1'],balance:['포술사']},high:{attack:['예리','포술사'],defense:['가드성능+1','포술사'],balance:['예리','포술사']},g:[['포격 기본',['포술사','예리'],'커뮤니티 정석'],['가드 포격',['포술사','가드성능+2'],'안정형'],['검격 화력',['도전자+2','예리도레벨+1'],'검격형'],['회피 건랜스',['회피성능+2','예리'],'커스텀']]},
'슬래시액스':{source:'sa',note:'검모드 화력과 회피 기동을 조합.',low:{attack:['공격력UP【중】'],defense:['회피성능+1'],balance:['숫돌사용고속화']},high:{attack:['예리도레벨+1','도전자+2'],defense:['회피성능+1','회피거리UP'],balance:['예리도레벨+1','회피성능+1']},g:[['도전자 예리도',['도전자+2','예리도레벨+1'],'커뮤니티 정석'],['업물 약특',['예리','약점특효'],'화력형'],['회피 기동',['회피성능+2','회피거리UP'],'안정형'],['귀마개 화력',['고급귀마개','예리도레벨+1'],'커스텀']]},
'차지액스':{source:'cb',note:'유탄병은 포술사 효율이 높고 가드포인트/화력을 선택.',low:{attack:['포술사'],defense:['가드성능+1'],balance:['포술사']},high:{attack:['포술사','도전자+1'],defense:['포술사','가드성능+1'],balance:['포술사','예리']},g:[['유탄 정석',['포술사','도전자+2','예리'],'커뮤니티 정석'],['유탄 도전자',['포술사','도전자+2'],'커뮤니티 기반'],['가드포인트',['포술사','가드성능+2'],'안정형'],['약점 유탄',['포술사','약점특효','예리'],'화력형']]},
'조충곤':{source:'ig',note:'탑승보다 종반에는 범용 검사 화력 스킬 가치가 높음.',low:{attack:['공격력UP【중】'],defense:['회피성능+1'],balance:['탑승명인']},high:{attack:['예리도레벨+1','도전자+2'],defense:['고급귀마개'],balance:['탑승마스터','예리']},g:[['스타나이트 계열',['도전자+2','예리'],'커뮤니티 정석'],['진타 기반',['명검'],'커뮤니티 기반'],['귀마개 범용',['고급귀마개','예리도레벨+1'],'안정형'],['탑승 특화',['탑승마스터','예리도레벨+1'],'무기 특화']]},
'라이트보우건':{source:'lbg',note:'속사 탄종에 맞는 탄 강화가 최우선.',low:{attack:['공격력UP【중】'],defense:['회피거리UP'],balance:['통상탄�연사살UP']},high:{attack:['통상탄�연사살UP','연발수+1'],defense:['회피거리UP'],balance:['통상탄�연사살UP','연발수+1']},g:[['통상 속사',['통상탄�연사살UP','연발수+1'],'커뮤니티 정석'],['속사 화력',['연발수+1','도전자+2'],'화력형'],['속사 기동',['연발수+1','회피거리UP'],'안정형'],['통상 약점',['통상탄�연사살UP','약점특효'],'커스텀']]},
'헤비보우건':{source:'hbg',note:'관통탄, 반동, 회피거리의 조합을 우선.',low:{attack:['관통탄�관통살UP'],defense:['회피거리UP'],balance:['관통탄�관통살UP']},high:{attack:['관통탄�관통살UP','반동경감+1'],defense:['회피거리UP','반동경감+1'],balance:['관통탄�관통살UP','회피거리UP']},g:[['관통 정석',['관통탄�관통살UP','반동경감+1','회피거리UP'],'커뮤니티 정석'],['관통 화력',['관통탄�관통살UP','도전자+2'],'화력형'],['관통 안정',['관통탄�관통살UP','회피거리UP'],'안정형'],['반동 대응',['반동경감+2','회피거리UP'],'탄종 특화']]},
'활':{source:'bow',note:'연사활 기준. 활 타입에 따라 탄 강화 교체 필요.',low:{attack:['공격력UP【중】'],defense:['러너'],balance:['집중']},high:{attack:['집중','통상탄�연사살UP'],defense:['집중','러너'],balance:['집중','장전수UP']},g:[['연사 3핵심',['집중','통상탄�연사살UP'],'커뮤니티 정석'],['연사 화력',['집중','도전자+2'],'화력형'],['스태미나 안정',['집중','스태미나급속회복'],'안정형'],['회피 연사',['집중','회피성능+1'],'커스텀']]}
};
function craftPenalty(build){let n=0;for(const a of build.armors||[]){const m=String(a.materials||'').match(rareRe);n+=m?m.length:0;}return n;}
function slimBuild(r){const dc={};for(const p of r.decorations||[]){const d=p.deco;if(!d)continue;if(!dc[d.id])dc[d.id]={id:d.id,name:d.name,slots:d.slots,count:0};dc[d.id].count++;}return {armors:(r.armors||[]).map(a=>({id:a.id,name:a.name,part:a.part,defense:a.defense,slots:a.slots,rank:a.rank,rare:a.rare||rareById.get(a.id)||0,materials:fullById.get(a.id)?.materials||a.materials||''})),decorations:Object.values(dc),defense:r.calc?.defense||0,resist:r.calc?.resist||{},activated:(r.calc?.activated||[]).filter(x=>x.threshold>0).map(x=>({skillId:x.skillId,name:x.name,points:x.points})),score:r.score||0,craftPenalty:craftPenalty(r)};}
function stageArmors(stage,hunter){return baseData.armors.filter(a=>(a.hunterType==='both'||a.hunterType===hunter)&&(stage==='low'?a.rank==='low':stage==='high'?(a.rank==='low'||a.rank==='high'):true));}
function stageDecorations(stage){return stage==='low'?decorations.filter(d=>d.rank==='low'):stage==='high'?decorations.filter(d=>d.rank==='low'||d.rank==='high'):decorations;}
async function solve(weaponType,stage,names,mode='balanced'){
 const hunter=gunner.has(weaponType)?'gunner':'blade'; let use=[...names], relaxed=[];
 while(use.length){
  const targets=use.map(n=>activationByName[n]).filter(Boolean); if(targets.length!==use.length) throw new Error(`missing activation ${weaponType}/${stage}: ${use.filter(n=>!activationByName[n])}`);
  const req=Object.fromEntries(targets.map(t=>[t.skillId,Number(t.points||10)])); const pool=stageArmors(stage,hunter); const armors=[];
  for(const part of ['head','body','arms','waist','legs']){const cand=pool.filter(a=>a.part===part).sort((a,b)=>{const score=x=>Object.keys(req).reduce((v,id)=>v+Math.max(0,Number(x.skills?.[id]||0))*5,0)+Number(x.slots||0)*1.7+Number(x.defense||0)*(mode==='defense'?.06:.02)+(x.torsoUp?7:0)-craftPenalty({armors:[x]})*(mode==='easy'?5:0);return score(b)-score(a);}).slice(0,16);armors.push(...cand);}
  const search=await searchBuilds({targetActivationIds:targets.map(x=>x.id),hunterType:hunter,rank:'all',charm:{skills:{},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit:6},{skills,armors,decorations:stageDecorations(stage)});
  const results=search.results||[]; if(results.length){let r=results[0];if(mode==='defense')r=[...results].sort((a,b)=>b.calc.defense-a.calc.defense||b.score-a.score)[0];if(mode==='easy')r=[...results].sort((a,b)=>craftPenalty(a)-craftPenalty(b)||b.calc.defense-a.calc.defense)[0];return {targets,build:slimBuild(r),relaxed};}
  if(use.length===1)break; relaxed.unshift(use.pop());
 }
 return null;
}
function srcFor(key){return SOURCES[key]||SOURCES.highbm;}
const out={generatedAt:new Date().toISOString(),method:'웹 커뮤니티/가이드에서 반복 확인되는 무기별 핵심 스킬을 기준으로 프로젝트 자동조합 엔진이 실제 방어구 조합을 검증. 호석 없음 · 무기 슬롯 0 기준. 커뮤니티의 정확한 장비 조합을 그대로 인용한 경우가 아니면 「커뮤니티 기반 커스텀」으로 표시.',progressionNote:'하위·상위는 지나가는 구간이므로 공격형/방어형/균형형 3종만 제공. G급은 최종 세팅 구간으로 무기별 4개 플레이스타일을 제공. 실제 최종 커스텀은 호석/무기 슬롯/상대 몬스터에 따라 달라질 수 있음.',weaponTypes:Object.keys(profiles),entries:[],sources:SOURCES};
const ONLY=(process.env.ONLY||'').split(',').filter(Boolean);
for(const [weaponType,p] of Object.entries(profiles)){
 if(ONLY.length&&!ONLY.includes(weaponType))continue;
 const hunter=gunner.has(weaponType)?'gunner':'blade';
 for(const stage of ['low','high']){
  const variants=[];
  for(const [key,label,mode] of [['attack','공격형','balanced'],['defense','방어형','defense'],['balance','균형형','easy']]){
   const solved=await solve(weaponType,stage,p[stage][key],mode);if(!solved)continue;
   const source=stage==='low'?SOURCES.low:(weaponType==='대검'?SOURCES.gs:SOURCES.highbm);
   variants.push({label,category:key,description:key==='attack'?'화력 스킬을 우선한 진행용 세팅':key==='defense'?'생존/가드/회피를 우선한 진행용 세팅':'제작 난이도와 무기 핵심 스킬을 절충한 진행용 세팅',targets:solved.targets,build:solved.build,source,relaxed:solved.relaxed});
  }
  out.entries.push({weaponType,rank:stage,rankLabel:stage==='low'?'하위':'상위',hunterType:hunter,summary:p.note,variants});
 }
 const gvars=[];const source=srcFor(p.source);
 for(const [label,names,kind] of p.g){const mode=kind==='안정형'?'defense':kind==='프로젝트 커스텀'||kind==='커스텀'?'easy':'balanced';const solved=await solve(weaponType,'g',names,mode);if(!solved)continue;gvars.push({label,category:kind,description:`${kind} · ${names.join(' + ')}`,targets:solved.targets,build:solved.build,source:{...source,type:kind.includes('커뮤니티')?source.type:'커뮤니티 근거 + 프로젝트 계산'},relaxed:solved.relaxed});}
 out.entries.push({weaponType,rank:'g',rankLabel:'G급',hunterType:hunter,summary:p.note,variants:gvars});
}
fs.writeFileSync(new URL(process.env.OUT||'../data/recommended_loadouts.json',import.meta.url),JSON.stringify(out,null,2));
console.log(`entries=${out.entries.length}, variants=${out.entries.reduce((n,e)=>n+e.variants.length,0)}`);
for(const e of out.entries)if(e.variants.length<(e.rank==='g'?3:3))console.log('LOW_VARIANTS',e.weaponType,e.rank,e.variants.length);
