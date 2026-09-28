import fs from 'fs';
import {performance} from 'perf_hooks';
const armors=JSON.parse(fs.readFileSync(new URL('../data/armors.json',import.meta.url),'utf8'));
const skills=JSON.parse(fs.readFileSync(new URL('../data/skills.json',import.meta.url),'utf8'));
const skillById=new Map(skills.map(s=>[s.id,s]));
const alias={"통격":"약점 약특 약점특효 회심 크리티컬","달인":"회심 크리티컬 통찰력","발도치명타":"회심 크리티컬 발도","잠재력":"회심 크리티컬 힘의해방","투혼":"회심 크리티컬 도전자","광격내성":"회심 크리티컬 광룡 무아지경"};
const torso=["몸통배가","동계통배가","몸통 배가","胴系統倍加","torso up","torso-up"];
const hunter=t=>({blade:'검사',gunner:'거너',both:'공용'}[t]||t||'-');
const rank=r=>({low:'하위',high:'상위',g:'G급'}[r]||r||'-');
function oldSkillCorpus(a){return Object.keys(a.skills||{}).map(id=>{const s=skillById.get(id);if(!s)return id;const acts=(s.activations||[]).flatMap(x=>[x.name,x.nameJa,x.nameEn]);return [s.name,s.nameJa,s.nameEn,alias[s.name]||'',...acts].filter(Boolean).join(' ')}).join(' ')}
function oldMatch(a,query){const q=String(query||'').trim().toLowerCase();if(!q)return true;if(torso.some(x=>x.toLowerCase()===q))return !!a.torsoUp;const exact=[];for(const s of skills){const names=[s.name,s.nameJa,s.nameEn].filter(Boolean).map(x=>String(x).toLowerCase());if(names.includes(q))exact.push(s.id)}if(exact.length)return exact.some(id=>Object.prototype.hasOwnProperty.call(a.skills||{},id));if(q.length>=2&&torso.some(x=>x.toLowerCase().includes(q)||q.includes(x.toLowerCase())))return !!a.torsoUp;let looks=false;if(q.length>=2)looks=skills.some(s=>[s.name,s.nameJa,s.nameEn,alias[s.name]||'',...(s.activations||[]).flatMap(x=>[x.name,x.nameJa,x.nameEn])].filter(Boolean).some(x=>String(x).toLowerCase().includes(q)));if(looks)return oldSkillCorpus(a).toLowerCase().includes(q);return `${a.name} ${a.nameJa||''} ${a.nameEn||''} ${hunter(a.hunterType)} ${rank(a.rank)} ${a.materials||''}`.toLowerCase().includes(q)}
const qcache=new Map(),acache=new Map();
function ctx(query){const q=String(query||'').trim().toLowerCase();if(qcache.has(q))return qcache.get(q);const exact=[];let looks=false;if(q){for(const s of skills){const exactNames=[s.name,s.nameJa,s.nameEn].filter(Boolean).map(x=>String(x).toLowerCase());if(exactNames.includes(q))exact.push(s.id);if(!looks&&q.length>=2){const names=[s.name,s.nameJa,s.nameEn,alias[s.name]||'',...(s.activations||[]).flatMap(x=>[x.name,x.nameJa,x.nameEn])].filter(Boolean);looks=names.some(x=>String(x).toLowerCase().includes(q))}}}const c={q,exact,looks,te:!!q&&torso.some(x=>x.toLowerCase()===q),tl:q.length>=2&&torso.some(x=>x.toLowerCase().includes(q)||q.includes(x.toLowerCase()))};qcache.set(q,c);return c}
function corpus(a){if(acache.has(a.id))return acache.get(a.id);const skill=oldSkillCorpus(a).toLowerCase(),normal=`${a.name} ${a.nameJa||''} ${a.nameEn||''} ${hunter(a.hunterType)} ${rank(a.rank)} ${a.materials||''}`.toLowerCase();const c={skill,normal};acache.set(a.id,c);return c}
function fastMatch(a,query){const c=ctx(query);if(!c.q)return true;if(c.te)return !!a.torsoUp;if(c.exact.length)return c.exact.some(id=>Object.prototype.hasOwnProperty.call(a.skills||{},id));if(c.tl)return !!a.torsoUp;const x=corpus(a);if(c.looks)return x.skill.includes(c.q);return x.normal.includes(c.q)}
const queries=['예리도','고급귀마개','몸통배가','리오','GX'];
function bench(fn,rounds=15){const t0=performance.now();let n=0;for(let r=0;r<rounds;r++)for(const q of queries)for(const a of armors)if(fn(a,q))n++;return {ms:performance.now()-t0,n}}
const old=bench(oldMatch,6); const fast=bench(fastMatch,30);
const oldPer=old.ms/6, fastPer=fast.ms/30;
const out={armors:armors.length,queries,oldMsPerSweep:Number(oldPer.toFixed(2)),optimizedMsPerSweep:Number(fastPer.toFixed(2)),speedup:Number((oldPer/fastPer).toFixed(2)),sameSampleCounts:queries.map(q=>({q,old:armors.filter(a=>oldMatch(a,q)).length,optimized:armors.filter(a=>fastMatch(a,q)).length}))};
fs.writeFileSync(new URL('./armor_search_benchmark_v0.7.7.json',import.meta.url),JSON.stringify(out,null,2));
console.log(JSON.stringify(out,null,2));
