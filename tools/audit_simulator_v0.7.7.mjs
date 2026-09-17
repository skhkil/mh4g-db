import fs from 'fs';
import {searchBuilds} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url),'utf8'));
const data={skills:read('data/skills.json'),armors:read('data/sim_armors.json'),decorations:read('data/decorations.json')};
const activations=new Map();
for(const s of data.skills)for(const a of s.activations||[])if(Number(a.points)>0)activations.set(a.name,{skillId:s.id,activationId:a.id,points:Number(a.points),skill:s.name});
const rankOrder={low:1,high:2,g:3};
function req(ids){const out={};for(const id of ids)for(const [name,x] of activations)if(x.activationId===id)out[x.skillId]=Math.max(out[x.skillId]||0,x.points);return out}
function validateResult(r,requirements,opt){
 const errors=[];
 for(const [id,need] of Object.entries(requirements))if(Number(r.calc.points[id]||0)<need)errors.push(`target:${id} ${r.calc.points[id]||0}<${need}`);
 for(const a of r.armors){
  if(!(a.hunterType==='both'||a.hunterType===opt.hunterType))errors.push(`hunter:${a.name}`);
  if(opt.rank!=='all'&&(rankOrder[a.rank]||99)>(rankOrder[opt.rank]||0))errors.push(`rank:${a.name}:${a.rank}`);
 }
 const cap={weapon:Number(opt.weaponSlots||0),head:0,body:0,arms:0,waist:0,legs:0,charm:Number(opt.charm?.slots||0)};
 for(const a of r.armors)cap[a.part]=Number(a.slots||0);
 for(const p of r.decorations){const c=Number(p.deco?.slots||0);if(!(p.container in cap)||cap[p.container]<c)errors.push(`slot:${p.container}:${p.deco?.name}`);else cap[p.container]-=c;}
 return errors;
}
const cases=[
 {name:'공격대',skills:['공격력UP【대】'],hunterType:'blade',rank:'all'},
 {name:'장인',skills:['예리도레벨+1'],hunterType:'blade',rank:'all'},
 {name:'공격대+장인',skills:['공격력UP【대】','예리도레벨+1'],hunterType:'blade',rank:'all'},
 {name:'집중+고귀',skills:['집중','고급귀마개'],hunterType:'gunner',rank:'all'},
 {name:'도공(장식주없음)',skills:['명검'],hunterType:'blade',rank:'g'},
 {name:'상위거너',skills:['집중','고급귀마개'],hunterType:'gunner',rank:'high'}
];
const audit=[];
for(const c of cases){
 const ids=c.skills.map(n=>activations.get(n)?.activationId).filter(Boolean);const opt={targetActivationIds:ids,hunterType:c.hunterType,rank:c.rank,charm:{skills:{},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit:20};
 const t=performance.now();const r=await searchBuilds(opt,data);const ms=Math.round(performance.now()-t);const requirements=req(ids);let errors=[];for(const x of r.results)errors.push(...validateResult(x,requirements,opt));
 audit.push({case:c.name,skills:c.skills,hunterType:c.hunterType,rank:c.rank,ms,results:r.results.length,errors:[...new Set(errors)],stats:r.stats});
}
const report={generatedAt:new Date().toISOString(),counts:{skills:data.skills.length,armors:data.armors.length,decorations:data.decorations.length},cases:audit,hardErrors:audit.reduce((n,x)=>n+x.errors.length,0)};
fs.writeFileSync(new URL('../tools/simulator_audit_v0.7.7.json',import.meta.url),JSON.stringify(report,null,2));
const lines=['# 자동조합 검색 감사 v0.7.7','',`- 스킬: ${data.skills.length}` ,`- 시뮬레이터 방어구: ${data.armors.length}`,`- 장식주: ${data.decorations.length}`,`- 하드 오류: ${report.hardErrors}`,'','## 검증 케이스',''];
for(const x of audit)lines.push(`- ${x.case}: ${x.hunterType}/${x.rank}, 결과 ${x.results}건, ${x.ms}ms, 오류 ${x.errors.length}건`);
lines.push('','## 수정 사항','','- 자동검색용 검사/거너 및 진행도 필터를 수동 장비 선택과 분리.','- 진행도는 하위/상위/G급까지의 사용 가능 장비를 누적 포함.','- 부위별 후보에서 목표 스킬/슬롯/방어력 기준 지배 후보 제거.','- 전체 후보 배열 정렬 대신 고정 크기 Top-K 최소 힙 사용.','- 장식주 관련 후보를 검색 1회만 사전 계산하고 조합 상태를 메모이즈.','- 반복 검색 결과를 브라우저 메모리 캐시(최대 12조건)로 재사용.','- 최종 결과마다 목표 스킬 충족/슬롯 초과를 재검증.','- 장식주 배치 단계에서 주기적으로 이벤트 루프에 제어를 반환해 모바일 UI 멈춤을 줄임.');
fs.writeFileSync(new URL('../tools/simulator_audit_v0.7.7.md',import.meta.url),lines.join('\n'));
console.log(JSON.stringify(report,null,2));
