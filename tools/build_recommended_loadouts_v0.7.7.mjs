// LEGACY ONLY: this file uses the automatic combination engine and must not overwrite the verified recommendation DB.
if(process.env.LEGACY_AUTOGEN !== "1"){
  console.error("This legacy auto-generator is disabled. Use: python tools/rebuild_recommendations_verified_v0.7.7.py");
  process.exit(2);
}
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
 low:{type:'국내 진행 참고',title:'몬헌4 장비 선택 조언',url:'https://www.inven.co.kr/board/mhf/1755/8390',note:'하위 재기/카브라 계열과 상위 카브라S 이후 커스텀 전환에 대한 국내 진행 조언.'},
 highbm:{type:'국내 진행 참고',title:'몬헌4 장비 선택 조언',url:'https://www.inven.co.kr/board/mhf/1755/8390',note:'상위 초반 카브라S 계열을 거친 뒤 무기와 취향에 맞는 커스텀으로 전환하는 국내 진행 조언.'},
 gs:{type:'국내 4G 참고',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'G3 대검용 예리도+1·집중·발도술 계열 세팅이 국내 4G 게시물에 정리되어 있음.'},
 ls:{type:'국내 4G 참고',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'검사 범용 G급 세팅과 국내 4G 장비 자료를 참고.'},
 sns:{type:'국내 4G 참고',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'검사 범용 G급 세팅과 국내 4G 장비 자료를 참고.'},
 db:{type:'국내 4G 참고',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'검사 범용 G급 세팅과 국내 4G 장비 자료를 참고.'},
 hammer:{type:'국내 4G 참고',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'검사 범용 G급 세팅과 국내 4G 장비 자료를 참고.'},
 hh:{type:'국내 4G 참고',title:'초보의 무기 선택시 팁',url:'https://www.inven.co.kr/board/mhf/3746/159',note:'무기 특성과 G급 범용 검사 장비 방향을 국내 자료와 함께 참고.'},
 lance:{type:'국내 4G 세트',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'자자미X/보로스X 및 G2 가드성능+2·예리도+1 랜스 세팅이 정리되어 있음.'},
 gl:{type:'국내 4G 세트',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'가드성능+2·업물·포술마스터 건랜스 세팅이 정리되어 있음.'},
 sa:{type:'국내 4G 참고',title:'초보의 무기 선택시 팁',url:'https://www.inven.co.kr/board/mhf/3746/166',note:'무기 특성과 G급 범용 검사 장비 방향을 국내 자료와 함께 참고.'},
 cb:{type:'국내 4G 참고',title:'초보의 무기 선택시 팁',url:'https://www.inven.co.kr/board/mhf/3746/166',note:'차지액스 특성과 G급 검사 장비 방향을 국내 자료와 함께 참고.'},
 ig:{type:'국내 4G 참고',title:'[4G] 조충곤 엽충 육성',url:'https://www.inven.co.kr/board/mhf/3746/314',note:'4G 조충곤 진액효과연장 엽충과 운용 관련 국내 자료.'},
 lbg:{type:'국내 4G 참고',title:'초보의 무기 선택시 팁',url:'https://www.inven.co.kr/board/mhf/3746/166',note:'라이트보우건 탄종/속사 운용 관련 국내 자료.'},
 hbg:{type:'국내 4G 세트',title:'[4G] G급 추천 방어구',url:'https://www.inven.co.kr/board/mhf/3746/393',note:'G1 자자미Z 관통 헤보 세팅이 국내 4G 게시물에 정리되어 있음.'},
 bow:{type:'국내 4G 참고',title:'초보의 무기 선택시 팁',url:'https://www.inven.co.kr/board/mhf/3746/166',note:'원거리 무기 운용과 장비 방향을 국내 자료와 함께 참고.'}
}
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

const skillById=new Map(skills.map(x=>[x.id,x]));
function activatedFromPoints(points={}){
  const out=[];
  for(const [skillId,valueRaw] of Object.entries(points||{})){
    const value=Number(valueRaw||0), def=skillById.get(skillId); if(!def)continue;
    const pos=(def.activations||[]).filter(a=>Number(a.points)>0&&Number(a.points)<=value).sort((a,b)=>Number(b.points)-Number(a.points))[0];
    if(pos)out.push({skillId,name:pos.name,points:value});
  }
  return out.sort((a,b)=>a.name.localeCompare(b.name,'ko'));
}
function setBuild(set){
  const armors=(set.pieces||[]).map(p=>fullById.get(p.id)).filter(Boolean).map(a=>({id:a.id,name:a.name,part:a.part,defense:a.defense,slots:a.slots,rank:a.rank,rare:a.rare||0,materials:a.materials||''}));
  return {armors,decorations:[],decorationPlacements:[],defense:Number(set.defense||0),resist:set.resistances||{},activated:activatedFromPoints(set.skills||{}),score:0,craftPenalty:craftPenalty({armors})};
}
function setScore(set,targetNames,mode){
  const targets=targetNames.map(n=>activationByName[n]).filter(Boolean);
  let score=0;
  for(const t of targets){const p=Number(set.skills?.[t.skillId]||0);score+=Math.min(1,Math.max(0,p)/Math.max(1,t.points))*85;}
  const positive=activatedFromPoints(set.skills||{}).length;
  score+=positive*10+Number(set.slots||0)*(mode==='balance'?2:1);
  if(mode==='defense')score+=Number(set.defense||0)*.45+Object.values(set.resistances||{}).reduce((a,b)=>a+Math.max(0,Number(b||0)),0)*.8;
  else if(mode==='attack')score+=Number(set.defense||0)*.08;
  else score+=Number(set.defense||0)*.2;
  const negative=Object.entries(set.skills||{}).filter(([id,v])=>Number(v)<=-10).length;score-=negative*20;
  return score;
}
function recommendFullSet(weaponType,stage,targetNames,mode){
  const hunter=gunner.has(weaponType)?'gunner':'blade';
  const pool=read('data/armor_sets.json').filter(s=>(s.hunterType==='both'||s.hunterType===hunter)&&s.rank===stage&&Array.isArray(s.pieces)&&s.pieces.length===5);
  return pool.sort((a,b)=>setScore(b,targetNames,mode)-setScore(a,targetNames,mode))[0]||null;
}
function craftPenalty(build){let n=0;for(const a of build.armors||[]){const m=String(a.materials||'').match(rareRe);n+=m?m.length:0;}return n;}
function slimBuild(r){const dc={};for(const p of r.decorations||[]){const d=p.deco;if(!d)continue;if(!dc[d.id])dc[d.id]={id:d.id,name:d.name,slots:d.slots,count:0};dc[d.id].count++;}return {armors:(r.armors||[]).map(a=>({id:a.id,name:a.name,part:a.part,defense:a.defense,slots:a.slots,rank:a.rank,rare:a.rare||rareById.get(a.id)||0,materials:fullById.get(a.id)?.materials||a.materials||''})),decorations:Object.values(dc),decorationPlacements:(r.decorations||[]).map(p=>({id:p.deco?.id,name:p.deco?.name,slots:Number(p.deco?.slots||0),container:p.container})).filter(x=>x.id&&x.container),defense:r.calc?.defense||0,resist:r.calc?.resist||{},activated:(r.calc?.activated||[]).filter(x=>x.threshold>0).map(x=>({skillId:x.skillId,name:x.name,points:x.points})),score:r.score||0,craftPenalty:craftPenalty(r)};}
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
const out={generatedAt:new Date().toISOString(),method:'국내 MH4/4G 커뮤니티 자료와 프로젝트 DB를 기준으로 구성.',progressionNote:'',weaponTypes:Object.keys(profiles),entries:[],sources:SOURCES};
const ONLY=(process.env.ONLY||'').split(',').filter(Boolean);
for(const [weaponType,p] of Object.entries(profiles)){
 if(ONLY.length&&!ONLY.includes(weaponType))continue;
 const hunter=gunner.has(weaponType)?'gunner':'blade';
 for(const stage of ['low','high']){
  const variants=[];
  const source=stage==='low'?SOURCES.low:SOURCES.highbm;
  for(const [key,label,mode,setMode] of [['attack','공격형','balanced','attack'],['defense','방어형','defense','defense'],['balance','균형형','easy','balance']]){
    const targetNames=p[stage][key];
    const set=recommendFullSet(weaponType,stage,targetNames,setMode);
    if(set){
      const targets=targetNames.map(n=>activationByName[n]).filter(Boolean);
      variants.push({label:`${label} 세트`,group:'set',category:key,description:'',targets,build:setBuild(set),source,relaxed:[],setName:set.name});
    }
  }
  for(const [key,label,mode] of [['attack','공격형','balanced'],['defense','방어형','defense'],['balance','균형형','easy']]){
    const solved=await solve(weaponType,stage,p[stage][key],mode);if(!solved)continue;
    variants.push({label:`${label} 커스텀`,group:'custom',category:key,description:'',targets:solved.targets,build:solved.build,source:{type:'프로젝트 커스텀',title:'',url:'',note:''},relaxed:solved.relaxed});
  }
  out.entries.push({weaponType,rank:stage,rankLabel:stage==='low'?'하위':'상위',hunterType:hunter,summary:p.note,variants});
 }
 const gvars=[];const source=srcFor(p.source);
 for(const [label,names,kind] of p.g){const mode=kind==='안정형'?'defense':kind==='프로젝트 커스텀'||kind==='커스텀'?'easy':'balanced';const solved=await solve(weaponType,'g',names,mode);if(!solved)continue;gvars.push({label,group:'g',category:kind,description:'',targets:solved.targets,build:solved.build,source:kind.includes('커뮤니티')?source:{type:'프로젝트 커스텀',title:'',url:'',note:''},relaxed:solved.relaxed});}
 out.entries.push({weaponType,rank:'g',rankLabel:'G급',hunterType:hunter,summary:p.note,variants:gvars});
}
fs.writeFileSync(new URL(process.env.OUT||'../data/recommended_loadouts.json',import.meta.url),JSON.stringify(out,null,2));
console.log(`entries=${out.entries.length}, variants=${out.entries.reduce((n,e)=>n+e.variants.length,0)}`);
for(const e of out.entries)if(e.variants.length<(e.rank==='g'?3:3))console.log('LOW_VARIANTS',e.weaponType,e.rank,e.variants.length);
