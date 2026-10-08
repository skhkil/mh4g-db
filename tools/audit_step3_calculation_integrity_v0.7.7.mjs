import fs from 'fs';
import {calculateBuild,searchBuilds} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const data={skills:read('./data/skills.json'),armors:read('./data/sim_armors.json'),decorations:read('./data/decorations.json')};
const checks={};const errors=[];
const expect=(k,v,d='')=>{checks[k]=!!v;if(!v)errors.push(`${k}${d?': '+d:''}`)};
// Synthetic torso-up arithmetic, including body decoration multiplication and negative activation.
const synSkills=[
 {id:'s',name:'테스트',activations:[{id:'s10',name:'테스트+1',points:10},{id:'s15',name:'테스트+2',points:15}]},
 {id:'n',name:'패널티',activations:[{id:'n-10',name:'패널티 발동',points:-10}]}
];
const body={id:'b',part:'body',skills:{s:4,n:-2},slots:3,defense:10,resistances:{fire:1,water:0,thunder:0,ice:0,dragon:0}};
const head={id:'h',part:'head',skills:{},torsoUp:true,slots:0,defense:5,resistances:{fire:0,water:1,thunder:0,ice:0,dragon:0}};
const arms={id:'a',part:'arms',skills:{},torsoUp:true,slots:0,defense:5,resistances:{fire:0,water:0,thunder:1,ice:0,dragon:0}};
const deco={id:'d',name:'테스트주',slots:1,skills:{s:2,n:-2}};
let c=calculateBuild({armors:[body,head,arms],charm:{skills:{s:1},slots:0},decorations:[{deco,container:'body'}]}, {skills:synSkills,decorations:[deco]}, true);
expect('torso_count_2',c.torsoUpCount===2,JSON.stringify(c));
expect('body_skill_multiplied',c.points.s===19,`s=${c.points.s}`); // 4*3 + charm1 + deco2*3
expect('body_negative_multiplied',c.points.n===-12,`n=${c.points.n}`);
expect('negative_activation_detected',c.activated.some(x=>x.name==='패널티 발동'),JSON.stringify(c.activated));
expect('defense_sum',c.defense===20,`def=${c.defense}`);
expect('resistance_sum',c.resist.fire===1&&c.resist.water===1&&c.resist.thunder===1,JSON.stringify(c.resist));
c=calculateBuild({armors:[body,head,arms],charm:{skills:{s:1},slots:0},decorations:[{deco,container:'body'}]}, {skills:synSkills,decorations:[deco]}, false);
expect('torso_disabled_count_0',c.torsoUpCount===0,JSON.stringify(c));
expect('torso_disabled_points',c.points.s===7&&c.points.n===-4,JSON.stringify(c.points));

const activation=name=>{for(const s of data.skills)for(const a of s.activations||[])if(a.name===name)return {activationId:a.id,skillId:s.id,need:Number(a.points)};throw new Error('missing '+name)};
const scenarios=[
 ['고급귀마개'],
 ['예리도레벨+1'],
 ['고급귀마개','숫돌사용고속화'],
 ['고급귀마개','통찰력+1'],
 ['세균연구가','명검']
];
const scenarioResults=[];
for(const names of scenarios){
 const defs=names.map(activation);
 const r=await searchBuilds({targetActivationIds:defs.map(x=>x.activationId),hunterType:'blade',rank:'g',charm:{skills:{},slots:0},weaponSlots:3,allowDecorations:true,includeTorsoUp:true,limit:5,timeBudgetMs:7000},data);
 const exact=r.results||[];
 expect(`scenario_${names.join('+')}_has_result`,exact.length>0,JSON.stringify(r.stats));
 for(const [i,b] of exact.entries()){
   for(const d of defs)expect(`scenario_${names.join('+')}_${i}_${d.skillId}_meets`,Number(b.calc?.points?.[d.skillId]||0)>=d.need,`have=${b.calc?.points?.[d.skillId]||0} need=${d.need}`);
   const capacity={weapon:3,charm:0};for(const a of b.armors)capacity[a.part]=Number(a.slots||0);
   const used={};for(const p of b.decorations||[]){const id=p.container;used[id]=(used[id]||0)+Number(p.deco?.slots||0)}
   expect(`scenario_${names.join('+')}_${i}_slot_capacity`,Object.entries(used).every(([id,n])=>n<=Number(capacity[id]||0)),JSON.stringify({used,capacity}));
   expect(`scenario_${names.join('+')}_${i}_metrics_slots`,Number(b.metrics?.remainingSlots)>=0,JSON.stringify(b.metrics));
 }
 scenarioResults.push({names,stats:r.stats,top:exact[0]?{armors:exact[0].armors.map(a=>a.name),points:Object.fromEntries(defs.map(d=>[d.skillId,exact[0].calc.points[d.skillId]||0])),metrics:exact[0].metrics}:null});
}

// Resource-satisfied target regression: when charm/relic points already satisfy the target,
// armor generation must not keep chasing the same skill and introduce avoidable negative activations.
const edgemaster=activation('명검');
const satisfied=await searchBuilds({targetActivationIds:[edgemaster.activationId],hunterType:'blade',rank:'g',charm:{skills:{[edgemaster.skillId]:10},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit:5,timeBudgetMs:7000},data);
expect('resource_satisfied_has_result',satisfied.results.length>0,JSON.stringify(satisfied.stats));
expect('resource_satisfied_top_no_negative',(satisfied.results[0]?.metrics?.negativeSkillCount||0)===0,JSON.stringify(satisfied.results[0]?.metrics||{}));
expect('resource_satisfied_target_exact',Number(satisfied.results[0]?.calc?.points?.[edgemaster.skillId]||0)===10,`have=${satisfied.results[0]?.calc?.points?.[edgemaster.skillId]}`);

const report={ok:errors.length===0,version:'0.7.7-step3-calculation-integrity-2',checks,errors,scenarioResults};
fs.writeFileSync('./tools/step3_calculation_integrity_audit_v0.7.7.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));process.exit(report.ok?0:1);
