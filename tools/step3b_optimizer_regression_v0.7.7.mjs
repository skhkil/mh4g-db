import fs from 'fs';
import {searchBuilds} from '../js/engine.js';
const read=n=>JSON.parse(fs.readFileSync(new URL('../data/'+n,import.meta.url),'utf8'));
const real={armors:read('sim_armors.json'),skills:read('skills.json'),decorations:read('decorations.json')};
const activ=(name)=>real.skills.flatMap(s=>(s.activations||[]).map(a=>({skillId:s.id,...a}))).find(a=>a.name===name);
const targetNames=['심안','약점특효','회피성능+3','공격력UP【소】','예리도레벨+1'];
const targetIds=targetNames.map(n=>activ(n).id);
const evadeSkill=real.skills.find(s=>s.name==='회피성능').id;
const ukauNames=['우캄루X사쿠파케','카이저X메일','우캄루X사쿰페','카이저X펄드','우캄루X케마르'];
const ukau=await searchBuilds({targetActivationIds:targetIds,hunterType:'blade',rank:'g',charm:{skills:{[evadeSkill]:5},slots:3},weaponSlots:2,allowDecorations:true,includeTorsoUp:true,limit:10,timeBudgetMs:20000},real);
const match=ukau.results.find(r=>ukauNames.every((n,i)=>(r.armors[i]?.name_ko||r.armors[i]?.name)===n));
if(!match)throw new Error('우카우카우 exact 조합 미발견');
const active=new Set(match.calc.activated.map(a=>a.name));
for(const n of targetNames)if(!active.has(n))throw new Error('목표 미발동: '+n);
if(!active.has('내진'))throw new Error('잔여 슬롯 추가 스킬 내진 미발동');
if((match.metrics?.remainingSlots??-1)<1)throw new Error('우카우카우 잔여 1슬롯 미확보');

// 4스킬 요청에서도 우카우카우를 보존하고, 남는 슬롯으로 공격소+내진까지 완성해야 한다.
const target4Names=['심안','약점특효','회피성능+3','예리도레벨+1'];
const target4Ids=target4Names.map(n=>activ(n).id);
const ukau4=await searchBuilds({targetActivationIds:target4Ids,hunterType:'blade',rank:'g',charm:{skills:{[evadeSkill]:5},slots:3},weaponSlots:2,allowDecorations:true,includeTorsoUp:true,limit:10,timeBudgetMs:20000},real);
const match4=ukau4.results.find(r=>ukauNames.every((n,i)=>(r.armors[i]?.name_ko||r.armors[i]?.name)===n));
if(!match4)throw new Error('4스킬 우카우카우 exact 조합 미발견');
const active4=new Set(match4.calc.activated.map(a=>a.name));
for(const n of target4Names)if(!active4.has(n))throw new Error('4스킬 목표 미발동: '+n);
for(const n of ['공격력UP【소】','내진'])if(!active4.has(n))throw new Error('4스킬 잔여 슬롯 추가 스킬 미발동: '+n);
if(Number(match4.calc.points?.[evadeSkill]||0)!==20)throw new Error('회피성능+3 과투자 제거 실패: '+match4.calc.points?.[evadeSkill]);
if((match4.metrics?.remainingSlots??-1)<1)throw new Error('4스킬 우카우카우 잔여 1슬롯 미확보');
if(!match4.decorations.some(p=>(p.deco?.name||p.deco?.name_ko)==='공격주【3】'))throw new Error('3슬롯 공격주 보존 실패');

// synthetic: 1슬롯이면 추가 긍정 스킬을 먼저 완성하고, 2슬롯이면 그 뒤 디메리트까지 해제해야 한다.
const skills=[
 {id:'t',name:'목표',activations:[{id:'ta',name:'목표발동',points:10}]},
 {id:'x',name:'추가',activations:[{id:'xa',name:'추가발동',points:10}]},
 {id:'n',name:'패널티',activations:[{id:'na',name:'패널티발동',points:-10}]}
];
const mkArmor=(part,slots=0)=>({id:'a_'+part,part,name_ko:part,hunterType:'blade',rank:'g',slots,defense:1,resist:{fire:0,water:0,thunder:0,ice:0,dragon:0},skills:part==='head'?{t:10,x:8,n:-10}:{}});
const armors=['head','body','arms','waist','legs'].map((p,i)=>mkArmor(p,i===0?0:0));
const decorations=[
 {id:'dx',name_ko:'추가주',slots:1,skills:{x:2}},
 {id:'dn',name_ko:'상쇄주',slots:1,skills:{n:1}}
];
const data={armors,skills,decorations};
for(const ws of [1,2]){
 const res=await searchBuilds({targetActivationIds:['ta'],hunterType:'blade',rank:'g',charm:{skills:{},slots:0},weaponSlots:ws,allowDecorations:true,includeTorsoUp:true,limit:3,timeBudgetMs:3000},data);
 if(!res.results.length)throw new Error('synthetic 결과 없음 '+ws);
 const names=new Set(res.results[0].calc.activated.map(a=>a.name));
 if(!names.has('추가발동'))throw new Error('추가 스킬 우선 실패 '+ws);
 if(ws===1 && !names.has('패널티발동'))throw new Error('1슬롯에서 추가스킬보다 패널티 제거가 우선됨');
 if(ws===2 && names.has('패널티발동'))throw new Error('잔여 슬롯으로 패널티 제거 실패');
}
const report={ok:true,ukau:{stats:ukau.stats,armors:match.armors.map(a=>a.name_ko||a.name),activated:[...active],decorations:match.decorations.map(p=>p.deco.name_ko||p.deco.name),metrics:match.metrics},ukau4:{stats:ukau4.stats,armors:match4.armors.map(a=>a.name_ko||a.name),activated:[...active4],evadePoints:match4.calc.points?.[evadeSkill],decorations:match4.decorations.map(p=>p.deco.name_ko||p.deco.name),metrics:match4.metrics},synthetic:{oneSlot:'extra skill first',twoSlots:'extra skill + negative cleanup'}};
fs.writeFileSync(new URL('./step3b_optimizer_regression_v0.7.7.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
