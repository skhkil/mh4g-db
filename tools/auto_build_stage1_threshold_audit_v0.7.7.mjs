import fs from 'fs';
import {searchBuilds} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(new URL(`../${p}`,import.meta.url),'utf8'));
const data={armors:read('data/sim_armors.json'),decorations:read('data/decorations.json'),skills:read('data/skills.json')};
const findActivation=name=>{for(const s of data.skills){const a=(s.activations||[]).find(x=>x.name===name);if(a)return {skill:s,activation:a};}throw new Error(`activation missing: ${name}`)};
const search=async names=>searchBuilds({targetActivationIds:names.map(n=>findActivation(n).activation.id),hunterType:'blade',rank:'g',charm:{skills:{},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit:5},data);
const hg=findActivation('고급귀마개');
const evade2=findActivation('회피성능+2');
const solo=await search(['고급귀마개']);
const mixed=await search(['고급귀마개','회피성능+3']);
const upgrade=await search(['회피성능+2']);
const checks={
  hg_exact_threshold_top5:solo.results.length===5&&solo.results.every(b=>Number(b.calc.points[hg.skill.id]||0)===15&&Number(b.metrics.targetWastePoints||0)===0),
  mixed_hg_not_overinvested:mixed.results.length>0&&mixed.results.every(b=>Number(b.calc.points[hg.skill.id]||0)===15),
  actual_upper_activation_is_valid:upgrade.results.length>0&&upgrade.results.every(b=>Number(b.calc.points[evade2.skill.id]||0)>=20&&Number(b.metrics.targetUpgradeSteps||0)>=1&&Number(b.metrics.targetWastePoints||0)===0)
};
const report={ok:Object.values(checks).every(Boolean),version:'0.7.7-stage1-threshold-efficiency',checks,soloTop:solo.results.map(b=>({points:b.calc.points[hg.skill.id],waste:b.metrics.targetWastePoints,remainingSlots:b.metrics.remainingSlots,armors:b.armors.map(a=>a.name)})),mixedTop:mixed.results.map(b=>({hearing:b.calc.points[hg.skill.id],waste:b.metrics.targetWastePoints,remainingSlots:b.metrics.remainingSlots})),upperActivationTop:upgrade.results.map(b=>({evade:b.calc.points[evade2.skill.id],waste:b.metrics.targetWastePoints,upgradeSteps:b.metrics.targetUpgradeSteps}))};
fs.writeFileSync(new URL('./auto_build_stage1_threshold_audit_v0.7.7.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
process.exit(report.ok?0:1);
