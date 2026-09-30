import fs from 'fs';
import {searchBuilds} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(new URL(`../${p}`,import.meta.url),'utf8'));
const data={armors:read('data/sim_armors.json'),decorations:read('data/decorations.json'),skills:read('data/skills.json')};
const findActivation=name=>{for(const s of data.skills){const a=(s.activations||[]).find(x=>x.name===name);if(a)return {skill:s,activation:a};}throw new Error(`activation missing: ${name}`)};
const ear=findActivation('고급귀마개'),expert=findActivation('통찰력+1'),evade=findActivation('회피성능+3'),sharp=findActivation('숫돌사용고속화');
const ids=[ear.activation.id,expert.activation.id,evade.activation.id,sharp.activation.id];
const base=await searchBuilds({targetActivationIds:ids,hunterType:'blade',rank:'g',charm:{skills:{},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit:10},data);
const assisted=await searchBuilds({targetActivationIds:ids,hunterType:'blade',rank:'g',charm:{skills:{[evade.skill.id]:5},slots:3},weaponSlots:3,allowDecorations:true,includeTorsoUp:true,limit:5},data);
const top=base.nearMisses?.[0];
const checks={
  base_has_near_miss:base.results.length===0&&!!top,
  resource_analysis_present:typeof top?.slotCompletion?.slotOnlyCompletable==='boolean'&&Number.isFinite(Number(top?.slotCompletion?.currentFreeSlots)),
  slot_completable_candidate_prioritized:top?.slotCompletion?.slotOnlyCompletable===true,
  minimum_additional_slots_computed:Number(top?.slotCompletion?.minAdditionalSlots)===5,
  base_top_evade_deficit:(top?.missing||[]).some(x=>x.skillId===evade.skill.id&&Number(x.missing)===7),
  assisted_exact_found:assisted.results.length>0,
  assisted_uses_full_resources:assisted.results.every(b=>Number(b.calc?.points?.[evade.skill.id]||0)>=20),
  exact_metrics_keep_free_slots:assisted.results.every(b=>Number.isFinite(Number(b.metrics?.remainingSlots)))
};
const report={ok:Object.values(checks).every(Boolean),version:'0.7.7-stage2-resource-feasibility',scenario:'고급귀마개 + 통찰력+1 + 회피성능+3 + 숫돌사용고속화',checks,base:{stats:base.stats,topNear:top?{missing:top.missing,slotCompletion:{...top.slotCompletion,extraPlacements:(top.slotCompletion.extraPlacements||[]).map(x=>({name:x.deco?.name||x.deco,container:x.container}))},armors:top.armors.map(a=>({name:a.name,slots:a.slots}))}:null},assisted:{condition:'회피성능 +5 / 호석3슬롯 / 무기3슬롯',stats:assisted.stats,top:assisted.results[0]?{armors:assisted.results[0].armors.map(a=>a.name),remainingSlots:assisted.results[0].metrics.remainingSlots,decorations:assisted.results[0].decorations.map(x=>x.deco?.name||x.deco)}:null}};
fs.writeFileSync(new URL('./auto_build_stage2_resource_audit_v0.7.7.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));process.exit(report.ok?0:1);
