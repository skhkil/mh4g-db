import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {searchBuilds} from '../js/engine.js';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=n=>JSON.parse(fs.readFileSync(path.join(ROOT,'data',n),'utf8'));
const data={skills:read('skills.json'),armors:read('sim_armors.json'),decorations:read('decorations.json')};
const relic=read('relic_weapon_decorations.json');
const PARTS=['head','body','arms','waist','legs'];
function actByName(name){for(const s of data.skills)for(const a of (s.activations||[]))if(a.name===name)return {skill:s,act:a};return null}
const requested=['고급귀마개','회피성능+2','예리도레벨+1','공격력UP【대】','장전수UP','통찰력+2','업물','집중'];
const available=requested.map(actByName).filter(Boolean);
if(available.length<4)throw new Error('not enough target activations: '+available.map(x=>x?.act?.name));
function add(dst,src,m=1){for(const [k,v] of Object.entries(src||{}))dst[k]=(dst[k]||0)+Number(v||0)*m}
function independentCalc(build,charm,weaponSlots,includeTorsoUp){
  const pts={}; const body=build.armors.find(a=>a?.part==='body'); const others=build.armors.filter(a=>a&&a.part!=='body');
  const torso=includeTorsoUp?others.filter(a=>a.torsoUp).length:0;
  for(const a of others)add(pts,a.skills,1);
  if(body)add(pts,body.skills,1+torso);
  add(pts,charm?.skills,1);
  for(const p of build.decorations||[]){const d=typeof p.deco==='string'?data.decorations.find(x=>x.id===p.deco):p.deco;if(d)add(pts,d.skills,p.container==='body'?(1+torso):1)}
  const defense=build.armors.reduce((s,a)=>s+Number(a?.defense||0),0);
  const resist={fire:0,water:0,thunder:0,ice:0,dragon:0}; for(const a of build.armors)for(const k in resist)resist[k]+=Number(a?.resistances?.[k]||0);
  return {pts,defense,resist,torso};
}
function sameMap(a,b){const ks=new Set([...Object.keys(a||{}),...Object.keys(b||{})]);for(const k of ks)if(Number(a?.[k]||0)!==Number(b?.[k]||0))return false;return true}
const scenarios=[];
for(const hunterType of ['blade','gunner'])for(let ws=0;ws<=3;ws++)scenarios.push({name:`${hunterType}-crafted-${ws}`,hunterType,rank:'g',weaponSlots:ws,includeTorsoUp:true,allowDecorations:true,charm:{skills:{},slots:0}});
for(const hunterType of ['blade','gunner'])for(const rank of ['low','high'])for(const ws of [0,3])scenarios.push({name:`${hunterType}-${rank}-${ws}`,hunterType,rank,weaponSlots:ws,includeTorsoUp:true,allowDecorations:true,charm:{skills:{},slots:0}});
for(const hunterType of ['blade','gunner'])scenarios.push({name:`${hunterType}-torso-off`,hunterType,rank:'g',weaponSlots:2,includeTorsoUp:false,allowDecorations:true,charm:{skills:{},slots:0}});
for(const hunterType of ['blade','gunner'])scenarios.push({name:`${hunterType}-no-deco`,hunterType,rank:'g',weaponSlots:3,includeTorsoUp:true,allowDecorations:false,charm:{skills:{},slots:0}});
// owned charm-like scenarios
for(const hunterType of ['blade','gunner']){const t=available[0];scenarios.push({name:`${hunterType}-owned-charm`,hunterType,rank:'g',weaponSlots:1,includeTorsoUp:true,allowDecorations:true,charm:{skills:{[t.skill.id]:5},slots:2}})}
// owned relic-like scenarios: relic fixed skill is combined into resource and normal weapon slots are zero.
const relic3=relic.find(d=>Number(d.slots)===3)||relic[0];
for(const hunterType of ['blade','gunner'])scenarios.push({name:`${hunterType}-owned-relic`,hunterType,rank:'g',weaponSlots:0,includeTorsoUp:true,allowDecorations:true,charm:{skills:{...(relic3?.skills||{})},slots:0},relicId:relic3?.id});
let checks=0, failures=[], completed=0, nearChecked=0;
for(let i=0;i<scenarios.length;i++){
  const sc=scenarios[i]; const target=available[i%available.length];
  const r=await searchBuilds({targetActivationIds:[target.act.id],hunterType:sc.hunterType,rank:sc.rank||'g',charm:sc.charm,weaponSlots:sc.weaponSlots,allowDecorations:sc.allowDecorations,includeTorsoUp:sc.includeTorsoUp,limit:3,timeBudgetMs:2500},data);
  const rows=[...(r.results||[]),...(r.nearMisses||[])]; if((r.results||[]).length)completed++;
  for(const b of rows){
    const ind=independentCalc(b,sc.charm,sc.weaponSlots,sc.includeTorsoUp); checks++;
    if(!sameMap(ind.pts,b.calc?.points))failures.push({scenario:sc.name,target:target.act.name,kind:'points',expected:ind.pts,actual:b.calc?.points});
    if(ind.defense!==Number(b.calc?.defense||0))failures.push({scenario:sc.name,target:target.act.name,kind:'defense',expected:ind.defense,actual:b.calc?.defense});
    if(!sameMap(ind.resist,b.calc?.resist))failures.push({scenario:sc.name,target:target.act.name,kind:'resist',expected:ind.resist,actual:b.calc?.resist});
    if(ind.torso!==Number(b.calc?.torsoUpCount||0))failures.push({scenario:sc.name,target:target.act.name,kind:'torso',expected:ind.torso,actual:b.calc?.torsoUpCount});
    if((r.nearMisses||[]).includes(b))nearChecked++;
  }
  for(const b of r.results||[]){const have=Number(b.calc?.points?.[target.skill.id]||0),need=Number(target.act.points);if(have<need)failures.push({scenario:sc.name,target:target.act.name,kind:'solver_target_not_met',have,need});}
}
const out={version:'0.7.7-finalize-step3',scenarioCount:scenarios.length,scenarios,calculationRowsChecked:checks,completedScenarioCount:completed,nearMissRowsChecked:nearChecked,relicSample:{id:relic3?.id,slots:relic3?.slots,skills:relic3?.skills},failureCount:failures.length,failures};
fs.writeFileSync(path.join(ROOT,'data','simulator_consistency_audit_final_v0.7.7.json'),JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({scenarioCount:out.scenarioCount,calculationRowsChecked:checks,completedScenarioCount:completed,nearMissRowsChecked:nearChecked,failureCount:failures.length},null,2));
if(failures.length)process.exit(1);
