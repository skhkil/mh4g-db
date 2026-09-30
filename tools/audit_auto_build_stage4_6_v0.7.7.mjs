import fs from 'fs';
import {searchBuilds} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(new URL(`../${p}`,import.meta.url),'utf8'));
const data={armors:read('data/sim_armors.json'),decorations:read('data/decorations.json'),skills:read('data/skills.json')};
const priorities=read('data/weapon_skill_priorities.json');
const reco=read('data/recommended_loadouts.json');
const research=fs.readFileSync(new URL('./recommended_loadouts_weapon_research_v0.7.7.md',import.meta.url),'utf8');
const weapons=['대검','태도','한손검','쌍검','해머','수렵피리','랜스','건랜스','슬래시액스','차지액스','조충곤','라이트보우건','헤비보우건','활'];
const skillByName=new Map(data.skills.map(s=>[s.name,s]));
const findAct=name=>{for(const s of data.skills){const a=(s.activations||[]).find(x=>x.name===name);if(a)return {s,a};}throw new Error(name)};
const coverage=Object.fromEntries(weapons.map(w=>[w,{priority:!!priorities.weapons?.[w],recommended:reco.entries?.some(e=>e.weaponType===w),research:research.includes(`| ${w} |`),missingSkills:Object.keys(priorities.weapons?.[w]||{}).filter(n=>!skillByName.has(n))}]));
const hg=findAct('고급귀마개');
const artillery=skillByName.get('포술');
const r=await searchBuilds({targetActivationIds:[hg.a.id],hunterType:'blade',rank:'g',charm:{skills:{},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit:5,preferredSkillWeights:{[artillery.id]:999}},data);
const checks={
  fourteen_weapons:weapons.length===14&&Object.keys(priorities.weapons||{}).length===14,
  priority_skills_resolve:Object.values(coverage).every(x=>x.missingSkills.length===0),
  recommendation_db_coverage:Object.values(coverage).every(x=>x.recommended),
  research_coverage:Object.values(coverage).every(x=>x.research),
  target_stays_primary:r.results.length>0&&r.results.every(b=>Number(b.calc.points[hg.s.id]||0)>=15),
  preferred_metric_present:r.results.length>0&&r.results.every(b=>typeof b.metrics.preferredSkillScore==='number'),
  source_policy:priorities.policy?.includes('사용자 목표 스킬이 최우선')===true
};
const report={ok:Object.values(checks).every(Boolean),version:'0.7.7-auto-build-stage4-6',checks,coverage,probe:{target:'고급귀마개',preferred:'포술 x999',top:r.results.map(b=>({hearing:b.calc.points[hg.s.id],preferredSkillScore:b.metrics.preferredSkillScore,targetWaste:b.metrics.targetWastePoints,remainingSlots:b.metrics.remainingSlots}))}};
fs.writeFileSync(new URL('./auto_build_stage4_6_audit_v0.7.7.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));process.exit(report.ok?0:1);
