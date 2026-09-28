import fs from 'fs';
import {calculateBuild} from '../js/engine.js';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const rec=read('./data/recommended_loadouts.json');
const armors=read('./data/armors.json');
const decorations=read('./data/decorations.json');
const skills=read('./data/skills.json');
const byArmor=Object.fromEntries(armors.map(x=>[x.id,x]));
const byDeco=Object.fromEntries(decorations.map(x=>[x.id,x]));
const norm=a=>(a||[]).map(x=>({skillId:x.skillId,name:x.name,points:Number(x.points||0)}));
const sortedNames=a=>(a||[]).map(x=>String(x.name??x)).sort((a,b)=>a.localeCompare(b,'ko'));
const cards=[]; const issues=[];
let engineMismatch=0, missingArmor=0, missingDeco=0, finalMatched=0, finalConditional=0;
for(const e of rec.entries||[]) for(const v of e.variants||[]){
  const b=v.build||{};
  const aa=[];
  for(const a of b.armors||[]){
    const live=byArmor[a.id];
    if(!live){missingArmor++;issues.push(`${e.weaponType}/${e.rank}/${v.label}: missing armor ${a.id}`);} else aa.push(live);
  }
  const placed=[];
  for(const x of b.decorationPlacements||[]){
    const d=byDeco[x.id];
    if(!d){missingDeco++;issues.push(`${e.weaponType}/${e.rank}/${v.label}: missing deco ${x.id}`);} else placed.push({deco:d,container:x.container});
  }
  const calc=calculateBuild({armors:aa,decorations:placed},{decorations,skills});
  const actual=norm(calc.activated);
  const stored=norm(b.activated);
  const engineOk=JSON.stringify(actual)===JSON.stringify(stored);
  if(!engineOk){engineMismatch++;issues.push(`${e.weaponType}/${e.rank}/${v.label}: stored activated mismatch`);}
  const finalNames=sortedNames(v.finalSkillsExample||[]), actualNames=sortedNames(actual);
  const finalOk=JSON.stringify(finalNames)===JSON.stringify(actualNames);
  if(finalOk) finalMatched++; else finalConditional++;
  cards.push({weaponType:e.weaponType,rank:e.rank,label:v.label,engineOk,actualSkills:actual.map(x=>x.name),finalExampleStatus:finalOk?'matches_verified_build':'conditional_or_extended_example',finalSkillsExample:v.finalSkillsExample||[],exampleEvidence:v.exampleEvidence||''});
}
const out={generatedAt:new Date().toISOString(),entries:(rec.entries||[]).length,cards:cards.length,engineMismatch,missingArmor,missingDeco,finalMatched,finalConditional,issues,autoInjectionPolicy:{armors:true,decorations:false,charm:false,weapon:false,weaponSlots:false},cardsDetail:cards};
fs.writeFileSync('./tools/recommend_simulator_link_audit_v0.7.7.json',JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({...out,cardsDetail:undefined},null,2));
if(issues.length)process.exitCode=1;
