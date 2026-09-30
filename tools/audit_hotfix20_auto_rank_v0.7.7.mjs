import fs from 'fs';
import {searchBuilds} from '../js/engine.js';

const read=(p)=>JSON.parse(fs.readFileSync(new URL(`../${p}`,import.meta.url),'utf8'));
const data={armors:read('data/sim_armors.json'),decorations:read('data/decorations.json'),skills:read('data/skills.json')};
const findActivation=(name)=>{
  for(const s of data.skills){
    const a=(s.activations||[]).find(x=>x.name===name);
    if(a)return {skillId:s.id,activationId:a.id,need:Number(a.points)};
  }
  throw new Error(`activation missing: ${name}`);
};
const attack=findActivation('공격력UP【소】');
const bacteria=findActivation('세균연구가');
const mastersTouch=findActivation('명검');
const allowed={low:new Set(['low']),high:new Set(['low','high']),g:new Set(['low','high','g'])};
const failures=[];
const checks={};
const check=(name,ok,detail='')=>{checks[name]=!!ok;if(!ok)failures.push(`${name}${detail?`: ${detail}`:''}`)};

async function run(ids,rank,limit=12){
  return await searchBuilds({targetActivationIds:ids,hunterType:'blade',rank,charm:{skills:{},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit},data);
}

const low=await run([attack.activationId],'low',8);
check('low_progression_has_results',low.results.length>0,`count=${low.results.length}`);
check('low_progression_only_low',low.results.every(b=>b.armors.every(a=>allowed.low.has(a.rank))));
check('low_target_fully_activated',low.results.every(b=>Number(b.calc?.points?.[attack.skillId]||0)>=attack.need));

const high=await run([bacteria.activationId,mastersTouch.activationId],'high',12);
check('high_progression_has_results',high.results.length>0,`count=${high.results.length}`);
check('high_progression_no_g',high.results.every(b=>b.armors.every(a=>allowed.high.has(a.rank))));
check('high_targets_fully_activated',high.results.every(b=>Number(b.calc?.points?.[bacteria.skillId]||0)>=bacteria.need&&Number(b.calc?.points?.[mastersTouch.skillId]||0)>=mastersTouch.need));

const g=await run([bacteria.activationId,mastersTouch.activationId],'g',20);
check('g_progression_has_results',g.results.length>0,`count=${g.results.length}`);
check('g_targets_fully_activated',g.results.every(b=>Number(b.calc?.points?.[bacteria.skillId]||0)>=bacteria.need&&Number(b.calc?.points?.[mastersTouch.skillId]||0)>=mastersTouch.need));
check('g_top_prefers_current_rank',g.results.length>0&&g.results[0].metrics?.rankMaxDowngrade===0&&g.results[0].armors.every(a=>a.rank==='g'),g.results[0]?.armors?.map(a=>`${a.name}[${a.rank}]`).join(' / '));
check('g_top_no_low_gavra_bias',g.results.slice(0,5).every(b=>!b.armors.some(a=>a.rank==='low'&&/가브라스/.test(a.name||''))));
check('g_top_contains_g_torso_up_waist',g.results.slice(0,5).some(b=>b.armors.some(a=>a.part==='waist'&&a.rank==='g'&&a.torsoUp)),g.results.slice(0,5).map(b=>b.armors.find(a=>a.part==='waist')?.name).join(', '));

check('ranking_metrics_present',g.results.every(b=>{
  const m=b.metrics||{};
  return ['negativeSkillCount','negativeSkillSeverity','usedDecorationSlots','decorationCount','distinctDecorationTypes','targetWastePoints','targetUpgradeSteps','extraPositiveSkillCount','rankMaxDowngrade','rankTotalDowngrade','defense','resistanceTotal','resistanceMinimum','remainingSlots'].every(k=>Number.isFinite(Number(m[k])));
}));
check('resistance_metrics_match_calc',g.results.every(b=>{
  const vals=['fire','water','thunder','ice','dragon'].map(k=>Number(b.calc?.resist?.[k]||0));
  return Number(b.metrics.resistanceTotal)===vals.reduce((s,v)=>s+v,0)&&Number(b.metrics.resistanceMinimum)===Math.min(...vals);
}));

function metricTuple(b){const m=b.metrics||{};return [m.negativeSkillCount,m.negativeSkillSeverity,m.usedDecorationSlots,m.decorationCount,m.distinctDecorationTypes,m.targetWastePoints,-m.targetUpgradeSteps,-m.extraPositiveSkillCount,m.rankMaxDowngrade,m.rankTotalDowngrade,-m.defense,-m.resistanceTotal,-m.resistanceMinimum,-m.remainingSlots].map(Number)}
function leq(a,b){for(let i=0;i<a.length;i++){if(a[i]<b[i])return true;if(a[i]>b[i])return false}return true}
check('ranking_lexicographic_order',g.results.every((b,i,arr)=>i===0||leq(metricTuple(arr[i-1]),metricTuple(b))));

const top=g.results[0];
const report={
  ok:failures.length===0,
  version:'0.7.7-chat4-research2-hotfix20',
  checks,failures,
  scenario:{
    target:'세균연구가 + 명검',progression:'G급',
    topArmors:top?.armors?.map(a=>({part:a.part,name:a.name,rank:a.rank,defense:a.defense,resistances:a.resistances,torsoUp:!!a.torsoUp}))||[],
    topMetrics:top?.metrics||{},
    topActivated:top?.calc?.activated||[]
  },
  counts:{lowEligible:low.stats.eligible,highEligible:high.stats.eligible,gEligible:g.stats.eligible,gRankedPool:g.stats.rankedPool}
};
fs.writeFileSync(new URL('./hotfix20_auto_rank_audit_v0.7.7.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
process.exit(report.ok?0:1);
