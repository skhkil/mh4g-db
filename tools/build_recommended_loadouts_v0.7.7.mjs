import fs from 'fs';
import {searchBuilds, PART_NAMES} from '../js/engine.js';
const read=p=>JSON.parse(fs.readFileSync(new URL(`../${p}`,import.meta.url),'utf8'));
const data={skills:read('data/skills.json'),armors:read('data/sim_armors.json'),decorations:read('data/decorations.json')};
const activationByName={}; for(const s of data.skills) for(const a of s.activations||[]) if(Number(a.points)>0) activationByName[a.name]={id:a.id,skillId:s.id,name:a.name,points:Number(a.points)};
const rankLabel={low:'하위',high:'상위',g:'G급'};
const profiles={
'대검':{note:'차지 공격과 발도 중심 운용을 기준으로 구성.',low:['집중'],high:['집중','발도술【기술】'],g:['집중','발도술【기술】','예리도레벨+1']},
'태도':{note:'게이지 유지와 지속 공격을 위한 예리도/화력 중심 구성.',low:['숫돌사용고속화'],high:['예리','통찰력+1'],g:['예리도레벨+1','도전자+2']},
'한손검':{note:'짧은 공격 주기와 회피 운용을 고려한 범용 구성.',low:['숫돌사용고속화'],high:['예리','회피성능+1'],g:['예리도레벨+1','도전자+1']},
'쌍검':{note:'스태미나와 예리도 소모를 줄이는 지속 공격형 구성.',low:['러너'],high:['예리','스태미나급속회복'],g:['예리도레벨+1','스태미나급속회복']},
'해머':{note:'머리 타격과 차지 공격을 중심으로 한 기절/화력 구성.',low:['KO술'],high:['KO술','집중'],g:['KO술','도전자+2']},
'수렵피리':{note:'선율 유지와 기절 보조를 우선한 파티 지원형 구성.',low:['피리명인'],high:['피리명인','KO술'],g:['피리명인','고급귀마개','KO술']},
'랜스':{note:'가드 안정성을 우선한 정면 유지형 구성.',low:['가드성능+1'],high:['가드성능+2'],g:['가드성능+2','가드강화']},
'건랜스':{note:'포격 화력과 가드 안정성을 함께 확보하는 구성.',low:['포술사'],high:['포술왕','가드성능+1'],g:['포술마스터','가드성능+2']},
'슬래시액스':{note:'회피 기동성과 검모드 화력을 고려한 구성.',low:['회피성능+1'],high:['회피성능+1','회피거리UP'],g:['예리도레벨+1','회피성능+2']},
'차지액스':{note:'유탄병 속성해방베기와 가드 포인트를 고려한 구성.',low:['포술사'],high:['포술왕','가드성능+1'],g:['포술마스터','예리도레벨+1']},
'조충곤':{note:'탑승 성능과 근접 화력을 함께 확보하는 구성.',low:['탑승명인'],high:['탑승마스터','예리'],g:['탑승마스터','예리도레벨+1','도전자+1']},
'라이트보우건':{note:'통상탄/속사형 범용 예시. 사용하는 탄종에 따라 탄 강화 스킬 교체 권장.',low:['통상탄�연사살UP'],high:['통상탄�연사살UP','연발수+1'],g:['통상탄�연사살UP','연발수+1','회피거리UP']},
'헤비보우건':{note:'관통탄 운용 기준 예시. 보우건 반동과 주력 탄종에 맞춰 조정 권장.',low:['관통탄�관통살UP'],high:['관통탄�관통살UP','반동경감+1'],g:['관통탄�관통살UP','반동경감+1','회피거리UP']},
'활':{note:'연사 활 기준 범용 예시. 활의 사격 타입에 따라 통상/관통/산탄 강화 교체 권장.',low:['집중'],high:['집중','러너'],g:['집중','통상탄�연사살UP','스태미나급속회복']}
};
const gunner=new Set(['라이트보우건','헤비보우건','활']);
const rareRe=/(티켓|코인|증표|보옥|천린|대보옥|홍옥|역린|천각|천갑|천인|희소)/g;
function craftPenalty(build){let n=0;for(const a of build.armors||[]){const m=String(a.materials||'').match(rareRe);n+=m?m.length:0;}return n;}
function slimBuild(r){
 const decoCount={}; for(const p of r.decorations||[]){const d=p.deco;if(!d)continue; const k=d.id; if(!decoCount[k])decoCount[k]={id:k,name:d.name,slots:d.slots,count:0}; decoCount[k].count++;}
 return {armors:(r.armors||[]).map(a=>({id:a.id,name:a.name,part:a.part,defense:a.defense,slots:a.slots,rank:a.rank,materials:a.materials||''})),decorations:Object.values(decoCount),defense:r.calc?.defense||0,resist:r.calc?.resist||{},activated:(r.calc?.activated||[]).filter(x=>x.threshold>0).map(x=>({skillId:x.skillId,name:x.name,points:x.points})),score:r.score||0,craftPenalty:craftPenalty(r)};
}
function chooseVariants(results){
 if(!results.length)return [];
 const seen=new Set(); const unique=results.filter(r=>{const k=(r.armors||[]).map(a=>a.id).join('|');if(seen.has(k))return false;seen.add(k);return true;});
 const picks=[];
 const add=(label,r,desc)=>{if(!r)return;const k=(r.armors||[]).map(a=>a.id).join('|');if(picks.some(x=>x.key===k))return;picks.push({key:k,label,description:desc,build:slimBuild(r)});};
 add('균형',unique[0],'자동조합 점수 기준의 균형형 예시');
 add('제작 편의',[...unique].sort((a,b)=>craftPenalty(a)-craftPenalty(b)||b.calc.defense-a.calc.defense)[0],'희귀 티켓·코인·희소 소재 의존도를 낮춘 예시');
 add('방어력',[...unique].sort((a,b)=>b.calc.defense-a.calc.defense||b.score-a.score)[0],'조건을 만족하는 후보 중 방어력을 우선한 예시');
 for(const r of unique) if(picks.length<3)add(`대안 ${picks.length+1}`,r,'동일 핵심 스킬을 만족하는 대안');
 return picks.map(({key,...x})=>x);
}
const out={generatedAt:new Date().toISOString(),method:'자동조합 엔진 사전계산 · 호석 없음 · 무기 슬롯 0 · 장식주 허용',weaponTypes:[],entries:[]};
for(const [weaponType,p] of Object.entries(profiles)){
 out.weaponTypes.push(weaponType);
 for(const rank of ['low','high','g']){
   const names=p[rank]; const targets=names.map(n=>activationByName[n]).filter(Boolean);
   if(targets.length!==names.length)throw new Error(`${weaponType}/${rank}: activation missing ${names.filter(n=>!activationByName[n]).join(',')}`);
   const search=await searchBuilds({targetActivationIds:targets.map(x=>x.id),hunterType:gunner.has(weaponType)?'gunner':'blade',rank,charm:{skills:{},slots:0},weaponSlots:0,allowDecorations:true,includeTorsoUp:true,limit:30},data);
   out.entries.push({weaponType,rank,rankLabel:rankLabel[rank],hunterType:gunner.has(weaponType)?'gunner':'blade',targets,summary:p.note,variants:chooseVariants(search.results||[]),resultCount:(search.results||[]).length});
 }
}
fs.writeFileSync(new URL('../data/recommended_loadouts.json',import.meta.url),JSON.stringify(out,null,2));
console.log(`generated ${out.entries.length} entries; empty=${out.entries.filter(x=>!x.variants.length).length}`);
for(const x of out.entries.filter(x=>!x.variants.length))console.log('EMPTY',x.weaponType,x.rank,x.targets.map(t=>t.name));
