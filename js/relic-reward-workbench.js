
let loaded=null, selected="",level=131,purpose="sphere",pair="single",duoLeft="도스람포스",duoRight="라잔";
import {mountRelicMining} from "./relic-mining-guide.js?v=0.7.7-relic-mining-4";
const REWARD_GOAL_KEY="mh4g-relic-appearance-goals-v1";
let activeGoalId="";
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e};
const choice=(items,value,change)=>{const s=make("select");for(const [v,t] of items){const o=make("option",null,t);o.value=v;o.selected=v===value;s.append(o)}s.onchange=()=>change(s.value);return s};
const field=(name,control)=>{const l=make("label","rr-field");l.append(make("span",null,name),control);return l};
function band(x){return loaded?.verifiedLevelBands.find(b=>x>=b.min&&x<=b.max)}
function group(name){return loaded?.armorSphereGroups.find(g=>g.monsters.includes(name))}
function rate(name,x){const b=band(x);return loaded?.sealedWeaponPerQuest.find(r=>r.monster===name&&r.band===b?.min+"-"+b?.max)}
function notice(target,text){target.append(make("p","rr-note",text))}
function render(d,host){
 host.replaceChildren();const names=[...new Set((d.qualityGuide?.monsterRewardSlots||[]).map(x=>x.monster))];
 const request=window.__mh4gRelicRewardTarget;
 if(request?.monster&&names.includes(request.monster)){selected=request.monster;if(request.goalId)activeGoalId=request.goalId;window.__mh4gRelicRewardTarget=null;}

 if(!selected||!names.includes(selected))selected=names.includes("테오·테스카토르")?"테오·테스카토르":names[0];
 const goals=(()=>{try{const a=JSON.parse(localStorage.getItem(REWARD_GOAL_KEY)||"[]");return Array.isArray(a)?a:[]}catch{return []}})();

 const goalPanel=make("section","panel rr-workbench rr-goal-bridge");
 const goalHead=make("div","rr-heading");goalHead.append(make("span","rr-step","저장 목표 · 길퀘 연결"),make("h2",null,"목표 발굴 외형 · 길퀘 연결"));goalPanel.append(goalHead);
 if(goals.length){
  const all=[];for(const [type,arr] of Object.entries(d.weaponAppearances||{}))for(const jp of new Set(arr.filter(x=>x&&x!=="-")))all.push({id:["weapon",type,jp].join("|"),name:d.weaponAppearanceNamesKo?.[jp]||jp,groups:arr.flatMap((x,i)=>x===jp?[i+1]:[])});
  for(const jp of new Set(Object.values(d.armorAppearancePools||{}).flat()))all.push({id:["armor","방어구",jp].join("|"),name:d.armorAppearanceNamesKo?.[jp]||jp,groups:Object.entries(d.armorAppearancePools||{}).filter(([g,arr])=>arr.includes(jp)).map(([g])=>Number(g))});
  const matched=goals.map(g=>all.find(x=>x.id===g.id)).filter(Boolean);
  if(matched.length){
   if(!matched.some(g=>g.id===activeGoalId))activeGoalId=matched[0].id;
   goalPanel.append(field("저장한 외형",choice(matched.map(x=>[x.id,x.name]),activeGoalId,v=>{activeGoalId=v;render(d,host)})));
   const g=matched.find(x=>x.id===activeGoalId);
   const monsters=[...new Set(g.groups.flatMap(id=>d.sealedGroups?.find(x=>Number(x.id)===id)?.monsters||[]))];
   notice(goalPanel,"외형 그룹 "+g.groups.join(", ")+" · 해당 길퀘 몬스터: "+monsters.join(" / ")+" · 발굴 장비 획득은 확정이 아닙니다.");
   const buttons=make("div","rr-goal-monsters");
   for(const monster of monsters){const b=make("button",null,monster+" 조회");b.onclick=()=>{selected=monster;render(d,host)};buttons.append(b)}goalPanel.append(buttons)
  }else notice(goalPanel,"저장된 외형을 현재 발굴 DB에서 찾을 수 없습니다.");
 }else notice(goalPanel,"발굴 외형 탭에서 ☆ 목표 저장을 누르면 관련 길퀘 후보가 여기에 표시됩니다.");
 host.append(goalPanel);

 const top=make("section","panel rr-workbench rr-lookup");const heading=make("div","rr-heading");heading.append(make("span","rr-step","01 · 보상 조회"),make("h2",null,"선택한 길퀘 보상 분석"));top.append(heading);
 notice(top,"몬스터·레벨·파밍 목적을 선택하면 관련 보상만 보여줍니다. 수치는 확인된 자료만 사용합니다.");
 const selectors=make("div","rr-fields");
 selectors.append(field("몬스터",choice(names.map(n=>[n,n]),selected,v=>{selected=v;render(d,host)})));
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

 const duo=make("section","panel rr-workbench rr-duo");
 const duoHeading=make("div","rr-heading");duoHeading.append(make("span","rr-step","02 · 2두 길퀘"),make("h2",null,"2두 길퀘 보상 계산"),make("p","rr-note","두 몬스터의 포인트를 합산해 공통 보상칸 범위를 계산합니다. Lv136~140의 원문 상태값 기준이며, 계산 가능하다고 실제 생성 가능한 조합인 것은 아닙니다."));duo.append(duoHeading);
 const explanation=make("div","rr-explain");
 for(const [title,desc] of [["공통 보상","두 몬스터의 포인트를 합산해 결정. 단일 보상칸을 더하지 않습니다."],["기타 보상","몬스터마다 별도 1칸. ×2는 한 칸에서 2개를 받는 뜻입니다."],["발굴 외형","왼쪽 아이콘 몬스터가 외형 그룹을 결정합니다."]]){const x=make("div","rr-explain-item");x.append(make("strong",null,title),make("p",null,desc));explanation.append(x)}duo.append(explanation);
 const duoDb=loaded.duoDatabase;
 if(duoDb){
  const choices=duoDb.eligibleMonsters.map(x=>[x.name,x.name+" · "+x.points+"pt"]);
  if(!choices.some(x=>x[0]===duoLeft))duoLeft="도스람포스";
  if(!choices.some(x=>x[0]===duoRight))duoRight="라잔";
  const duoSelectors=make("div","rr-fields rr-duo-fields");
  duoSelectors.append(field("왼쪽 몬스터 · 외형 기준",choice(choices,duoLeft,v=>{duoLeft=v;render(d,host)})));
  duoSelectors.append(field("오른쪽 몬스터",choice(choices,duoRight,v=>{duoRight=v;render(d,host)})));
  duo.append(duoSelectors);
  const l=duoDb.eligibleMonsters.find(x=>x.name===duoLeft),r=duoDb.eligibleMonsters.find(x=>x.name===duoRight);
  const sum=l.points+r.points,range=duoDb.pointSlotBands.find(x=>x.points===sum);
  const output=make("div","rr-pair-output");output.append(make("strong",null,duoLeft+" + "+duoRight));
  const metrics=make("div","rr-facts");
  for(const [k,v] of [["보상 포인트",sum+"pt ("+l.points+" + "+r.points+")"],["공통 보상칸",range?range.min+"~"+range.max+"칸":"미확인"],["현재 레벨",level>=136?"Lv"+level+" · 범위 적용":"Lv"+level+" · 136 이상에서만 적용"],["외형 그룹",String(d.sealedGroups?.find(g=>g.monsters?.includes(duoLeft))?.id??"미확인")+"그룹 (왼쪽 기준)"]]){
   const item=make("div","rr-fact");item.append(make("small",null,k),make("strong",null,v));metrics.append(item)
  }output.append(metrics);
  notice(output,"적용 상태: "+duoLeft+" ["+l.defaultState+"] / "+duoRight+" ["+r.defaultState+"]. 원문에 기재된 상태 기준이며 현재 퀘스트의 실제 상태는 별도로 확인해야 합니다.");
  notice(output,"중요: 포인트 계산은 실제 길퀘 생성 가능성을 증명하지 않습니다. 미검증 조합의 결과는 가상 비교입니다.");
  const detail=make("details","rr-more");detail.append(make("summary",null,"몬스터별 기타 보상 상세"));
  for(const x of [l,r]){const key=x.name+(x.defaultState==="extreme"?" (극한상태)":"");const record=d.qualityGuide?.otherRewards136140?.find(z=>z.monster===key);notice(detail,x.name+": "+(record?record.outcomes.map(y=>y.item+" ×"+y.count+" ("+y.probability+"%)").join(" · "):"해당 상태 자료 미확인"))}
  output.append(detail);duo.append(output);
  const samples=make("details","rr-more");samples.append(make("summary",null,"원문 계산 예시 "+loaded.duoPresets.length+"건"));
  const sampleList=make("div","rr-preset-list");
  for(const p of loaded.duoPresets){const btn=make("button","rr-preset",p.label+" · "+(p.computedPoints??p.points??"?")+"pt");btn.onclick=()=>{duoLeft=p.left;duoRight=p.right;render(d,host)};sampleList.append(btn)}
  samples.append(sampleList);duo.append(samples);
  const exceptions=make("details","rr-more");exceptions.append(make("summary",null,"2두 대상 제외 몬스터 및 검증 한계"));notice(exceptions,duoDb.singleOnlyMonsters.map(x=>x.name).join(" · "));notice(exceptions,duoDb.caution);duo.append(exceptions);
 }else notice(duo,"2두 보상 포인트 데이터가 없습니다.");
 host.append(duo);
 const farm=make("section","panel rr-workbench");farm.append(make("div","rr-heading"));farm.firstChild.append(make("span","rr-step","03 · 목적별 파밍"),make("h2",null,"목적에 맞는 후보 조회"));
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
 const mining=make("section","panel rr-workbench rr-mining");mining.id="relicMiningGuide";host.append(mining);
 void mountRelicMining(mining,level).catch(e=>{mining.textContent="채굴 자료 표시 오류: "+e.message});
  const end=make("details","panel rr-source");end.append(make("summary",null,"계산 기준 및 원본 자료"));
 for(const [key,url] of Object.entries(loaded.sources)){const a=make("a",null,key+" · 출처");a.href=url;a.rel="noopener noreferrer";a.target="_blank";end.append(a)}
 notice(end,"2두 조합 결과와 단일 몬스터 1회 확률을 곱하거나 합산해 정확한 보상 기대값을 계산하지 않습니다.");
 host.append(end);
}
let rewardTargetListenerBound=false;
export async function mountRelicRewards(d){
 const area=document.getElementById("relicPanel-rewards");if(!area)return;
 if(!rewardTargetListenerBound){
  document.addEventListener("mh4g-relic-reward-target",()=>{
   const host=document.getElementById("relicRewardWorkbench");
   if(host&&loaded)render(d,host);
  });
  document.addEventListener("mh4g-relic-goals-changed",()=>{
   const host=document.getElementById("relicRewardWorkbench");
   if(host&&loaded)render(d,host);
  });
  rewardTargetListenerBound=true;
 }
 let root=area.querySelector("#relicRewardWorkbench");if(!root){root=make("div","rr-shell");root.id="relicRewardWorkbench";area.insertBefore(root,area.firstChild)}
 let legacy=area.querySelector("#relicRewardLegacy");
 if(!legacy){
  legacy=make("details","panel rr-legacy");legacy.id="relicRewardLegacy";
  legacy.append(make("summary",null,"기존 보상 상세표 · MH4/MH4G 출처 자료 펼쳐보기"));
  for(const node of [...area.children]){
   if(node!==root&&node.id!=="relicFarmTarget"&&node!==legacy)legacy.append(node);
  }
  area.append(legacy);
 }
 try{if(!loaded){const x=await fetch("./data/relic_reward_workbench.json?v=0.7.7-relic-mining-bridge5",{cache:"no-cache"});if(!x.ok)throw Error("HTTP "+x.status);loaded=await x.json()}
 if(!loaded?.verifiedLevelBands||!loaded?.duoPresets)throw Error("Invalid reward workbench data");
 render(d,root);
 }catch(e){root.replaceChildren();notice(root,"보상 분석 데이터를 불러오지 못했습니다: "+e.message)}
}
