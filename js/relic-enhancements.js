
const KEY="mh4g-relic-appearance-goals-v1";
let query="",goalOnly=false,series="all",letter="all",armorOpen=false;
let farm=null;
function goals(){try{const a=JSON.parse(localStorage.getItem(KEY)||"[]");return Array.isArray(a)?a.filter(x=>x&&typeof x.id==="string"):[]}catch{return []}}
function writeGoals(a){try{localStorage.setItem(KEY,JSON.stringify(a));return true}catch{return false}}
function idOf(x){return [x.kind,x.type,x.jp].join("|")}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function action(label,fn,cls){const b=el("button",cls,label);b.type="button";b.onclick=fn;return b}
function index(d){
 const rows=[];
 for(const [type,names] of Object.entries(d.weaponAppearances||{}))for(const jp of new Set(names.filter(n=>n&&n!=="-"))){
  rows.push({kind:"weapon",type,jp,ko:d.weaponAppearanceNamesKo?.[jp]||jp,groups:names.flatMap((n,i)=>n===jp?[i+1]:[])});
 }
 for(const jp of new Set(Object.values(d.armorAppearancePools||{}).flat())){
  rows.push({kind:"armor",type:"방어구",jp,ko:d.armorAppearanceNamesKo?.[jp]||jp,groups:Object.entries(d.armorAppearancePools||{}).filter(([k,a])=>a.includes(jp)).map(([k])=>Number(k))});
 }
 return rows;
}
function monsters(d,ids){return [...new Set(ids.flatMap(id=>(d.sealedGroups||[]).find(g=>Number(g.id)===id)?.monsters||[]))]}
function jumpGroup(d,group,refresh){
 const g=(d.sealedGroups||[]).find(x=>Number(x.id)===Number(group));
 const s=document.getElementById("relicMonsterFilter");
 if(!g?.monsters?.length||!s)return;
 s.value=g.monsters[0];refresh();document.getElementById("relicAppearanceResult")?.scrollIntoView({block:"start",behavior:"smooth"});
}
function renderSearch(d,refresh,changeTab){
 const existing=document.getElementById("relicReverseSearch");if(!existing)return;
 existing.replaceChildren();
 const all=index(d);
 let visibleCount=12;
 const top=el("div","relic-search-top");
 const title=el("div");title.append(el("h3",null,"외형 이름으로 역검색"),el("p","muted","한글·일본어·몬스터 검색 · 봉인된 무구 기준"));
 const count=el("span","muted");top.append(title,count);existing.append(top);
 const bar=el("div","relic-search-controls"),input=el("input");input.type="search";input.placeholder="천상천하무쌍도 / アギト / 라잔";input.value=query;
 input.setAttribute("aria-label","발굴 외형 검색");
 const label=el("label","relic-goal-filter"),check=el("input");check.type="checkbox";check.checked=goalOnly;
 const goalCount=el("span");label.append(check,goalCount);bar.append(input,label);existing.append(bar);
 const list=el("div","relic-search-list");existing.append(list);
 // Keep the actual input element mounted throughout typing. Replacing it on each
 // input event interrupts Korean/other IME composition and breaks the caret.
 function updateResults(){
  const saved=goals(),q=query.trim().toLocaleLowerCase();
  const matched=(!q&&!goalOnly?[]:all).filter(x=>(!goalOnly||saved.some(g=>g.id===idOf(x)))&&(!q||[x.ko,x.jp,x.type,...monsters(d,x.groups)].join(" ").toLocaleLowerCase().includes(q)));
  count.textContent=!q&&!goalOnly?"총 "+all.length+"종 검색 가능":"검색 결과 "+matched.length+"종";
  goalCount.textContent="저장 목표만 보기 ("+saved.length+")";
  list.replaceChildren();
  for(const x of matched.slice(0,visibleCount)){
   const box=el("article","relic-search-item"),head=el("div","relic-search-item-head"),name=el("div","relic-search-name");
   name.append(el("small",null,x.type),el("strong",null,x.ko),el("span",null,x.jp));name.lastChild.lang="ja";
   const id=idOf(x),on=saved.some(g=>g.id===id);
   const favorite=action(on?"★ 목표 해제":"☆ 목표 저장",()=>{
    const prev=goals(),next=prev.some(g=>g.id===id)?prev.filter(g=>g.id!==id):[...prev,{id,kind:x.kind,type:x.type,jp:x.jp}];
    if(writeGoals(next)){
     updateResults();
     document.dispatchEvent(new CustomEvent("mh4g-relic-goals-changed",{detail:{id,saved:next.some(g=>g.id===id)}}));
    }
   },"relic-favorite");favorite.setAttribute("aria-pressed",String(on));
   head.append(name,favorite);box.append(head);
   const groups=el("div","relic-result-groups");
   for(const gid of x.groups)groups.append(action("그룹 "+gid+" · "+monsters(d,[gid]).join(" / "),()=>jumpGroup(d,gid,refresh),"relic-group-link"));
   box.append(groups);
   if(x.kind==="armor"){
    const options=x.groups.flatMap(g=>(d.armorSeriesGuide?.rows||[]).filter(r=>(r.groups?.[String(g)]||[]).includes(x.jp)).map(r=>g+"그룹 · "+r.series+" "+r.letter));
    if(options.length){const detail=el("details","relic-match-series"),summary=el("summary",null,"방어구 계열·A~F 후보 보기");detail.append(summary,el("div","relic-series-hints",options.join(" · ")));box.append(detail)}
   }
   box.append(action("보상·파밍 정보 →",()=>{
    farm={name:x.ko,groups:x.groups,monsters:monsters(d,x.groups)};
    window.__mh4gRelicRewardTarget={monster:farm.monsters[0]||"",goalId:idOf(x)};
    changeTab("rewards");renderFarm(d);
    document.dispatchEvent(new CustomEvent("mh4g-relic-reward-target"));
   },"relic-farm-link"));
   list.append(box);
  }
  if(matched.length>visibleCount){
   const more=action("결과 더 보기 ("+Math.min(12,matched.length-visibleCount)+"개 추가 · "+visibleCount+"/"+matched.length+"개 표시)",()=>{visibleCount+=12;updateResults()},"relic-more-results");
   list.append(more);
  }
  if(!matched.length){
   list.append(el("p","muted relic-search-placeholder",!q&&!goalOnly?"외형명을 입력하면 일치하는 무기·방어구만 표시됩니다. 저장한 외형은 ‘저장 목표만 보기’로 확인하세요.":goalOnly&&!saved.length?"저장한 목표 외형이 없습니다. 체크를 해제하고 외형을 검색해 저장하세요.":"일치하는 외형이 없습니다."));
  }
 }
 let composing=false;
 input.addEventListener("compositionstart",()=>{composing=true});
 input.addEventListener("compositionend",()=>{composing=false;query=input.value;visibleCount=12;updateResults()});
 input.addEventListener("input",e=>{
  if(composing||e.isComposing)return;
  query=input.value;visibleCount=12;updateResults();
 });
 check.onchange=()=>{goalOnly=check.checked;visibleCount=12;updateResults()};
 updateResults();
}
function renderArmor(d,refresh){
 const target=document.getElementById("relicArmorSeriesHost");if(!target)return;
 target.replaceChildren();
 const details=el("details","panel relic-series-panel");details.open=armorOpen;
 details.ontoggle=()=>{armorOpen=details.open};
 const sum=el("summary");sum.append(el("strong",null,"방어구 오리지널·도스·트라이 / A~F 세부 분류"),el("small",null,"일본 MH4G@wiki 표에 기재된 후보 · 확정 획득 아님"));details.append(sum);
 details.append(el("p","muted",d.armorSeriesGuide?.caution||"위키 원문에 미확정·예외가 있어 참고 후보로만 사용합니다."));
 const source=el("a",null,"일본 MH4G@wiki 자료 보기 ↗");source.href=d.armorSeriesGuide?.source||"#";source.target="_blank";source.rel="noopener noreferrer";details.append(source);
 const controls=el("div","relic-series-filters");
 for(const [options,value,set,label] of [[["all","오리지널","도스","트라이"],series,v=>{series=v;renderArmor(d,refresh)},"방어구 계열"],[["all","A","B","C","D","E","F"],letter,v=>{letter=v;renderArmor(d,refresh)},"A~F 분류"]]){
  const l=el("label",null,label),sel=el("select");for(const o of options){const opt=el("option",null,o==="all"?"전체":o);opt.value=o;opt.selected=o===value;sel.append(opt)}
  sel.onchange=()=>{armorOpen=true;set(sel.value)};l.append(sel);controls.append(l);
 }
 details.append(controls);
 const selected=document.getElementById("relicMonsterFilter")?.value;
 const g=(d.sealedGroups||[]).find(x=>x.monsters?.includes(selected));
 const groupIds=g?[Number(g.id)]:Array.from({length:11},(_,i)=>i+1);
 const grid=el("div","relic-series-grid");
 for(const r of (d.armorSeriesGuide?.rows||[]).filter(r=>(series==="all"||r.series===series)&&(letter==="all"||r.letter===letter))){
  const card=el("article","relic-series-card");card.append(el("h4",null,r.series+" · "+r.letter));
  for(const gid of groupIds){const line=el("div","relic-series-row");line.append(el("span",null,"그룹 "+gid));const content=el("div");
   for(const jp of r.groups?.[String(gid)]||[]){const n=el("span","relic-series-name");n.append(el("strong",null,d.armorAppearanceNamesKo?.[jp]||jp),el("small",null,jp));content.append(n)}
   line.append(content);card.append(line);
  }
  grid.append(card);
 }
 details.append(grid);target.append(details);
}
function renderFarm(d){
 let box=document.getElementById("relicFarmTarget");
 if(!box){const rewards=document.getElementById("relicPanel-rewards");if(!rewards)return;box=el("div","panel relic-farm-target");box.id="relicFarmTarget";rewards.prepend(box)}
 if(!farm){box.hidden=true;return}box.hidden=false;box.replaceChildren();
 box.append(el("strong",null,"목표 외형: "+farm.name),el("p","muted","그룹 "+farm.groups.join(", ")+" · 관련 길드퀘스트 몬스터: "+farm.monsters.join(" / ")),el("p","muted","아래 표는 길퀘 보상·파밍 참고자료입니다. 특정 외형의 획득 확률이나 확정 드롭을 의미하지 않습니다."));
}
export function enhanceRelicAppearance(d,refresh,changeTab){
 const panel=document.getElementById("relicPanel-appearance");if(!panel)return;
 let search=document.getElementById("relicReverseSearch");if(!search){search=el("section","panel relic-search-panel");search.id="relicReverseSearch";{const appearance=panel.querySelector(".relic-appearance-panel");if(appearance)appearance.after(search);else panel.insertBefore(search,panel.firstChild)}}
 let armor=document.getElementById("relicArmorSeriesHost");if(!armor){armor=el("div");armor.id="relicArmorSeriesHost";const directory=document.getElementById("relicAppearanceDirectory");panel.insertBefore(armor,directory)}
 renderSearch(d,refresh,changeTab);renderArmor(d,refresh);renderFarm(d);
}
