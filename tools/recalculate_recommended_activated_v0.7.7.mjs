import fs from 'fs';
import {calculateBuild} from '../js/engine.js';
const p='./data/recommended_loadouts.json';
const rec=JSON.parse(fs.readFileSync(p,'utf8'));
const armors=JSON.parse(fs.readFileSync('./data/armors.json','utf8'));
const decorations=JSON.parse(fs.readFileSync('./data/decorations.json','utf8'));
const skills=JSON.parse(fs.readFileSync('./data/skills.json','utf8'));
const byA=Object.fromEntries(armors.map(x=>[x.id,x]));
const byD=Object.fromEntries(decorations.map(x=>[x.id,x]));
let changed=0, uncertain=[];
for(const e of rec.entries) for(const v of e.variants||[]){
  const b=v.build||{}; const aa=(b.armors||[]).map(x=>byA[x.id]).filter(Boolean);
  let placed=[];
  if((b.decorationPlacements||[]).length){
    for(const x of b.decorationPlacements) if(byD[x.id]) placed.push({deco:byD[x.id],container:x.container});
  } else if((b.decorations||[]).length){
    const torso=aa.filter(a=>a.part!=='body'&&a.torsoUp).length;
    if(torso) uncertain.push(`${e.weaponType}/${e.rank}/${v.label}: aggregate decorations + torso-up`);
    else for(const x of b.decorations) for(let i=0;i<Number(x.count||0);i++) if(byD[x.id]) placed.push({deco:byD[x.id],container:'head'});
  }
  const calc=calculateBuild({armors:aa,decorations:placed},{decorations,skills});
  const next=calc.activated.map(x=>({skillId:x.skillId,name:x.name,points:x.points}));
  if(JSON.stringify(next)!==JSON.stringify(b.activated||[])){b.activated=next;changed++;}
  // keep final example synced for cards whose example is just the verified build
  if(v.exampleEvidence==='기본 구성 검증' || v.exampleEvidence==='국내 원문 기본 세트' || v.exampleEvidence==='국내 원문 장식주 예시' || v.exampleEvidence==='국내 원문 정석 장식주 예시'){
    v.finalSkillsExample=next.map(x=>x.name);
  }
}
fs.writeFileSync(p,JSON.stringify(rec,null,2)+'\n');
console.log(JSON.stringify({changed,uncertain},null,2));
