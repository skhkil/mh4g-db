import fs from 'fs'; import {searchBuilds} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')); const data={skills:read('./data/skills.json'),armors:read('./data/sim_armors.json'),decorations:read('./data/decorations.json')};
const activation=name=>{for(const s of data.skills)for(const a of s.activations||[])if(a.name===name)return a.id;throw new Error('missing '+name)};
const sets=[
 ['고급귀마개','숫돌사용고속화','통찰력+1'],
 ['고급귀마개','숫돌사용고속화','통찰력+1','회피성능+2'],
 ['고급귀마개','숫돌사용고속화','통찰력+1','회피성능+2','예리도레벨+1']
];
const runs=[];let ok=true;
for(const names of sets){const started=Date.now();const r=await searchBuilds({targetActivationIds:names.map(activation),hunterType:'blade',rank:'g',charm:{skills:{},slots:3},weaponSlots:3,allowDecorations:true,includeTorsoUp:true,limit:5,timeBudgetMs:8000},data);const elapsed=Date.now()-started;const pass=elapsed<9500&&(r.results.length>0||(r.nearMisses||[]).length>0)&&['balanced3','complex4','complex5'].includes(r.stats?.profile);ok&&=pass;runs.push({names,elapsedMs:elapsed,profile:r.stats?.profile,exact:r.results.length,near:(r.nearMisses||[]).length,timedOut:r.stats?.timedOut,pass});}
const report={version:'0.7.7-step3-complex-profiles',ok,runs};fs.writeFileSync('./tools/step3_complex_profiles_audit_v0.7.7.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));process.exit(ok?0:1);
