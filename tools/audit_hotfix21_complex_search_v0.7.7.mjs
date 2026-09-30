import fs from 'fs';
import {searchBuilds} from '../js/engine.js';

const read=p=>JSON.parse(fs.readFileSync(new URL(`../${p}`,import.meta.url),'utf8'));
const data={armors:read('data/sim_armors.json'),decorations:read('data/decorations.json'),skills:read('data/skills.json')};
const findActivation=name=>{
  for(const s of data.skills){const a=(s.activations||[]).find(x=>x.name===name);if(a)return {skillId:s.id,activationId:a.id,need:Number(a.points)}}
  throw new Error(`activation missing: ${name}`);
};
const ear=findActivation('고급귀마개');
const expert=findActivation('통찰력+1');
const evade=findActivation('회피성능+3');
const sharp=findActivation('숫돌사용고속화');
const ids=[ear.activationId,expert.activationId,evade.activationId,sharp.activationId];
const failures=[];const checks={};
const check=(name,ok,detail='')=>{checks[name]=!!ok;if(!ok)failures.push(`${name}${detail?`: ${detail}`:''}`)};

async function runComplex({charm={skills:{},slots:0},weaponSlots=0,limit=10}={}){
  let ticks=0;const timer=setInterval(()=>ticks++,20);const started=Date.now();let progressEvents=0;
  const r=await searchBuilds({targetActivationIds:ids,hunterType:'blade',rank:'g',charm,weaponSlots,allowDecorations:true,includeTorsoUp:true,limit,onProgress:()=>progressEvents++},data);
  clearInterval(timer);return {r,elapsed:Date.now()-started,ticks,progressEvents};
}

const base=await runComplex();
check('complex_finishes_bounded',base.elapsed<7500,`elapsed=${base.elapsed}`);
check('complex_profile_selected',base.r.stats?.profile==='complex4',JSON.stringify(base.r.stats));
check('complex_ui_yield_points',base.ticks>=5,`ticks=${base.ticks}`);
check('complex_progress_events',base.progressEvents>=5,`events=${base.progressEvents}`);
check('complex_returns_diagnostic',base.r.results.length>0||(base.r.nearMisses||[]).length>0,`exact=${base.r.results.length} near=${base.r.nearMisses?.length||0}`);
if(base.r.results.length===0){
  const top=base.r.nearMisses?.[0];
  check('near_miss_present',!!top);
  check('near_miss_has_deficit',(top?.missing||[]).some(x=>Number(x.missing)>0),JSON.stringify(top?.missing||[]));
  check('near_miss_evade_deficit',(top?.missing||[]).some(x=>x.skillId===evade.skillId&&Number(x.missing)>0),JSON.stringify(top?.missing||[]));
}

const assisted=await runComplex({charm:{skills:{[evade.skillId]:5},slots:3},weaponSlots:3,limit:5});
check('assisted_finishes_bounded',assisted.elapsed<8500,`elapsed=${assisted.elapsed}`);
check('assisted_finds_exact',assisted.r.results.length>0,`exact=${assisted.r.results.length} near=${assisted.r.nearMisses?.length||0}`);
check('assisted_targets_satisfied',assisted.r.results.every(b=>
  Number(b.calc?.points?.[ear.skillId]||0)>=ear.need&&
  Number(b.calc?.points?.[expert.skillId]||0)>=expert.need&&
  Number(b.calc?.points?.[evade.skillId]||0)>=evade.need&&
  Number(b.calc?.points?.[sharp.skillId]||0)>=sharp.need
));

const report={ok:failures.length===0,version:'0.7.7-chat4-research2-hotfix21',scenario:'고급귀마개 + 통찰력+1 + 회피성능+3 + 숫돌사용고속화',checks,failures,base:{elapsedMs:base.elapsed,ticks:base.ticks,progressEvents:base.progressEvents,stats:base.r.stats,exact:base.r.results.length,nearMiss:base.r.nearMisses?.[0]?.missing||[]},assisted:{condition:'회피성능 +5 호석 / 호석 3슬롯 / 무기 3슬롯',elapsedMs:assisted.elapsed,stats:assisted.r.stats,exact:assisted.r.results.length,top:assisted.r.results[0]?.armors?.map(a=>a.name)||[]}};
fs.writeFileSync(new URL('./hotfix21_complex_search_audit_v0.7.7.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
process.exit(report.ok?0:1);
