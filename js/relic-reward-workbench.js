
const KEY="mh4g-relic-farm-records-v1";
let loaded=null, selected="",level=131,purpose="sphere",pair="single",minutes=30,success=90;
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e};
const choice=(items,value,change)=>{const s=make("select");for(const [v,t] of items){const o=make("option",null,t);o.value=v;o.selected=v===value;s.append(o)}s.onchange=()=>change(s.value);return s};
const field=(name,control)=>{const l=make("label","rr-field");l.append(make("span",null,name),control);return l};
const fmt=n=>Number.isFinite(n)?n.toFixed(2):"–";
function readRecords(){try{return JSON.parse(localStorage.getItem(KEY)||"{}")}catch{return {}}}
function saveRecord(name,m,s){try{const a=readRecords();a[name]={minutes:m,success:s};localStorage.setItem(KEY,JSON.stringify(a));return true}catch{return false}}
function band(x){return loaded?.verifiedLevelBands.find(b=>x>=b.min&&x<=b.max)}
function group(name){return loaded?.armorSphereGroups.find(g=>g.monsters.includes(name))}
function rate(name,x){const b=band(x);return loaded?.sealedWeaponPerQuest.find(r=>r.monster===name&&r.band===b?.min+"-"+b?.max)}
function notice(target,text){target.append(make("p","rr-note",text))}
function render(d,host){
 host.replaceChildren();const names=[...new Set((d.qualityGuide?.monsterRewardSlots||[]).map(x=>x.monster))];
 if(!selected||!names.includes(selected))selected=names.includes("테오·테스카토르")?"테오·테스카토르":names[0];
 const top=make("section","panel rr-workbench");top.append(make("h2",null,"선택한 길퀘 보상 분석"));
 notice(top,"몬스터·레벨·파밍 목적을 선택하면 관련 보상만 보여줍니다. 수치는 확인된 자료만 사용합니다.");
 const selectors=make("div","rr-fields");
 selectors.append(field("몬스터",choice(names.map(n=>[n,n]),selected,v=>{selected=v;const r=readRecords()[v];if(r){minutes=r.minutes;success=r.success}pair="single";render(d,host)})));
 const lv=make("input");lv.type="number";lv.min="86";lv.max="140";lv.step="1";lv.value=level;lv.onchange=()=>{level=Math.min(140,Math.max(86,Number(lv.value)||86));render(d,host)};
 selectors.append(field("길퀘 레벨 (86~140)",lv));
 selectors.append(field("파밍 목표",choice([["sphere","천갑옥"],["weapon","봉인 무기"],["armor","봉인 방어구"],["any","전체 보상"]],purpose,v=>{purpose=v;render(d,host)})));
 top.append(selectors);
 const b=band(level),g=group(selected),r=rate(selected,level),slots=d.qualityGuide?.monsterRewardSlots?.find(x=>x.monster===selected);
 const result=make("div","rr-facts");
 const facts=[
 ["현재 구간",b?.label||"미확인"],
 ["기본 단일 보상칸",slots?.singleSlots||"미확인"],
 ["천갑옥 출현 조건",g?(level>=g.minLevel?"표기상 출현 가능 (Lv"+g.minLevel+"+)":"Lv"+g.minLevel+"부터 출현 표기"):"출처 미확인"],
 ["봉인 무기 · 1회 퀘스트 확률",r?r.percent+"% (Game-Cap)":"해당 조건 수치 미확인"]
 ];
 for(const [key,val] of facts){const cell=make("div","rr-fact");cell.append(make("small",null,key),make("strong",null,val));result.append(cell)}top.append(result);
 if(purpose==="sphere")notice(top,"천갑옥 획득 확률 자체는 미확인입니다. 위의 출현 레벨은 획득 보장이 아닙니다.");
 if(purpose==="weapon")notice(top,"Game-Cap의 1회 퀘스트 확률은 일본 보상칸별 추첨 확률과 다른 단위이며 서로 합산하지 않습니다.");
 if(purpose==="armor")notice(top,"봉인 방어구의 몬스터·레벨별 1회 퀘스트 확률은 아직 이 화면의 검증 데이터에 없습니다.");
 const compare=make("details","rr-more");compare.append(make("summary",null,"레벨 구간 전체 비교"));
 const matrix=make("div","rr-band-grid");
 for(const x of loaded.verifiedLevelBands){const el=make("div",level>=x.min&&level<=x.max?"rr-band rr-current":"rr-band");const rateFor=rate(selected,x.min);el.append(make("b",null,x.label),make("span",null,"천갑옥: "+(g&&x.max>=g.minLevel?"출현 가능 구간":"출현 조건 미달/미확인")),make("span",null,"봉인 무기: "+(rateFor?rateFor.percent+"% (1회)":"미확인")));matrix.append(el)}
 compare.append(matrix);top.append(compare);
 host.append(top);
 const duo=make("section","panel rr-workbench");duo.append(make("h2",null,"2두 길퀘 보상 비교"));
 notice(duo,"일본 분석 자료에 기재된 조합만 표시합니다. 극한상태·보상 포인트가 확인되지 않은 조건은 계산하지 않습니다.");
 const options=[["single","1두 · "+selected],...loaded.duoPresets.map(x=>[x.id,x.label])];
 duo.append(field("비교 대상",choice(options,pair,v=>{pair=v;render(d,host)})));
 const current=loaded.duoPresets.find(x=>x.id===pair);
 const box=make("div","rr-pair-output");
 if(!current){box.append(make("strong",null,"1두 "+selected),make("p",null,"기본 단일 보상칸 "+(slots?.singleSlots||"미확인")+" · Lv136~140 대표 포인트는 조건별 기존 원본표를 참고"))}
 else{box.append(make("strong",null,current.label));
 box.append(make("p",null,"왼쪽 몬스터: "+current.left+" · 오른쪽 몬스터: "+current.right));
 box.append(make("p",null,"공통 보상 포인트: "+(current.points??"상태별 검증 필요")+" · 공통 보상칸: "+(current.slots??"미확인")));
 box.append(make("p",null,"외형은 왼쪽 몬스터 그룹 기준. 각 몬스터의 기타 보상은 공통 보상칸과 별개입니다."));
 if(current.support==="conditional_unverified")box.append(make("p","rr-note","조건부 사례이므로 미확인 수치를 채우지 않았습니다."));
 if(level<136)box.append(make("p","rr-note","주의: 현재 선택한 Lv"+level+"에는 Lv136~140 보상 포인트·칸 자료를 그대로 적용할 수 없습니다."));
 }
 duo.append(box);host.append(duo);
 const farm=make("section","panel rr-workbench");farm.append(make("h2",null,"목적별 파밍 후보"));
 const sourceNames=purpose==="sphere"?names.filter(n=>group(n)):(purpose==="weapon"?names.filter(n=>rate(n,level)):purpose==="armor"?[]:names);
 const ranked=sourceNames.map(name=>{const g=group(name),r=rate(name,level);const verified=(purpose==="sphere"?g&&level>=g.minLevel:purpose==="weapon"?Boolean(r):true);return {name,g,r,verified}}).filter(x=>x.verified);
 if(purpose==="armor")notice(farm,"봉인 방어구의 1회 퀘스트 획득 확률에 대한 동일 기준 자료가 부족해 수치 순위를 제공하지 않습니다. 기존 Lv136~140 기타 보상 표를 참고하세요.");
 else{
 notice(farm,"후보는 출처가 있는 조건별 목록이며 사냥 난도·보유 길퀘·클리어 속도를 고려한 추천 순위가 아닙니다.");
 const rows=make("div","rr-candidate-list");
 for(const x of ranked.slice(0,24)){
  const p=make("div","rr-candidate");p.append(make("strong",null,x.name));
  p.append(make("small",null,purpose==="sphere"?"천갑옥 출현 레벨 Lv"+x.g.minLevel+"+":x.r?"봉인 무기 1회 퀘스트 "+x.r.percent+"%":"원자료 조건 확인 필요"));
  const btn=make("button",null,"이 몬스터 조회");btn.onclick=()=>{selected=x.name;pair="single";render(d,host);host.scrollIntoView({block:"start",behavior:"smooth"})};p.append(btn);rows.append(p)
 }
 farm.append(rows);if(!ranked.length)notice(farm,"선택 조건에서 검증된 후보가 없습니다.");
 }host.append(farm);
 const efficiency=make("section","panel rr-workbench");efficiency.append(make("h2",null,"나의 파밍 효율"));
 const timeFields=make("div","rr-fields");const time=make("input");time.type="number";time.min="1";time.max="240";time.value=minutes;
 const prob=make("input");prob.type="number";prob.min="1";prob.max="100";prob.value=success;
 const update=()=>{minutes=Math.max(1,Number(time.value)||1);success=Math.min(100,Math.max(1,Number(prob.value)||1));showMetrics()};
 time.oninput=update;prob.oninput=update;
 timeFields.append(field("클리어 시간 (분)",time),field("성공률 (%)",prob));efficiency.append(timeFields);
 const report=make("div","rr-facts");efficiency.append(report);
 function showMetrics(){report.replaceChildren();const h=60/minutes*success/100;const items=[["성공한 퀘스트 / 시간",fmt(h)+"회"],["60분당 봉인 무기 획득 확률 참고",r?"검증된 1회 퀘스트 "+r.percent+"%":"확률 미확인"]];
 for(const [k,v] of items){const e=make("div","rr-fact");e.append(make("small",null,k),make("strong",null,v));report.append(e)}
 noticePlaceholder.textContent="시간당 클리어 수는 실패에 추가로 걸리는 시간을 별도 모델링하지 않은 간이 추정입니다. 기대 감정품 개수는 1회 확률과 보상 수량 분포가 충분히 검증되지 않아 산출하지 않습니다.";
 }
 const noticePlaceholder=make("p","rr-note");efficiency.append(noticePlaceholder);
 const save=make("button","rr-save","이 몬스터 기록 저장");save.onclick=()=>{if(saveRecord(selected,minutes,success)){save.textContent="저장됨 ✓"}};efficiency.append(save);showMetrics();host.append(efficiency);
 const end=make("details","panel rr-source");end.append(make("summary",null,"계산 기준 및 원본 자료"));
 for(const [key,url] of Object.entries(loaded.sources)){const a=make("a",null,key+" · 출처");a.href=url;a.rel="noopener noreferrer";a.target="_blank";end.append(a)}
 notice(end,"2두 조합 결과와 단일 몬스터 1회 확률을 곱하거나 합산해 정확한 보상 기대값을 계산하지 않습니다.");
 host.append(end);
}
export async function mountRelicRewards(d){
 const area=document.getElementById("relicPanel-rewards");if(!area)return;
 let root=area.querySelector("#relicRewardWorkbench");if(!root){root=make("div","rr-shell");root.id="relicRewardWorkbench";area.insertBefore(root,area.firstChild)}
 try{if(!loaded){const x=await fetch("./data/relic_reward_workbench.json?v=0.7.7-relic-rewards-steps1-4",{cache:"no-cache"});if(!x.ok)throw Error("HTTP "+x.status);loaded=await x.json()}
 if(!loaded?.verifiedLevelBands||!loaded?.duoPresets)throw Error("Invalid reward workbench data");
 const prior=readRecords();if(!selected&&prior["테오·테스카토르"]){minutes=prior["테오·테스카토르"].minutes;success=prior["테오·테스카토르"].success}
 render(d,root);
 }catch(e){root.replaceChildren();notice(root,"보상 분석 데이터를 불러오지 못했습니다: "+e.message)}
}
