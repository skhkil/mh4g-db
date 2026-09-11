import {loadSimulatorData,loadFullData,FULL_DATA_KEYS,classifyImported} from "./data-loader.js?v=0.7.2";
import {PARTS,PART_NAMES,slotsText,calculateBuild,searchBuilds} from "./engine.js?v=0.7.2";

let data={skills:[],armors:[],armorSets:[],decorations:[],weapons:[],weaponSummary:[],melodies:[],items:[],meals:[],monsterSummary:[],monsterDetails:[],monsterRewards:[],dragonExchange:[],dragonSell:[],dragonIncrease:[],compositions:[],quests:[],siteInfo:{},meta:{}};
let targets=[];
let currentPage="simulator";
const BUILD_STORAGE_KEY="mh4g-builds-v1";
const WEAPON_TYPES=["대검","태도","한손검","쌍검","해머","수렵피리","랜스","건랜스","슬래시액스","차지액스","조충곤","라이트보우건","헤비보우건","활"];
const RANGED_TYPES=new Set(["라이트보우건","헤비보우건","활"]);
const MANUAL_CONTAINERS=["weapon",...PARTS,"charm"];
const uiState={
  targetActivation:"", manualSet:"", manualWeapon:"", manualWeaponType:"all",
  charmSkill1:"",charmPoint1:0,charmSkill2:"",charmPoint2:0,charmSlots:0,
  manual:Object.fromEntries(PARTS.map(p=>[p,""])),
  manualDecorations:Object.fromEntries(MANUAL_CONTAINERS.map(c=>[c,[]]))
};
let sourceView="main";
let armorViewMode="all";
let decoView="type";
let monsterView="summary";
let dragonView="exchange";
let questView="key";

// v0.7.2: 반복 배열 검색과 옵션 재생성을 줄이기 위한 인덱스/캐시
let skillById=new Map(),armorById=new Map(),weaponById=new Map(),decorationByIdMap=new Map(),armorSetById=new Map();
const optionCache={armorByPart:new Map(),weaponByType:new Map(),armorSets:null,skillPicker:null,activation:null,weaponTypes:null};
function rebuildIndexes(){
  skillById=new Map((data.skills||[]).map(x=>[x.id,x]));
  armorById=new Map((data.armors||[]).map(x=>[x.id,x]));
  weaponById=new Map((data.weapons||[]).map(x=>[x.id,x]));
  decorationByIdMap=new Map((data.decorations||[]).map(x=>[x.id,x]));
  armorSetById=new Map((data.armorSets||[]).map(x=>[x.id,x]));
  optionCache.armorByPart.clear();optionCache.weaponByType.clear();
  optionCache.armorSets=null;optionCache.skillPicker=null;optionCache.activation=null;optionCache.weaponTypes=null;
}

const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
const rankName=r=>({low:"하위",high:"상위",g:"G급",all:"전체"}[r]||r||"-");
const hunterName=t=>({blade:"검사",gunner:"거너",both:"공용"}[t]||t||"-");
const resistText=r=>`화 ${r?.fire??0} / 수 ${r?.water??0} / 뇌 ${r?.thunder??0} / 빙 ${r?.ice??0} / 용 ${r?.dragon??0}`;

const SKILL_SEARCH_ALIASES={
  "통격":"약점 약특 약점특효 회심 크리티컬",
  "달인":"회심 크리티컬 통찰력",
  "발도치명타":"회심 크리티컬 발도",
  "잠재력":"회심 크리티컬 힘의해방",
  "투혼":"회심 크리티컬 도전자",
  "광격내성":"회심 크리티컬 광룡 무아지경"
};
function cleanEffectText(text=""){return String(text||"").replace(/�+/g,"·").replace(/\s+/g," ").trim()}
function shortEffect(text="",max=54){const t=cleanEffectText(text);return t.length>max?t.slice(0,max-1)+"…":t}
function skillDefinition(id){return skillById.get(id)||null}
function skillName(id){return skillDefinition(id)?.name||id}
function skillSearchCorpus(skillOrId){
  const s=typeof skillOrId==="string"?skillDefinition(skillOrId):skillOrId;if(!s)return "";
  return [s.name,s.nameJa,SKILL_SEARCH_ALIASES[s.name]||"",...(s.activations||[]).flatMap(a=>[a.name,a.nameJa,a.description,Number(a.points)>0?`+${a.points}`:String(a.points)])].map(cleanEffectText).join(" ");
}
function decorationSearchCorpus(d){
  const positiveEffects=Object.entries(d.skills||{}).filter(([,v])=>Number(v)>0).map(([k])=>skillSearchCorpus(k)).join(" ");
  const allSkillNames=Object.keys(d.skills||{}).map(skillName).join(" ");
  return `${d.name||""} ${d.nameJa||""} ${allSkillNames} ${positiveEffects} ${d.materials||""}`;
}
function activationOptions(){
  if(optionCache.activation)return optionCache.activation;
  const rows=[];
  for(const skill of data.skills){
    for(const a of skill.activations||[]){
      if(Number(a.points)>0) rows.push({value:a.id,skillId:skill.id,label:`${a.name} (${a.points}P · ${skill.name})`,name:a.name,points:a.points,category:skill.name,meta:shortEffect(a.description),search:`${skillSearchCorpus(skill)} ${a.name} ${a.points}`});
    }
  }
  optionCache.activation=rows.sort((a,b)=>a.name.localeCompare(b.name,"ko"));
  return optionCache.activation;
}
function skillPickerOptions(){
  if(optionCache.skillPicker)return optionCache.skillPicker;
  optionCache.skillPicker=data.skills.map(s=>({value:s.id,label:s.name,search:skillSearchCorpus(s)})).sort((a,b)=>a.label.localeCompare(b.label,"ko"));
  return optionCache.skillPicker;
}
function currentSkillStatus(skillId,points){
  const def=skillDefinition(skillId),value=Number(points||0);
  if(!def)return {def:null,value,tone:value<0?"negative":"pending",active:null,next:null,effect:""};
  const acts=[...(def.activations||[])].sort((a,b)=>Number(a.points)-Number(b.points));
  let active=null,next=null;
  if(value>=0){
    for(const a of acts)if(Number(a.points)>0&&value>=Number(a.points))active=a;
    next=acts.filter(a=>Number(a.points)>value).find(a=>Number(a.points)>0)||null;
  }else{
    for(const a of acts.filter(a=>Number(a.points)<0).sort((a,b)=>Number(b.points)-Number(a.points)))if(value<=Number(a.points))active=a;
    next=active?null:acts.filter(a=>Number(a.points)<0).sort((a,b)=>Number(b.points)-Number(a.points))[0]||null;
  }
  const tone=value<0?"negative":active&&Number(active.points)>0?"active":"pending";
  const source=active||next;
  return {def,value,tone,active,next,effect:cleanEffectText(source?.description||"")};
}

function mountSearchSelect(selector,options,{value="",placeholder="검색 또는 선택",emptyLabel="선택 안 함",onChange=()=>{}}={}){
  const root=typeof selector==="string"?$(selector):selector;
  if(!root) return;
  const selected=options.find(o=>o.value===value);
  for(const o of options) if(!o._searchLower) o._searchLower=`${o.label} ${o.search||""}`.toLowerCase();
  root.innerHTML=`<div class="search-select-control"><input class="search-select-input" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" placeholder="${esc(placeholder)}" value="${esc(selected?.label||"")}"/><button type="button" class="search-select-toggle" title="목록 펼치기">⌄</button></div><div class="search-select-menu" role="listbox"></div>`;
  const input=root.querySelector(".search-select-input"),menu=root.querySelector(".search-select-menu"),toggle=root.querySelector(".search-select-toggle");
  root.dataset.value=value||"";
  let filtered=[];
  let highlightedIndex=-1;

  const optionButtons=()=>[...menu.querySelectorAll('.search-select-option:not(.empty-option)')];
  const setHighlight=(index,{scroll=true}={})=>{
    const buttons=optionButtons();
    if(!buttons.length){highlightedIndex=-1;return;}
    highlightedIndex=Math.max(0,Math.min(index,buttons.length-1));
    buttons.forEach((btn,i)=>{
      const active=i===highlightedIndex;
      btn.classList.toggle('keyboard-active',active);
      btn.setAttribute('aria-selected',active?'true':'false');
    });
    if(scroll) buttons[highlightedIndex]?.scrollIntoView({block:'nearest'});
  };
  const closeMenu=()=>{
    menu.classList.remove("open");root.classList.remove("open");
    input.setAttribute('aria-expanded','false');highlightedIndex=-1;
  };
  const draw=(query="",{preserveHighlight=false}={})=>{
    closePickers(root);
    const q=query.trim().toLowerCase();
    filtered=options.filter(o=>!q||o._searchLower.includes(q)).slice(0,120);
    menu.innerHTML=`<button type="button" class="search-select-option empty-option" data-value="">${esc(emptyLabel)}</button>`+
      (filtered.length?filtered.map((o,i)=>`<button type="button" class="search-select-option ${o.value===root.dataset.value?"selected":""}" data-value="${esc(o.value)}" data-index="${i}" role="option"><span class="search-select-label">${esc(o.label)}</span>${o.meta?`<small>${esc(o.meta)}</small>`:""}</button>`).join(""):'<div class="search-select-noresult">검색 결과 없음</div>');
    menu.classList.add("open");root.classList.add("open");input.setAttribute('aria-expanded','true');
    if(!preserveHighlight) highlightedIndex=-1;
    menu.querySelectorAll(".search-select-option").forEach(btn=>{
      btn.onclick=e=>{
        e.preventDefault();e.stopPropagation();
        const v=btn.dataset.value||"",opt=options.find(o=>o.value===v);
        root.dataset.value=v;input.value=opt?.label||"";closeMenu();onChange(v,opt);
      };
      if(!btn.classList.contains('empty-option')){
        btn.onmouseenter=()=>{
          const buttons=optionButtons();
          const idx=buttons.indexOf(btn);
          if(idx>=0)setHighlight(idx,{scroll:false});
        };
      }
    });
  };
  input.onfocus=()=>{input.select();draw("")};
  input.onclick=e=>{e.stopPropagation();draw(input.value===selected?.label?"":input.value)};
  input.oninput=()=>{highlightedIndex=-1;draw(input.value)};
  input.onkeydown=e=>{
    if(e.key==="Escape"){e.preventDefault();closeMenu();input.value=options.find(o=>o.value===root.dataset.value)?.label||"";return;}
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){
      e.preventDefault();
      if(!menu.classList.contains("open")) draw(input.value===selected?.label?"":input.value);
      const buttons=optionButtons();
      if(!buttons.length)return;
      if(e.key==="ArrowDown") setHighlight(highlightedIndex<0?0:(highlightedIndex+1)%buttons.length);
      else setHighlight(highlightedIndex<0?buttons.length-1:(highlightedIndex-1+buttons.length)%buttons.length);
      return;
    }
    if(e.key==="Home"&&menu.classList.contains("open")){e.preventDefault();setHighlight(0);return;}
    if(e.key==="End"&&menu.classList.contains("open")){e.preventDefault();setHighlight(optionButtons().length-1);return;}
    if(e.key==="Enter"&&menu.classList.contains("open")){
      e.preventDefault();
      const buttons=optionButtons();
      const target=highlightedIndex>=0?buttons[highlightedIndex]:buttons[0];
      if(target)target.click();
    }
  };
  toggle.onclick=e=>{e.stopPropagation(); if(menu.classList.contains("open")){closeMenu()}else{input.focus();draw("")}};
}
function pickerValue(selector){return $(selector)?.dataset.value||""}
function closePickers(exceptRoot=null){
  $$('.search-select.open').forEach(r=>{
    if(r===exceptRoot) return;
    r.classList.remove('open');
    r.querySelector('.search-select-menu')?.classList.remove('open');
  });
}

function fillSelectors(){
  mountSearchSelect("#targetSkillPicker",activationOptions(),{value:uiState.targetActivation,placeholder:"발동 스킬·효과 검색 (예: 회심, 귀마개)",emptyLabel:"선택 안 함",onChange:v=>uiState.targetActivation=v});
  const currentType=$("#weaponTypeFilter")?.value||"all";
  if($("#weaponTypeFilter")){
    $("#weaponTypeFilter").innerHTML='<option value="all">전체 무기</option>'+WEAPON_TYPES.filter(t=>data.weapons.some(w=>w.weaponType===t)).map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
    if([...$("#weaponTypeFilter").options].some(o=>o.value===currentType)) $("#weaponTypeFilter").value=currentType;
  }
  renderWeaponSubNav();
  if($("#weaponSummaryType")){
    const old=$("#weaponSummaryType").value||"all";
    $("#weaponSummaryType").innerHTML='<option value="all">전체 무기</option>'+WEAPON_TYPES.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
    $("#weaponSummaryType").value=WEAPON_TYPES.includes(old)?old:"all";
  }
  populateMealIngredientFilter();
  populateMonsterSelect();populateQuestLevels();
}
function populateMealIngredientFilter(){
  const el=$("#mealIngredientFilter");if(!el)return;
  const old=el.value||"all";
  const ingredients=[...new Set((data.meals||[]).flatMap(x=>[x.ingredient1,x.ingredient2]))].filter(Boolean);
  el.innerHTML='<option value="all">전체 식재료</option>'+ingredients.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
  el.value=ingredients.includes(old)?old:"all";
}
function charm(){
  const skills={};
  if(uiState.charmSkill1) skills[uiState.charmSkill1]=Number(uiState.charmPoint1||0);
  if(uiState.charmSkill2) skills[uiState.charmSkill2]=(skills[uiState.charmSkill2]||0)+Number(uiState.charmPoint2||0);
  return {skills,slots:Number(uiState.charmSlots||0)};
}
function getSavedBuilds(){try{const v=JSON.parse(localStorage.getItem(BUILD_STORAGE_KEY)||"[]");return Array.isArray(v)?v:[]}catch{return []}}
function setSavedBuilds(list){localStorage.setItem(BUILD_STORAGE_KEY,JSON.stringify(list))}
function renderSavedBuilds(selectedId=""){
  const el=$("#savedBuildSelect"); if(!el)return;
  const list=getSavedBuilds();
  el.innerHTML='<option value="">저장한 세팅</option>'+list.map(b=>`<option value="${esc(b.id)}" ${b.id===selectedId?"selected":""}>${esc(b.name)}</option>`).join("");
}
function saveCurrentBuild(){
  const list=getSavedBuilds(),name=$("#buildName")?.value.trim()||`세팅 ${list.length+1}`;
  const rec={
    id:`build_${Date.now()}_${Math.random().toString(36).slice(2,7)}`,name,
    targets:[...targets],
    manualSet:uiState.manualSet,manualWeapon:uiState.manualWeapon,manualWeaponType:uiState.manualWeaponType,manual:{...uiState.manual},
    charmSkill1:uiState.charmSkill1,charmPoint1:uiState.charmPoint1,charmSkill2:uiState.charmSkill2,charmPoint2:uiState.charmPoint2,charmSlots:uiState.charmSlots,
    manualDecorations:Object.fromEntries(MANUAL_CONTAINERS.map(c=>[c,[...(uiState.manualDecorations[c]||[])]]))
  };
  list.push(rec);setSavedBuilds(list);renderSavedBuilds(rec.id);if($("#buildName"))$("#buildName").value="";
}
function loadSelectedBuild(){
  const rec=getSavedBuilds().find(x=>x.id===$("#savedBuildSelect")?.value);if(!rec)return;
  targets=[...(rec.targets||[])];
  uiState.manualSet=rec.manualSet||"";uiState.manualWeapon=rec.manualWeapon||"";uiState.manualWeaponType=rec.manualWeaponType||"all";uiState.manual={...Object.fromEntries(PARTS.map(p=>[p,""])),...(rec.manual||{})};
  uiState.charmSkill1=rec.charmSkill1||"";uiState.charmPoint1=Number(rec.charmPoint1||0);uiState.charmSkill2=rec.charmSkill2||"";uiState.charmPoint2=Number(rec.charmPoint2||0);uiState.charmSlots=Number(rec.charmSlots||0);
  uiState.manualDecorations=Object.fromEntries(MANUAL_CONTAINERS.map(c=>[c,[...(rec.manualDecorations?.[c]||[])]]));
  fillSelectors();renderTargets();renderManualSelectors();renderManualResult();
}
function deleteSelectedBuild(){const id=$("#savedBuildSelect")?.value;if(!id)return;setSavedBuilds(getSavedBuilds().filter(x=>x.id!==id));renderSavedBuilds()}

function rankEligible(x){const rank=$("#rankFilter").value;return rank==="all"||x.rank===rank}
function armorEligible(a){
  const hunter=$("#hunterType").value;
  return (hunter==="both"||a.hunterType==="both"||a.hunterType===hunter)&&rankEligible(a);
}
function weaponEligible(w){
  const hunter=$("#hunterType").value;
  const isRanged=RANGED_TYPES.has(w.weaponType);
  const typeOk=hunter==="both"||(hunter==="gunner"?isRanged:!isRanged);
  return typeOk&&rankEligible(w);
}
function selectedArmors(){return PARTS.map(p=>armorById.get(uiState.manual[p])).filter(Boolean)}
function selectedWeapon(){return weaponById.get(uiState.manualWeapon)||null}
// 시뮬레이터는 DB 메뉴의 숨겨진 타입/등급 상태와 완전히 독립적으로 동작한다.
function armorPickerOptions(part){
  if(optionCache.armorByPart.has(part))return optionCache.armorByPart.get(part);
  const opts=data.armors.filter(a=>a.part===part).sort((a,b)=>a.name.localeCompare(b.name,"ko")).map(a=>({value:a.id,label:a.name,meta:`${hunterName(a.hunterType)} · ${rankName(a.rank)} · ${slotsText(a.slots)} · DEF ${a.defense}`,search:`${a.name} ${a.nameJa||""} ${hunterName(a.hunterType)} ${rankName(a.rank)} ${Object.keys(a.skills||{}).map(skillName).join(" ")} ${a.materials||""}`}));
  optionCache.armorByPart.set(part,opts);return opts;
}
function manualWeaponTypeOptions(){
  if(optionCache.weaponTypes)return optionCache.weaponTypes;
  optionCache.weaponTypes=WEAPON_TYPES.filter(t=>data.weapons.some(w=>w.weaponType===t));return optionCache.weaponTypes;
}
function weaponPickerOptions(){
  const type=uiState.manualWeaponType||"all";
  if(optionCache.weaponByType.has(type))return optionCache.weaponByType.get(type);
  const opts=data.weapons.filter(w=>type==="all"||w.weaponType===type).sort((a,b)=>a.weaponType.localeCompare(b.weaponType,"ko")||a.name.localeCompare(b.name,"ko")).map(w=>({value:w.id,label:`[${w.weaponType}] ${w.name}`,meta:`${rankName(w.rank)} · ${slotsText(w.slots)} · ATK ${w.attack??"-"}`,search:`${w.name} ${w.nameJa||""} ${w.weaponType} ${rankName(w.rank)} ${w.tree||""} ${w.element||""}`}));
  optionCache.weaponByType.set(type,opts);return opts;
}
function armorSetPickerOptions(){
  if(optionCache.armorSets)return optionCache.armorSets;
  optionCache.armorSets=data.armorSets.slice().sort((a,b)=>a.name.localeCompare(b.name,"ko")).map(s=>({value:s.id,label:s.name,meta:`${hunterName(s.hunterType)} · ${rankName(s.rank)} · 슬롯 ${Number(s.slots||0)}칸`,search:`${s.name} ${hunterName(s.hunterType)} ${rankName(s.rank)} ${Object.keys(s.skills||{}).map(skillName).join(" ")}`}));
  return optionCache.armorSets;
}
function simulatorSearchHunterType(){
  const type=selectedWeapon()?.weaponType || (uiState.manualWeaponType!=="all"?uiState.manualWeaponType:"");
  return type ? (RANGED_TYPES.has(type)?"gunner":"blade") : "blade";
}
function containerCapacity(container){
  if(container==="weapon")return Number(selectedWeapon()?.slots||0);
  if(container==="charm")return Number(uiState.charmSlots||0);
  const a=armorById.get(uiState.manual[container]);return Number(a?.slots||0);
}
function decorationById(id){return decorationByIdMap.get(id)}
function skillPointEntries(points={}){
  return Object.entries(points||{}).filter(([,v])=>Number(v)!==0).sort((a,b)=>{
    const dv=Math.abs(Number(b[1]))-Math.abs(Number(a[1]));
    return dv||skillName(a[0]).localeCompare(skillName(b[0]),"ko");
  });
}
function mergePointMaps(...maps){
  const out={};
  for(const map of maps){
    for(const [id,v] of Object.entries(map||{})) out[id]=(out[id]||0)+Number(v||0);
  }
  return out;
}
function scalePointMap(points={},mul=1){
  return Object.fromEntries(Object.entries(points||{}).map(([id,v])=>[id,Number(v||0)*mul]));
}
function decorationPointsForContainer(container,{effective=true}={}){
  let points={};
  for(const id of uiState.manualDecorations[container]||[]){
    const d=decorationById(id);points=mergePointMaps(points,d?.skills||{});
  }
  if(effective&&container==="body"&&$("#includeTorsoUp")?.checked!==false){
    const torsoUpCount=selectedArmors().filter(a=>a?.part!=="body"&&a?.torsoUp).length;
    if(torsoUpCount) points=scalePointMap(points,1+torsoUpCount);
  }
  return points;
}
function torsoUpMultiplier(){
  if($("#includeTorsoUp")?.checked===false)return 1;
  return 1+selectedArmors().filter(a=>a?.part!=="body"&&a?.torsoUp).length;
}
function containerSkillPoints(container,{effective=true}={}){
  let points={};
  if(container==="charm") points={...charm().skills};
  else if(container!=="weapon") points={...(armorById.get(uiState.manual[container])?.skills||{})};
  if(effective&&container==="body"){
    const mul=torsoUpMultiplier();
    if(mul>1) points=scalePointMap(points,mul);
  }
  return points;
}
function allDecorationSkillPoints(){
  return MANUAL_CONTAINERS.reduce((acc,c)=>mergePointMaps(acc,decorationPointsForContainer(c,{effective:true})),{});
}
function skillPointsPlain(points={},empty="-"){
  const entries=skillPointEntries(points);
  return entries.length?entries.map(([id,v])=>`${skillName(id)} ${Number(v)>0?"+":""}${v}`).join(" · "):empty;
}
function containerSkillText(container,empty="스킬 없음"){
  const base=skillPointsPlain(containerSkillPoints(container),empty);
  const mul=container==="body"?torsoUpMultiplier():1;
  return mul>1&&base!==empty?`${base} · 몸통×${mul}`:base;
}
function skillPointsHtml(points={},className="equipment-skill-points",empty="스킬 없음",suffix=""){
  const base=skillPointsPlain(points,empty),text=suffix&&base!==empty?`${base}${suffix}`:base;
  return `<span class="${className} ${base===empty?"is-empty":""}" title="${esc(text)}">${esc(text)}</span>`;
}
function refreshManualSkillPointDisplays(){
  for(const container of MANUAL_CONTAINERS){
    const card=$("#deco-editor-"+container)?.closest(".manual-equipment-card");
    const el=card?.querySelector(".equipment-skill-points");
    if(!el)continue;
    const text=containerSkillText(container,"스킬 없음");
    el.textContent=text;el.title=text;el.classList.toggle("is-empty",text==="스킬 없음");
  }
}
function usedDecorationSlots(container){return (uiState.manualDecorations[container]||[]).reduce((n,id)=>n+Number(decorationById(id)?.slots||0),0)}
function pruneDecorations(container){
  const cap=containerCapacity(container);let used=0,keep=[];
  for(const id of uiState.manualDecorations[container]||[]){const cost=Number(decorationById(id)?.slots||0);if(cost>0&&used+cost<=cap){keep.push(id);used+=cost}}
  uiState.manualDecorations[container]=keep;
}
function manualDecorationPlacements(){
  return MANUAL_CONTAINERS.flatMap(container=>(uiState.manualDecorations[container]||[]).map(id=>({deco:id,container})));
}
function decoPickerOptions(container){
  const remain=containerCapacity(container)-usedDecorationSlots(container);
  return data.decorations.filter(d=>Number(d.slots||0)>0&&Number(d.slots||0)<=remain).sort((a,b)=>Number(a.slots)-Number(b.slots)||a.name.localeCompare(b.name,"ko")).map(d=>({value:d.id,label:d.name,meta:`${d.slots}칸 · ${Object.entries(d.skills||{}).map(([k,v])=>`${skillName(k)} ${v>0?"+":""}${v}`).join(", ")}`,search:decorationSearchCorpus(d)}));
}
function refreshManualContainer(container){mountDecorationEditor(container);refreshManualSkillPointDisplays()}
function addManualDecoration(container,id){
  if(!id)return;const d=decorationById(id);if(!d)return;
  if(usedDecorationSlots(container)+Number(d.slots||0)>containerCapacity(container))return;
  uiState.manualDecorations[container].push(id);refreshManualContainer(container);renderManualResult();
}
function removeManualDecoration(container,index){uiState.manualDecorations[container].splice(index,1);refreshManualContainer(container);renderManualResult()}
function decorationEditorHtml(container){
  const cap=containerCapacity(container),used=usedDecorationSlots(container),list=uiState.manualDecorations[container]||[];
  const chips=list.map((id,i)=>{const d=decorationById(id);return `<span class="deco-chip">${esc(d?.name||id)} <small>${d?.slots||0}</small><button type="button" data-remove-deco="${container}:${i}">×</button></span>`}).join("");
  const slotState=`<span class="deco-slot-summary ${used>cap?'over':''}">슬롯 ${slotsText(cap)} · ${used}/${cap}</span>`;
  const picker=cap<=0?'<span class="deco-full">장식주 장착 불가</span>':cap>used?`<div id="deco-picker-${container}" class="search-select deco-picker"></div>`:'<span class="deco-full">슬롯 사용 완료</span>';
  return `<div class="manual-deco-line">${slotState}<div class="deco-chip-list">${chips||'<span class="muted deco-empty">장식주 없음</span>'}</div>${picker}</div>`;
}
function mountDecorationEditor(container){
  const box=$("#deco-editor-"+container);if(!box)return;pruneDecorations(container);box.innerHTML=decorationEditorHtml(container);
  box.querySelectorAll('[data-remove-deco]').forEach(b=>b.onclick=()=>{const [c,i]=b.dataset.removeDeco.split(':');removeManualDecoration(c,Number(i))});
  if(containerCapacity(container)>usedDecorationSlots(container))mountSearchSelect(`#deco-picker-${container}`,decoPickerOptions(container),{placeholder:"장식주·스킬효과 검색",emptyLabel:"취소",onChange:v=>addManualDecoration(container,v)});
}
function applyArmorSet(id){
  uiState.manualSet=id||"";const set=armorSetById.get(id);if(!set){renderManualSelectors();renderManualResult();return}
  for(const p of PARTS){uiState.manual[p]=set.pieces?.find(x=>x.part===p)?.id||"";uiState.manualDecorations[p]=[]}
  renderManualSelectors();renderManualResult();
}
function equipmentCard(label,container,pickerId,extra=""){
  return `<div class="manual-equipment-card"><div class="manual-equipment-main"><span class="equipment-label">${label}</span><div id="${pickerId}" class="search-select"></div>${extra}${skillPointsHtml(containerSkillPoints(container),"equipment-skill-points","스킬 없음",container==="body"&&torsoUpMultiplier()>1?` · 몸통×${torsoUpMultiplier()}`:"")}</div><div id="deco-editor-${container}" class="manual-deco-editor"></div></div>`;
}
function mountManualWeaponSearch(){
  const wopts=weaponPickerOptions();
  mountSearchSelect("#manual-weapon",wopts,{value:uiState.manualWeapon,placeholder:`무기 검색 (${wopts.length}개)`,emptyLabel:"무기 선택 안 함",onChange:v=>{
    uiState.manualWeapon=v;uiState.manualDecorations.weapon=[];refreshManualContainer("weapon");renderManualResult();
  }});
}
function renderManualSelectors(){
  for(const p of PARTS){if(uiState.manual[p]&&(!armorById.has(uiState.manual[p])||armorById.get(uiState.manual[p])?.part!==p))uiState.manual[p]=""}
  if(uiState.manualWeapon&&(!weaponById.has(uiState.manualWeapon)||(uiState.manualWeaponType!=="all"&&selectedWeapon()?.weaponType!==uiState.manualWeaponType)))uiState.manualWeapon="";
  MANUAL_CONTAINERS.forEach(pruneDecorations);
  const setOpts=armorSetPickerOptions();
  if(uiState.manualSet&&!setOpts.some(x=>x.value===uiState.manualSet))uiState.manualSet="";
  mountSearchSelect("#armorSetPicker",setOpts,{value:uiState.manualSet,placeholder:`방어구 세트 검색 (${setOpts.length}개)`,emptyLabel:"세트 선택 안 함",onChange:v=>applyArmorSet(v)});

  const box=$("#manualEquipmentBuilder");
  box.innerHTML=
    `<div class="manual-equipment-card weapon-card"><div class="manual-equipment-main"><span class="equipment-label">무기</span><div class="manual-weapon-picker-row"><select id="manualWeaponTypeFilter" class="manual-weapon-type-filter" aria-label="시뮬레이터 무기 종류"><option value="all">전체 무기</option>${manualWeaponTypeOptions().map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("")}</select><div id="manual-weapon" class="search-select"></div></div>${skillPointsHtml(containerSkillPoints("weapon"),"equipment-skill-points")}</div><div id="deco-editor-weapon" class="manual-deco-editor"></div></div>`+
    PARTS.map(p=>equipmentCard(PART_NAMES[p],p,`manual-${p}`)).join("")+
    `<div class="manual-equipment-card charm-card"><div class="manual-equipment-main charm-main"><span class="equipment-label">호석</span><div class="manual-charm-inline"><span class="inline-field-label">스킬1</span><div id="charmSkill1Picker" class="search-select compact"></div><input id="charmPoint1" class="charm-point" type="number" min="-20" max="20" value="${uiState.charmPoint1}" /><span class="inline-field-label">스킬2</span><div id="charmSkill2Picker" class="search-select compact"></div><input id="charmPoint2" class="charm-point" type="number" min="-20" max="20" value="${uiState.charmPoint2}" /><span class="inline-field-label">슬롯</span><select id="charmSlots" class="charm-slot-select"><option value="0">---</option><option value="1">O--</option><option value="2">OO-</option><option value="3">OOO</option></select></div>${skillPointsHtml(containerSkillPoints("charm"),"equipment-skill-points")}</div><div id="deco-editor-charm" class="manual-deco-editor"></div></div>`;

  const manualTypeEl=$("#manualWeaponTypeFilter");
  if(manualTypeEl){
    const availableTypes=manualWeaponTypeOptions();
    manualTypeEl.value=availableTypes.includes(uiState.manualWeaponType)?uiState.manualWeaponType:"all";
    uiState.manualWeaponType=manualTypeEl.value;
    manualTypeEl.onchange=e=>{
      uiState.manualWeaponType=e.target.value||"all";
      const current=selectedWeapon();
      if(current&&uiState.manualWeaponType!=="all"&&current.weaponType!==uiState.manualWeaponType){
        uiState.manualWeapon="";uiState.manualDecorations.weapon=[];
      }
      mountManualWeaponSearch();refreshManualContainer("weapon");renderManualResult();
    };
  }
  mountManualWeaponSearch();
  for(const p of PARTS){
    const opts=armorPickerOptions(p);
    mountSearchSelect(`#manual-${p}`,opts,{value:uiState.manual[p],placeholder:`${PART_NAMES[p]} 검색 (${opts.length}개)`,emptyLabel:`선택 안 함 (${opts.length}개)`,onChange:v=>{
      uiState.manual[p]=v;uiState.manualDecorations[p]=[];refreshManualContainer(p);renderManualResult();
    }});
  }
  mountSearchSelect("#charmSkill1Picker",skillPickerOptions(),{value:uiState.charmSkill1,placeholder:"스킬 검색",emptyLabel:"없음",onChange:v=>{uiState.charmSkill1=v;renderManualResult()}});
  mountSearchSelect("#charmSkill2Picker",skillPickerOptions(),{value:uiState.charmSkill2,placeholder:"스킬 검색",emptyLabel:"없음",onChange:v=>{uiState.charmSkill2=v;renderManualResult()}});
  $("#charmPoint1").oninput=e=>{uiState.charmPoint1=Number(e.target.value||0);renderManualResult()};
  $("#charmPoint2").oninput=e=>{uiState.charmPoint2=Number(e.target.value||0);renderManualResult()};
  $("#charmSlots").value=String(uiState.charmSlots||0);$("#charmSlots").onchange=e=>{uiState.charmSlots=Number(e.target.value||0);pruneDecorations("charm");refreshManualContainer("charm");renderManualResult()};
  MANUAL_CONTAINERS.forEach(mountDecorationEditor);
}

function renderSkillResult(calc){
  const active=calc.activated.length?calc.activated.map(a=>{const st=currentSkillStatus(a.skillId,a.points);return `<span class="skill-active ${a.threshold<0?"skill-negative":""}" title="${esc(st.effect)}">${esc(a.name)}</span>`}).join(""):'<span class="muted">발동 스킬 없음</span>';
  const rows=Object.entries(calc.points).sort((a,b)=>{
    const sa=currentSkillStatus(a[0],a[1]),sb=currentSkillStatus(b[0],b[1]);
    const order={active:0,pending:1,negative:2};return order[sa.tone]-order[sb.tone]||Number(b[1])-Number(a[1])||skillName(a[0]).localeCompare(skillName(b[0]),"ko");
  }).map(([id,p])=>{
    const st=currentSkillStatus(id,p),shown=st.active||st.next;
    const trigger=shown?`${Number(shown.points)>0?"+":""}${shown.points}P`:"";
    let applied="미발동",effect="발동 조건이 없습니다.";
    if(st.active){applied=`<strong>${esc(st.active.name)}</strong><small>${trigger} 발동</small>`;effect=st.effect||"효과 설명 없음"}
    else if(st.next&&st.tone==="pending"){applied=`<span>미발동</span><small>다음 ${trigger} → ${esc(st.next.name)}</small>`;effect=st.effect?`다음 효과: ${st.effect}`:"다음 발동 효과 설명 없음"}
    else if(st.next&&st.tone==="negative"){applied=`<span>마이너스 포인트</span><small>${trigger} 이하 → ${esc(st.next.name)}</small>`;effect=st.effect?`주의: ${st.effect}`:"마이너스 포인트"}
    else if(st.tone==="negative"){applied="<span>마이너스 포인트</span>";effect="현재 스킬 포인트가 음수입니다."}
    return `<tr class="skill-result-row skill-state-${st.tone}"><td class="skill-tree-cell">${esc(skillName(id))}</td><td class="skill-point-cell"><span class="skill-point-badge">${p>0?"+":""}${p}</span></td><td class="skill-activation-cell">${applied}</td><td class="skill-effect-cell">${esc(effect)}</td></tr>`;
  }).join("");
  return `<div class="skill-summary">${active}</div><div class="muted">방어력 ${calc.defense} · ${resistText(calc.resist)} · 몸통배가 ${calc.torsoUpCount}개</div><div class="skill-result-table-wrap"><table class="skill-points"><colgroup><col class="col-tree"><col class="col-point"><col class="col-active"><col class="col-effect"></colgroup><thead><tr><th>스킬 계통</th><th>포인트</th><th>발동 스킬</th><th>효과</th></tr></thead><tbody>${rows||'<tr><td colspan="4" class="skill-empty-row">포인트 없음</td></tr>'}</tbody></table></div>`;
}
function manualLoadoutSummary(){
  const w=selectedWeapon();
  const torsoUpCount=$("#includeTorsoUp")?.checked!==false?selectedArmors().filter(a=>a?.part!=="body"&&a?.torsoUp).length:0;
  const skillCell=(container)=>{
    const pts=containerSkillPoints(container);
    const note=container==="body"&&torsoUpCount?` <small class="torso-mult">몸통×${1+torsoUpCount}</small>`:"";
    return `<span class="loadout-skill-points">${esc(skillPointsPlain(pts,"-"))}${note}</span>`;
  };
  const gear=[`<div><b>무기</b><span>${esc(w?.name||"-")} ${w?`<small>${slotsText(w.slots)}</small>`:""}</span>${skillCell("weapon")}</div>`];
  for(const p of PARTS){
    const a=armorById.get(uiState.manual[p]);
    gear.push(`<div><b>${PART_NAMES[p]}</b><span>${esc(a?.name||"-")} ${a?`<small>${slotsText(a.slots)}</small>`:""}</span>${skillCell(p)}</div>`);
  }
  const decoCount=manualDecorationPlacements().length;
  const charmText=`${uiState.charmSkill1?`${esc(skillName(uiState.charmSkill1))} ${uiState.charmPoint1>0?"+":""}${uiState.charmPoint1}`:"-"}${uiState.charmSkill2?` / ${esc(skillName(uiState.charmSkill2))} ${uiState.charmPoint2>0?"+":""}${uiState.charmPoint2}`:""} <small>${slotsText(uiState.charmSlots)}</small>`;
  return `<div class="manual-loadout-summary"><div class="loadout-summary-head"><b>구분</b><span>선택 장비 / 슬롯</span><span>파츠별 스킬 포인트</span></div>${gear.join("")}<div><b>호석</b><span>${charmText}</span>${skillCell("charm")}</div><div><b>장식주</b><span>${decoCount}개 장착</span><span class="loadout-skill-points">${esc(skillPointsPlain(allDecorationSkillPoints(),"-"))}</span></div></div>`;
}
function renderManualResult(){
  if(!$("#manualResult"))return;
  refreshManualSkillPointDisplays();
  const w=selectedWeapon(),decos=manualDecorationPlacements();
  const calc=calculateBuild({armors:selectedArmors(),charm:charm(),weaponSlots:Number(w?.slots||0),decorations:decos},data,$("#includeTorsoUp")?.checked!==false);
  $("#manualResult").innerHTML=manualLoadoutSummary()+renderSkillResult(calc);
}
function renderTargets(){
  const box=$("#targetSkills");if(!targets.length){box.className="chip-list empty-state";box.textContent="선택된 스킬이 없습니다.";return}
  box.className="chip-list";const opts=activationOptions();box.innerHTML=targets.map(id=>{const a=opts.find(x=>x.value===id);return `<span class="chip">${esc(a?.name||id)} <button data-remove-target="${esc(id)}">×</button></span>`}).join("");
  $$('[data-remove-target]').forEach(b=>b.onclick=()=>{targets=targets.filter(x=>x!==b.dataset.removeTarget);renderTargets()});
}
function renderBuildCard(b,i){
  const decolines={};for(const p of b.decorations){const key=`${p.container}:${p.deco.id}`;decolines[key]=(decolines[key]||0)+1}
  const decoText=Object.entries(decolines).map(([key,n])=>{const [container,id]=key.split(":"),d=data.decorations.find(x=>x.id===id),label={weapon:"무기",head:"머리",body:"몸통",arms:"팔",waist:"허리",legs:"다리",charm:"호석"}[container]||container;return `${label} ${d?.name||id} ×${n}`}).join(" · ");
  return `<article class="build-card"><h3><span>조합 ${i+1}</span><span class="score">DEF ${b.calc.defense}</span></h3><div class="build-equipment">${PARTS.map(p=>{const a=b.armors.find(x=>x.part===p);return `<span class="label">${PART_NAMES[p]}</span><span>${esc(a?.name||"-")} <span class="slots">${slotsText(a?.slots)}</span></span>`}).join("")}</div><div class="deco-line">${decoText?`장식주: ${esc(decoText)}`:"장식주 없음"}</div>${renderSkillResult(b.calc)}</article>`;
}
async function runSearch(){
  if(!targets.length){$("#searchResults").innerHTML='<div class="result-empty">먼저 원하는 스킬을 추가하세요.</div>';return}
  const btn=$("#runSearch");btn.disabled=true;btn.textContent="검색 중…";$("#searchStats").textContent="실제 DB에서 후보 조합을 계산하고 있습니다.";
  try{
    const simHunter=simulatorSearchHunterType();
    const r=await searchBuilds({targetActivationIds:targets,hunterType:simHunter,rank:"all",charm:charm(),weaponSlots:Number(selectedWeapon()?.slots||0),allowDecorations:$("#allowDecorations").checked,includeTorsoUp:$("#includeTorsoUp").checked,limit:Number($("#resultLimit").value||20)},data);
    $("#searchStats").textContent=r.stats.message||`검색 타입 ${hunterName(simHunter)} · 전체 등급 · 대상 방어구 ${r.stats.eligible}개 · 최종 후보 ${r.stats.finalists}개 · 고속 후보검색(완전탐색 아님)`;
    $("#searchResults").innerHTML=r.results.length?r.results.map(renderBuildCard).join(""):'<div class="result-empty">조건을 만족하는 조합을 찾지 못했습니다.</div>';
  }finally{btn.disabled=false;btn.textContent="조합 검색"}
}

function renderTable(el,headers,rows){$(el).innerHTML=`<table class="data-table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.length?rows.join(""):`<tr><td colspan="${headers.length}" class="result-empty">검색 결과 없음</td></tr>`}</tbody></table>`}
function renderArmorTable(){
  const q=$("#armorSearch").value.trim().toLowerCase(),part=$("#armorPartFilter").value;
  const rows=data.armors.filter(a=>(part==="all"||a.part===part)&&armorEligible(a)&&(armorViewMode!=="other"||(a.source||"").endsWith("/armor/etc.htm"))).filter(a=>!q||`${a.name} ${a.nameJa||""} ${Object.keys(a.skills||{}).map(skillName).join(" ")} ${a.materials||""}`.toLowerCase().includes(q)).map(a=>`<tr><td>${esc(a.name)}</td><td>${hunterName(a.hunterType)}</td><td>${PART_NAMES[a.part]||a.part}</td><td>${a.rare||"-"}</td><td>${a.defense||0} / ${a.maxDefense||a.defense||0}</td><td class="slots">${slotsText(a.slots)}</td><td>${a.torsoUp?"몸통배가":Object.entries(a.skills||{}).map(([k,v])=>`${esc(skillName(k))} ${v>0?"+":""}${v}`).join(", ")}</td><td>${resistText(a.resistances)}</td><td>${rankName(a.rank)}</td></tr>`);
  renderTable("#armorTable",["명칭","타입","부위","RARE","방어(초기/최대)","슬롯","스킬","내성","등급"],rows);
}

function sharpnessBar(bar,maxTotal){
  if(!bar?.segments?.length)return '<span class="sharpness-missing">원본 미기재</span>';
  return `<div class="sharpness-gauge" title="게이지 ${bar.total||maxTotal}">${bar.segments.map(seg=>`<span class="sharp-seg sharp-${esc(seg.color)}" style="flex:${Number(seg.length)||0} 0 0"></span>`).join("")}${bar.total<maxTotal?`<span class="sharp-seg sharp-empty" style="flex:${maxTotal-bar.total} 0 0"></span>`:""}</div>`;
}
function renderSharpness(w){
  if(RANGED_TYPES.has(w.weaponType))return '<span class="muted">해당 없음</span>';
  if(!w.sharpness)return '<span class="sharpness-missing">원본 미기재</span>';
  const n=w.sharpness.normal,p=w.sharpness.plus,max=Math.max(n?.total||0,p?.total||0,40),conf=w.sharpness.confidence||"";
  const warning=conf==="high"?"":`<span class="sharpness-warning" title="원본 표의 게이지 문자열 복원 신뢰도: ${esc(conf||"unknown")}">⚠ 복원</span>`;
  return `<div class="sharpness-stack">${warning}<div><small>기본</small>${sharpnessBar(n,max)}</div><div><small>+1</small>${sharpnessBar(p,max)}</div></div>`;
}
function weaponExtra(w){
  const bits=[];
  if(w.phial)bits.push(`병 ${w.phial}`);if(w.shelling)bits.push(`포격 ${w.shelling}`);if(w.notes)bits.push(`음색 ${w.notes}`);if(w.melody)bits.push(w.melody);if(w.kinsect)bits.push(`벌레 ${w.kinsect}`);if(w.arcShot)bits.push(`곡사 ${w.arcShot}`);if(w.specialFire)bits.push(`속사 ${w.specialFire}`);if(w.chargeLevels)bits.push(w.chargeLevels.join(" / "));if(w.coatings)bits.push(`병 ${w.coatings}`);if(w.reloadRecoilDrift)bits.push(w.reloadRecoilDrift);
  return bits.join(" · ");
}
function weaponFeatureColumns(type){
  if(type==="슬래시액스"||type==="차지액스") return [{key:"phial",label:"병",className:"feature-short",render:w=>esc(w.phial||"-")}];
  if(type==="건랜스") return [{key:"shelling",label:"포격",className:"feature-short",render:w=>esc(w.shelling||"-")}];
  if(type==="수렵피리") return [
    {key:"notes",label:"음색",className:"feature-short",render:w=>esc(w.notes||"-")},
    {key:"melody",label:"선율/효과",className:"feature-wrap",render:w=>esc(w.melody||"-")}
  ];
  if(type==="조충곤") return [{key:"kinsect",label:"벌레",className:"feature-wrap",render:w=>esc(w.kinsect||"-")}];
  if(type==="라이트보우건"||type==="헤비보우건") return [
    {key:"reloadRecoilDrift",label:"리로드/반동/흔들림",className:"feature-wrap",render:w=>esc(w.reloadRecoilDrift||"-")},
    {key:"specialFire",label:type==="라이트보우건"?"속사":"특수",className:"feature-wrap",render:w=>esc(w.specialFire||"-")}
  ];
  if(type==="활") return [
    {key:"chargeLevels",label:"모으기",className:"feature-charge",render:w=>esc((w.chargeLevels||[]).join(" / ")||"-")},
    {key:"arcShot",label:"곡사",className:"feature-short",render:w=>esc(w.arcShot||"-")},
    {key:"coatings",label:"병",className:"feature-wrap",render:w=>esc(w.coatings||"-")}
  ];
  return [];
}
function renderCraft(w){
  const craft=w.craft||[];
  if(!craft.length)return '<span class="muted">-</span>';
  return `<div class="craft-list">${craft.map(c=>`<div class="craft-line"><span class="craft-method">${esc(c.method||"소재")}</span><span class="craft-materials">${esc(c.materials||"-")}</span></div>`).join("")}</div>`;
}
function renderWeaponSubNav(){
  const box=$("#weaponSubNav");if(!box)return;
  const types=WEAPON_TYPES.filter(t=>data.weapons.some(w=>w.weaponType===t));
  box.innerHTML=types.map(t=>`<button type="button" class="weapon-sub-btn" data-weapon-type="${esc(t)}">${esc(t)}</button>`).join("")+
    `<button type="button" class="weapon-sub-btn sub-special" data-special-page="melody">　┗ 선율표</button>`+
    `<button type="button" class="weapon-sub-btn sub-special" data-special-page="weapon-summary">속성별 무기요약</button>`;
  box.querySelectorAll('[data-weapon-type]').forEach(b=>b.onclick=e=>{e.stopPropagation();armorViewMode="all";$("#weaponTypeFilter").value=b.dataset.weaponType;syncWeaponSubActive();openPage("weapon")});
  box.querySelectorAll('[data-special-page]').forEach(b=>b.onclick=e=>{e.stopPropagation();openPage(b.dataset.specialPage)});
}
function syncWeaponSubActive(){const t=$("#weaponTypeFilter")?.value||"all";$$('[data-weapon-type]').forEach(b=>b.classList.toggle('active',b.dataset.weaponType===t))}
function weaponFilteredBase(){
  const type=$("#weaponTypeFilter").value;
  // 무기 DB 화면의 종류 필터는 상단 전역 필터와 독립적으로 동작한다.
  return data.weapons.filter(w=>type==="all"||w.weaponType===type);
}
function renderWeaponTreeFilter(){
  const old=$("#weaponTreeFilter").value||"all";
  const trees=[...new Set(weaponFilteredBase().map(w=>w.tree).filter(Boolean))].sort((a,b)=>{
    const aw=data.weapons.find(w=>w.tree===a),bw=data.weapons.find(w=>w.tree===b);return (aw?.treeOrder??9999)-(bw?.treeOrder??9999)||a.localeCompare(b,"ko")
  });
  $("#weaponTreeFilter").innerHTML='<option value="all">전체 파생</option>'+trees.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
  $("#weaponTreeFilter").value=trees.includes(old)?old:"all";
}
function weaponTableColumns(type){
  const cols=[
    {key:"name",label:"명칭",className:"col-name"},
    {key:"attack",label:"공격력",className:"col-attack"},
    {key:"element",label:"속성/특수",className:"col-element"},
    {key:"affinity",label:"회심",className:"col-affinity"},
    {key:"slots",label:"슬롯",className:"col-slots"}
  ];
  if(!RANGED_TYPES.has(type)) cols.push({key:"sharpness",label:"예리도",className:"col-sharpness"});
  cols.push(...weaponFeatureColumns(type));
  cols.push({key:"rank",label:"등급",className:"col-rank"},{key:"craft",label:"생산/강화 소재",className:"col-craft"});
  return cols;
}
function weaponCell(w,col){
  if(col.key==="name"){
    const prefix=w.treePrefix?`<span class="tree-prefix">${esc(w.treePrefix)}</span>`:"";
    return `${prefix}${w.isFinal?'<span class="final-mark">■</span> ':''}<strong>${esc(w.name)}</strong>${w.nameJa?`<small>${esc(w.nameJa)}</small>`:""}`;
  }
  if(col.key==="attack") return w.attack??"-";
  if(col.key==="element") return esc(w.element||"-");
  if(col.key==="affinity") return `${w.affinity??0}%`;
  if(col.key==="slots") return slotsText(w.slots);
  if(col.key==="sharpness") return renderSharpness(w);
  if(col.key==="rank") return rankName(w.rank);
  if(col.key==="craft") return renderCraft(w);
  const f=weaponFeatureColumns(w.weaponType).find(x=>x.key===col.key);
  return f?f.render(w):"-";
}
function weaponRow(w,cols){
  return `<tr>${cols.map(col=>`<td class="${col.key==="name"?"weapon-name-cell ":""}${col.key==="slots"?"slots ":""}${col.key==="sharpness"?"sharpness-cell ":""}${esc(col.className||"")}">${weaponCell(w,col)}</td>`).join("")}</tr>`;
}
function renderWeaponTrees(){
  const q=$("#weaponSearch").value.trim().toLowerCase(),tree=$("#weaponTreeFilter").value;
  let rows=weaponFilteredBase().filter(w=>(tree==="all"||w.tree===tree)&&(!q||`${w.name} ${w.nameJa||""} ${w.element||""} ${w.tree||""} ${weaponExtra(w)} ${(w.craft||[]).map(c=>c.materials).join(" ")}`.toLowerCase().includes(q)));
  const groups=new Map();for(const w of rows){const k=w.tree||"기타";if(!groups.has(k))groups.set(k,[]);groups.get(k).push(w)}
  const ordered=[...groups.entries()].sort((a,b)=>(a[1][0]?.treeOrder??9999)-(b[1][0]?.treeOrder??9999)||a[0].localeCompare(b[0],"ko"));
  $("#weaponResultInfo").textContent=`${rows.length.toLocaleString()}개 무기 · ${ordered.length.toLocaleString()}개 파생`;
  $("#weaponTrees").innerHTML=ordered.length?ordered.map(([name,list],i)=>{
    const sorted=list.sort((a,b)=>(a.rowOrder??0)-(b.rowOrder??0));
    const type=sorted[0]?.weaponType||"";
    const cols=weaponTableColumns(type);
    return `<details class="weapon-tree-group" ${(q||tree!=="all"||i===0)?"open":""}><summary><span>${esc(name)}</span><span class="tree-meta">${esc(type)} · ${list.length}개</span></summary><div class="weapon-tree-table-wrap"><table class="data-table weapon-data-table ${RANGED_TYPES.has(type)?"ranged-table":"melee-table"}"><thead><tr>${cols.map(c=>`<th class="${esc(c.className||"")}">${esc(c.label)}</th>`).join("")}</tr></thead><tbody>${sorted.map(w=>weaponRow(w,cols)).join("")}</tbody></table></div></details>`;
  }).join(""):'<div class="panel result-empty">검색 결과 없음</div>';
  syncWeaponSubActive();
}
function renderDecoTable(){
  const q=$("#decoSearch").value.trim().toLowerCase(),rank=$("#rankFilter").value;
  const list=data.decorations.filter(d=>(rank==="all"||d.rank===rank)&&(!q||decorationSearchCorpus(d).toLowerCase().includes(q)));
  list.sort((a,b)=>decoView==="slot"?(a.slots-b.slots||a.name.localeCompare(b.name,"ko")):(Object.keys(a.skills||{}).map(skillName).join("").localeCompare(Object.keys(b.skills||{}).map(skillName).join(""),"ko")||a.name.localeCompare(b.name,"ko")));
  const rows=list.map(d=>`<tr><td>${esc(d.name)}</td><td>${d.slots}</td><td>${Object.entries(d.skills||{}).map(([k,v])=>`${esc(skillName(k))} ${v>0?"+":""}${v}`).join(", ")}</td><td>${rankName(d.rank)}</td><td>${esc(d.materials||"")}</td></tr>`);
  renderTable("#decoTable",["장식주","필요 슬롯","스킬 포인트","등급","생산 소재"],rows);
}
function renderSkillTable(){
  const q=$("#skillSearch").value.trim().toLowerCase();
  const rows=data.skills.filter(s=>!q||skillSearchCorpus(s).toLowerCase().includes(q)).map(s=>`<tr><td>${esc(s.name)}</td><td>${(s.activations||[]).map(a=>`${a.points>0?"+":""}${a.points} → <strong>${esc(a.name)}</strong>`).join("<br>")}</td><td>${(s.activations||[]).map(a=>a.description?`<div><strong>${esc(a.name)}</strong>: ${esc(cleanEffectText(a.description))}</div>`:"").filter(Boolean).join("")}</td></tr>`);
  renderTable("#skillTable",["스킬 계통","발동 조건","효과 및 비고"],rows);
}
function renderItemTable(){
  const q=$("#itemSearch").value.trim().toLowerCase();
  const rows=data.items.filter(i=>!q||`${i.name} ${i.nameJa||""} ${i.acquire||""} ${i.note||""}`.toLowerCase().includes(q)).map(i=>`<tr><td>${esc(i.name)}</td><td>${i.rare||"-"}</td><td>${i.maxStack||"-"}</td><td>${esc(i.buyPrice||"-")}</td><td>${esc(i.sellPrice||"-")}</td><td>${esc(i.acquire||"")}</td><td>${esc(i.note||"")}</td></tr>`);
  renderTable("#itemTable",["아이템","RARE","소지수","구매","판매","입수","효과/비고"],rows);
}

function renderSourcePage(){
  const box=$("#sourceContent");
  if(!box) return;
  if(sourceView==="history"){
    const rows=(data.siteInfo?.history||[]).map(h=>`<tr><td>${esc(h.version||"")}</td><td>${esc(h.date||"")}</td><td>${esc(h.content||"")}</td><td>${esc(h.category||"")}</td></tr>`);
    box.innerHTML=`<div class="source-head"><h2>원본 DB 이력</h2><p class="muted">flashkiller MH4G DB의 업데이트 이력을 정리한 화면입니다.</p></div><div class="table-panel"><table class="data-table"><thead><tr><th>버전</th><th>일자</th><th>내용</th><th>비고</th></tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
  }else{
    const lines=(data.siteInfo?.main||[]).filter(x=>x&&!/^Ver\s/i.test(x)).slice(0,24);
    box.innerHTML=`<div class="source-head"><h2>애니타임 몬스터헌터 4G Database</h2><p class="muted">원본 사이트의 안내 내용을 보존한 페이지입니다.</p></div><div class="source-copy">${lines.map(x=>`<p>${esc(x)}</p>`).join("")}</div><p><a class="source-link" href="https://flashkiller.cafe24.com/mh4g/main.htm" target="_blank" rel="noreferrer">원본 사이트 열기 ↗</a></p>`;
  }
}

function armorSetEligible(s){
  const hunter=$("#hunterType").value,rank=$("#rankFilter").value;
  return (hunter==="both"||s.hunterType===hunter)&&(rank==="all"||s.rank===rank);
}
function renderArmorSetTable(){
  const q=$("#armorSetSearch").value.trim().toLowerCase();
  const rows=data.armorSets.filter(armorSetEligible).filter(s=>!q||`${s.name} ${(s.pieces||[]).map(p=>p.name).join(" ")} ${Object.keys(s.skills||{}).map(skillName).join(" ")}`.toLowerCase().includes(q))
    .map(s=>`<tr><td><strong>${esc(s.name)}</strong><small>${(s.pieces||[]).map(p=>`${PART_NAMES[p.part]||p.part}:${p.name}`).map(esc).join(" · ")}</small></td><td>${hunterName(s.hunterType)}</td><td>${rankName(s.rank)}</td><td>${s.rare||"-"}</td><td>${s.defense||0} / ${s.maxDefense||s.defense||0}</td><td>${s.slots||0}</td><td>${Object.entries(s.skills||{}).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${esc(skillName(k))} ${v>0?"+":""}${v}`).join(", ")}</td><td>${resistText(s.resistances)}</td></tr>`);
  renderTable("#armorSetTable",["세트","타입","등급","RARE","방어(초기/최대)","총 슬롯","스킬 합계","내성 합계"],rows);
}

function renderWeaponSummary(){
  const q=$("#weaponSummarySearch").value.trim().toLowerCase(),type=$("#weaponSummaryType").value;
  const list=data.weaponSummary.filter(x=>(type==="all"||x.weaponType===type)&&(!q||`${x.weaponType} ${x.attribute} ${x.normal} ${x.awaken}`.toLowerCase().includes(q)));
  const rows=list.map(x=>`<tr><td>${esc(x.weaponType)}</td><td><strong>${esc(x.attribute)}</strong></td><td class="wrap-cell">${esc(x.normal||"-")}</td><td class="wrap-cell">${esc(x.awaken||"-")}</td></tr>`);
  renderTable("#weaponSummaryTable",["무기","속성","각성 불필요","각성 필요"],rows);
}

function renderMelodyTable(){
  const q=$("#melodySearch").value.trim().toLowerCase();
  const rows=data.melodies.filter(x=>!q||`${x.notes} ${(x.effects||[]).join(" ")} ${(x.weapons||[]).join(" ")}`.toLowerCase().includes(q))
    .map(x=>`<tr><td><strong>${esc(x.notes)}</strong></td><td class="wrap-cell">${(x.effects||[]).map(e=>`<span class="mini-chip">${esc(e)}</span>`).join(" ")||"-"}</td><td class="wrap-cell">${esc((x.weapons||[]).join(" · "))}</td></tr>`);
  renderTable("#melodyTable",["음색","선율 효과","해당 무기"],rows);
}

function renderMealGrid(){
  const q=$("#mealSearch").value.trim().toLowerCase(),ing=$("#mealIngredientFilter").value;
  const list=data.meals.filter(x=>(ing==="all"||x.ingredient1===ing||x.ingredient2===ing)&&(!q||`${x.ingredient1} ${x.ingredient2} ${x.method} ${x.effect} ${(x.skills||[]).join(" ")}`.toLowerCase().includes(q)));
  const grouped=new Map();
  for(const x of list){const k=`${x.ingredient1}+${x.ingredient2}`;if(!grouped.has(k))grouped.set(k,[]);grouped.get(k).push(x)}
  $("#mealGrid").innerHTML=[...grouped.entries()].map(([key,rows])=>`<section class="panel meal-card"><h3>${esc(key)}</h3><div class="meal-method-grid">${rows.map(x=>`<div class="meal-method"><strong>${esc(x.method)}</strong><span class="meal-effect">${esc(x.effect||"효과없음")}</span><small>${(x.skills||[]).map(esc).join(" · ")||"-"}</small></div>`).join("")}</div></section>`).join("")||'<div class="panel result-empty">검색 결과 없음</div>';
}

function populateMonsterSelect(){
  const el=$("#monsterSelect"); if(!el) return;
  const old=el.value||"all";
  const names=[...new Set([...(data.monsterSummary||[]).map(x=>x.name),...(data.monsterDetails||[]).map(x=>x.name),...(data.monsterRewards||[]).map(x=>x.monster)])].filter(Boolean).sort((a,b)=>a.localeCompare(b,"ko"));
  el.innerHTML='<option value="all">전체 몬스터</option>'+names.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join("");
  el.value=names.includes(old)?old:"all";
}
function monsterMatchName(name){
  const sel=$("#monsterSelect").value; return sel==="all"||name===sel;
}
function renderMonsterSummaryView(){
  const q=$("#monsterSearch").value.trim().toLowerCase();
  const rows=data.monsterSummary.filter(x=>monsterMatchName(x.name)&&(!q||`${x.name} ${x.species} ${x.materialName} ${x.traits}`.toLowerCase().includes(q))).map(x=>`<tr><td>${esc(x.species)}</td><td><strong>${esc(x.name)}</strong><small>${esc(x.materialName||"")}</small></td><td>${esc(x.weakspots?.cut||"-")}</td><td>${esc(x.weakspots?.impact||"-")}</td><td>${esc(x.weakspots?.shot||"-")}</td><td>${["fire","water","thunder","ice","dragon"].map(k=>esc(x.elements?.[k]||"-")).join(" / ")}</td><td>${["poison","sleep","paralysis","blast"].map(k=>esc(x.ailments?.[k]||"-")).join(" / ")}</td><td>${["pitfall","shock","flash","sonic","meat"].map(k=>esc(x.traps?.[k]||"-")).join(" / ")}</td><td>${esc(x.traits||"")}</td></tr>`);
  $("#monsterContent").innerHTML='<div class="panel table-panel"><div id="monsterSummaryTable"></div></div>';
  renderTable("#monsterSummaryTable",["종류","몬스터","절단","타격","탄","불/물/뇌/빙/용","독/수면/마비/폭파","구멍/마비/섬광/음폭/육류","특성"],rows);
}
function renderMonsterDetailView(){
  const q=$("#monsterSearch").value.trim().toLowerCase();
  const list=data.monsterDetails.filter(x=>monsterMatchName(x.name)&&(!q||`${x.name} ${(x.parts||[]).map(p=>p.part).join(" ")} ${(x.statuses||[]).map(s=>s.status).join(" ")}`.toLowerCase().includes(q)));
  $("#monsterContent").innerHTML=list.map((x,i)=>`<details class="monster-detail panel" ${(list.length===1||i===0)?"open":""}><summary><strong>${esc(x.name)}</strong><span class="tree-meta">부위 ${(x.parts||[]).length} · 상태 ${(x.statuses||[]).length}</span></summary><div class="monster-meta">${x.meta?.baseHp?`<span>기본체력 <strong>${esc(x.meta.baseHp)}</strong></span>`:""}${x.meta?.minCrown?`<span>최소금관 ${esc(x.meta.minCrown)}</span>`:""}${x.meta?.maxSilver?`<span>최대은관 ${esc(x.meta.maxSilver)}</span>`:""}${x.meta?.maxGold?`<span>최대금관 ${esc(x.meta.maxGold)}</span>`:""}</div><div class="table-panel"><table class="data-table"><thead><tr><th>부위</th><th>절단</th><th>타격</th><th>탄</th><th>불</th><th>물</th><th>번개</th><th>얼음</th><th>용</th><th>기절</th><th>다운</th></tr></thead><tbody>${(x.parts||[]).map(p=>`<tr><td>${esc(p.part)}</td><td>${esc(p.cut)}</td><td>${esc(p.impact)}</td><td>${esc(p.shot)}</td><td>${esc(p.fire)}</td><td>${esc(p.water)}</td><td>${esc(p.thunder)}</td><td>${esc(p.ice)}</td><td>${esc(p.dragon)}</td><td>${esc(p.stun)}</td><td>${esc(p.down)}</td></tr>`).join("")}</tbody></table></div><h4>상태이상 내성</h4><div class="table-panel"><table class="data-table"><thead><tr><th>상태</th><th>지속/데미지</th><th>초기내성</th><th>상승치</th><th>최대내성</th></tr></thead><tbody>${(x.statuses||[]).map(s=>`<tr><td>${esc(s.status)}</td><td>${esc(s.durationDamage)}</td><td>${esc(s.initial)}</td><td>${esc(s.increase)}</td><td>${esc(s.max)}</td></tr>`).join("")}</tbody></table></div></details>`).join("")||'<div class="panel result-empty">검색 결과 없음</div>';
}
function filteredRewards(){
  const q=$("#monsterSearch").value.trim().toLowerCase(),rank=$("#monsterRankFilter").value;
  return data.monsterRewards.filter(x=>monsterMatchName(x.monster)&&(rank==="all"||x.rank===rank)&&(!q||`${x.monster} ${x.method} ${x.item}`.toLowerCase().includes(q)));
}
function renderMonsterRewardsView(){
  const rows=filteredRewards().map(x=>`<tr><td>${esc(x.monster)}</td><td>${esc(x.method||"-")} ${esc(x.count||"")}</td><td>${rankName(x.rank)==="extreme"?"극한":rankName(x.rank)}</td><td>${esc(x.item)}</td><td>${esc(x.probability)}</td></tr>`);
  $("#monsterContent").innerHTML='<div class="panel table-panel"><div id="monsterRewardsTable"></div></div>';
  renderTable("#monsterRewardsTable",["몬스터","입수방법","등급","아이템","확률"],rows);
}
function renderMonsterMaterialsView(){
  const rewards=filteredRewards(),groups=new Map();
  for(const x of rewards){const k=`${x.monster}|${x.rank}`;if(!groups.has(k))groups.set(k,{monster:x.monster,rank:x.rank,items:new Map()});const g=groups.get(k);if(!g.items.has(x.item))g.items.set(x.item,new Set());g.items.get(x.item).add(x.method||"입수")}
  const cards=[...groups.values()].map(g=>`<section class="panel material-card"><h3>${esc(g.monster)} <small>${g.rank==="extreme"?"극한":rankName(g.rank)}</small></h3><div class="material-chip-list">${[...g.items.entries()].map(([item,methods])=>`<span class="material-chip"><strong>${esc(item)}</strong><small>${esc([...methods].join(" · "))}</small></span>`).join("")}</div></section>`);
  $("#monsterContent").innerHTML=cards.length?`<div class="card-grid">${cards.join("")}</div>`:'<div class="panel result-empty">검색 결과 없음</div>';
}
function renderMonster(){
  $("#monsterRankFilter").style.display=["rewards","materials"].includes(monsterView)?"":"none";
  if(monsterView==="summary")renderMonsterSummaryView();
  else if(monsterView==="detail")renderMonsterDetailView();
  else if(monsterView==="rewards")renderMonsterRewardsView();
  else renderMonsterMaterialsView();
}

function renderDragon(){
  const q=$("#dragonSearch").value.trim().toLowerCase();
  if(dragonView==="exchange"){
    const rows=data.dragonExchange.filter(x=>!q||`${x.result} ${x.required} ${x.unlock}`.toLowerCase().includes(q)).map(x=>`<tr><td>${esc(x.result)}</td><td>${esc(x.required)}</td><td class="wrap-cell">${esc(x.unlock)}</td></tr>`);
    renderTable("#dragonTable",["교환 아이템","필요 아이템","해금 조건/퀘스트"],rows);
  }else if(dragonView==="sell"){
    const rows=data.dragonSell.filter(x=>!q||`${x.line} ${x.name}`.toLowerCase().includes(q)).map(x=>`<tr><td>${esc(x.line)}</td><td>${esc(x.name)}</td><td>${esc(x.points)}</td></tr>`);
    renderTable("#dragonTable",["목록","물품","필요 여단P"],rows);
  }else{
    const rows=data.dragonIncrease.filter(x=>!q||`${x.market} ${x.name}`.toLowerCase().includes(q)).map(x=>`<tr><td>${esc(x.market)}</td><td>${esc(x.name)}</td><td>${x.rare}</td><td>${esc(x.successRate)}</td><td>${esc(x.points)}</td></tr>`);
    renderTable("#dragonTable",["시장","아이템","RARE","성공률","필요 여단P"],rows);
  }
}

function renderCompose(){
  const q=$("#composeSearch").value.trim().toLowerCase();
  const rows=data.compositions.filter(x=>!q||`${x.result} ${x.materialA} ${x.materialB}`.toLowerCase().includes(q)).map(x=>`<tr><td>${x.no}</td><td><strong>${esc(x.result)}</strong></td><td>${esc(x.materialA)}</td><td>${esc(x.materialB)}</td><td>${esc(x.successRate)}</td><td>${esc(x.yield)}</td></tr>`);
  renderTable("#composeTable",["No.","조합 결과","소재 A","소재 B","성공확률","생산수"],rows);
}

function questTypeForView(){
  if(questView.startsWith("village"))return "village";
  if(questView.startsWith("hub"))return "hub";
  if(questView.startsWith("g-"))return "g";
  return "all";
}
function populateQuestLevels(){
  const el=$("#questLevelFilter");if(!el)return;
  const old=el.value||"all",type=questTypeForView();
  const levels=[...new Set(data.quests.filter(q=>type==="all"||q.questType===type).map(q=>q.level))].sort();
  el.innerHTML='<option value="all">전체 ★</option>'+levels.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
  el.value=levels.includes(old)?old:"all";
}
function renderQuest(){
  populateQuestLevels();
  const qtext=$("#questSearch").value.trim().toLowerCase(),type=questTypeForView(),level=$("#questLevelFilter").value;
  const keyOnly=questView==="key"||$("#questKeyOnly").checked;
  const list=data.quests.filter(q=>(type==="all"||q.questType===type)&&(level==="all"||q.level===level)&&(!keyOnly||q.key)&&(!qtext||`${q.name} ${q.nameJa} ${q.objective} ${q.location} ${q.note}`.toLowerCase().includes(qtext)));
  const detail=questView.endsWith("detail")||questView==="key";
  const rows=list.map(q=>detail?`<tr><td>${esc(q.questTypeLabel)}</td><td>${esc(q.level)}</td><td>${q.key?"○":""}</td><td><strong>${esc(q.name)}</strong><small>${esc(q.nameJa||"")}</small></td><td class="wrap-cell">${esc(q.objective)}</td><td>${esc(q.location)}</td><td>${esc(q.fee)}</td><td>${esc(q.reward)}</td><td>${esc(q.time)}</td><td>${esc(q.conditions)}</td><td>${esc(q.note)}</td></tr>`:`<tr><td>${esc(q.level)}</td><td>${q.key?"○":""}</td><td><strong>${esc(q.name)}</strong></td><td class="wrap-cell">${esc(q.objective)}</td><td>${esc(q.location)}</td><td>${esc(q.note)}</td></tr>`);
  renderTable("#questTable",detail?["구분","레벨","키","퀘스트","클리어 조건","장소","계약금","보수금","시간","특수조건","비고"]:["레벨","키","퀘스트","클리어 조건","장소","비고"],rows);
}

function pageTitleForState(page){
  if(page==="source") return sourceView==="history"?["이력","원본 MH4G DB 업데이트 이력"]:["메인","원본 MH4G DB 안내"];
  if(page==="armor-set") return [`${hunterName($("#hunterType").value)} 방어구 세트`,"5부위 세트의 방어·슬롯·스킬 합계를 조회합니다."];
  if(page==="weapon-summary") return ["속성별 무기요약","무기별 속성 및 각성 필요 여부를 비교합니다."];
  if(page==="melody") return ["수렵피리 선율표","음색 조합별 선율 효과와 해당 무기를 조회합니다."];
  if(page==="meal") return ["식사","식재료 조합과 조리법에 따른 식사효과·야옹스킬을 조회합니다."];
  if(page==="monster"){
    const t={summary:"육질표요약",detail:"육질표상세",rewards:"갈무리보수확률",materials:"몬스터소재요약"}[monsterView];
    return [t,"몬스터 약점·육질·상태이상·소재 정보를 조회합니다."];
  }
  if(page==="dragon"){
    const t={exchange:"교환소재",sell:"판매물품",increase:"아이템증식"}[dragonView];
    return [`용인족 도매상 · ${t}`,"교환·판매·증식 정보를 조회합니다."];
  }
  if(page==="compose") return ["조합서","아이템 조합식과 성공확률·생산수를 조회합니다."];
  if(page==="quest"){
    const t={key:"키퀘스트","village-summary":"여단요약","village-detail":"여단상세","hub-summary":"집회소요약","hub-detail":"집회소상세","g-summary":"G급요약","g-detail":"G급상세"}[questView];
    return [`퀘스트 · ${t}`,"키퀘·클리어 조건·장소·보수 정보를 조회합니다."];
  }
  return null;
}

function handleRoute(btn){
  const route=btn.dataset.route;
  if(route==="armor-set"){
    armorViewMode="all";$("#hunterType").value=btn.dataset.hunter;$("#rankFilter").value="all";openPage("armor-set");
  }else if(route==="armor-detail"){
    armorViewMode="all";$("#hunterType").value=btn.dataset.hunter;$("#rankFilter").value=btn.dataset.rank;openPage("armor");
  }else if(route==="armor-other"){
    armorViewMode="other";$("#hunterType").value="both";$("#rankFilter").value="all";openPage("armor");
  }else if(route==="decoration-view"){
    decoView=btn.dataset.decoView||"type";openPage("decoration");
  }else if(route==="monster-view"){
    monsterView=btn.dataset.monsterView||"summary";openPage("monster");
  }else if(route==="dragon-view"){
    dragonView=btn.dataset.dragonView||"exchange";openPage("dragon");
  }else if(route==="quest-view"){
    questView=btn.dataset.questView||"key";$("#questKeyOnly").checked=questView==="key";openPage("quest");
  }
}

function renderSummary(){
  const vals=[
    ["방어구",data.armors.length],["방어구 세트",data.armorSets.length],["무기",data.weapons.length],["속성무기 요약",data.weaponSummary.length],
    ["장식주",data.decorations.length],["스킬 계통",data.skills.length],["식사 조합",data.meals.length],["아이템",data.items.length],
    ["몬스터 요약",data.monsterSummary.length],["몬스터 상세",data.monsterDetails.length],["갈무리/보수",data.monsterRewards.length],
    ["용인족 도매상",data.dragonExchange.length+data.dragonSell.length+data.dragonIncrease.length],["조합식",data.compositions.length],["퀘스트",data.quests.length]
  ];
  const sharp=data.weapons.filter(w=>w.sharpness).length,trees=new Set(data.weapons.map(w=>w.tree).filter(Boolean)).size;
  $("#dataSummary").innerHTML=`<div class="summary-list">${vals.map(([n,v])=>`<div class="summary-item"><strong>${Number(v||0).toLocaleString()}</strong><span>${n}</span></div>`).join("")}</div><p class="muted">무기 파생 ${trees.toLocaleString()}개 · 예리도 데이터 ${sharp.toLocaleString()}개 · 수렵피리 음색그룹 ${data.melodies.length.toLocaleString()}개<br>데이터 버전: ${esc(data.meta?.version||"unknown")}<br>원본: ${esc(data.meta?.source||"-")}<br>${esc(data.meta?.note||"")}</p>`;
  const isDemo=Boolean(data.meta?.demo);$("#datasetBadge").textContent=isDemo?"샘플 데이터":`실데이터 v${data.meta?.version||""}`;$("#datasetBadge").className=`badge ${isDemo?"warning":"good"}`;
}
function updateHeaderFilterVisibility(){
  const typePages=new Set(["simulator","armor","armor-set","weapon"]),rankPages=new Set(["simulator","armor","armor-set","weapon","decoration"]);
  $("#hunterTypeWrap").classList.toggle("hidden-filter",!typePages.has(currentPage));
  $("#rankFilterWrap").classList.toggle("hidden-filter",!rankPages.has(currentPage));
}
const loadedFullKeys=new Set(["skills","decorations","meta"]);
let pageLoadToken=0;
function dataKeysForPage(page){
  if(page==="source")return ["siteInfo"];
  if(page==="armor")return ["armors"];
  if(page==="armor-set")return ["armorSets"];
  if(page==="weapon")return ["weapons"];
  if(page==="weapon-summary")return ["weaponSummary"];
  if(page==="melody")return ["melodies"];
  if(page==="meal")return ["meals"];
  if(page==="monster")return monsterView==="summary"?["monsterSummary"]:monsterView==="detail"?["monsterDetails"]:["monsterRewards"];
  if(page==="dragon")return dragonView==="exchange"?["dragonExchange"]:dragonView==="sell"?["dragonSell"]:["dragonIncrease"];
  if(page==="item")return ["items"];
  if(page==="compose")return ["compositions"];
  if(page==="quest")return ["quests"];
  if(page==="data")return FULL_DATA_KEYS;
  return [];
}
async function ensureFullData(keys){
  const missing=[...new Set(keys)].filter(k=>!loadedFullKeys.has(k));
  if(!missing.length)return false;
  const patch=await loadFullData(missing);
  Object.assign(data,patch);missing.forEach(k=>loadedFullKeys.add(k));
  if(missing.some(k=>["skills","armors","armorSets","decorations","weapons"].includes(k)))rebuildIndexes();
  if(missing.includes("meals"))populateMealIngredientFilter();
  if(missing.some(k=>["monsterSummary","monsterDetails","monsterRewards"].includes(k)))populateMonsterSelect();
  if(missing.includes("quests"))populateQuestLevels();
  return true;
}
function renderPageData(page){
  if(page==="source")renderSourcePage();
  else if(page==="armor")renderArmorTable();
  else if(page==="armor-set")renderArmorSetTable();
  else if(page==="weapon"){renderWeaponTreeFilter();renderWeaponTrees()}
  else if(page==="weapon-summary")renderWeaponSummary();
  else if(page==="melody")renderMelodyTable();
  else if(page==="decoration")renderDecoTable();
  else if(page==="skill")renderSkillTable();
  else if(page==="meal")renderMealGrid();
  else if(page==="monster")renderMonster();
  else if(page==="dragon")renderDragon();
  else if(page==="item")renderItemTable();
  else if(page==="compose")renderCompose();
  else if(page==="quest")renderQuest();
}
async function openPage(page){
  currentPage=page;
  $$('.nav-main[data-page]').forEach(x=>x.classList.toggle('active',x.dataset.page===page&&(!x.dataset.sourceView||x.dataset.sourceView===sourceView)));
  $$('.page').forEach(p=>p.classList.remove('active'));
  const section=$(`#page-${page}`); if(section)section.classList.add('active');
  const titles={simulator:["스킬 시뮬레이터","방어구 + 호석 + 장식주 조합을 계산합니다."],armor:["방어구 상세","타입·등급·부위 조건으로 방어구를 조회합니다."],weapon:["무기 DB","무기 종류·파생·예리도와 제작 정보를 조회합니다."],decoration:[decoView==="slot"?"장신구 · 소켓별":"장신구 · 종류별","슬롯·스킬 포인트·생산소재를 조회합니다."],skill:["스킬 DB","스킬 계통과 발동 조건·효과를 조회합니다."],item:["아이템 DB","아이템 입수방법과 효과를 조회합니다."],data:["데이터 관리","실제 JSON 데이터 상태와 업데이트 방법을 확인합니다."]};
  const dynamic=pageTitleForState(page);
  const title=dynamic||titles[page]||["MH4G DB",""];
  $("#pageTitle").textContent=title[0];$("#pageSubtitle").textContent=title[1];
  updateHeaderFilterVisibility();
  const token=++pageLoadToken;
  const keys=dataKeysForPage(page);
  if(keys.some(k=>!loadedFullKeys.has(k))){
    $("#pageSubtitle").textContent=`${title[1]} · 데이터 불러오는 중…`;
    await ensureFullData(keys);
    if(token!==pageLoadToken||currentPage!==page)return;
    $("#pageSubtitle").textContent=title[1];
  }
  if(page==="data")renderSummary();
  renderPageData(page);
}
function renderAll(){fillSelectors();renderSavedBuilds();renderManualSelectors();renderTargets();renderManualResult();renderSummary();updateHeaderFilterVisibility()}

function bind(){
  document.addEventListener('click',()=>closePickers());
  $("#sidebarToggle").onclick=()=>{$(".app-shell").classList.toggle("sidebar-collapsed");const collapsed=$(".app-shell").classList.contains("sidebar-collapsed");$("#sidebarToggle").title=collapsed?"좌측 메뉴 펼치기":"좌측 메뉴 접기";};

  $$('.nav-group-toggle').forEach(b=>b.onclick=e=>{
    e.stopPropagation();
    const menu=$(`#${b.dataset.submenu}`);
    if(menu)menu.classList.toggle("open");
  });
  $$('.nav-main[data-page]').forEach(b=>b.onclick=e=>{
    e.stopPropagation();
    if(b.dataset.sourceView)sourceView=b.dataset.sourceView;
    openPage(b.dataset.page);
  });
  $$('[data-route]').forEach(b=>b.onclick=e=>{e.stopPropagation();handleRoute(b)});

  $("#addTargetSkill").onclick=()=>{const v=uiState.targetActivation;if(v&&!targets.includes(v)){targets.push(v);renderTargets()}};
  $("#clearTargets").onclick=()=>{targets=[];renderTargets()};$("#calculateManual").onclick=renderManualResult;$("#runSearch").onclick=runSearch;
  $("#saveBuild").onclick=saveCurrentBuild;$("#loadBuild").onclick=loadSelectedBuild;$("#deleteBuild").onclick=deleteSelectedBuild;$("#savedBuildSelect").onchange=loadSelectedBuild;

  $("#hunterType").onchange=()=>{
    if(currentPage==="armor")renderArmorTable();
    if(currentPage==="armor-set"){renderArmorSetTable();const t=pageTitleForState("armor-set");$("#pageTitle").textContent=t[0]}
    if(currentPage==="weapon"){renderWeaponTreeFilter();renderWeaponTrees()}
  };
  $("#rankFilter").onchange=()=>{
    if(currentPage==="armor")renderArmorTable();
    if(currentPage==="armor-set")renderArmorSetTable();
    if(currentPage==="weapon"){renderWeaponTreeFilter();renderWeaponTrees()}
    if(currentPage==="decoration")renderDecoTable();
  };
  $("#includeTorsoUp").onchange=()=>{renderManualResult()};

  $("#armorSearch").oninput=renderArmorTable;$("#armorPartFilter").onchange=renderArmorTable;
  $("#armorSetSearch").oninput=renderArmorSetTable;
  $("#weaponSearch").oninput=renderWeaponTrees;$("#weaponTypeFilter").onchange=()=>{renderWeaponTreeFilter();renderWeaponTrees()};$("#weaponTreeFilter").onchange=renderWeaponTrees;
  $("#weaponSummarySearch").oninput=renderWeaponSummary;$("#weaponSummaryType").onchange=renderWeaponSummary;
  $("#melodySearch").oninput=renderMelodyTable;
  $("#decoSearch").oninput=renderDecoTable;$("#skillSearch").oninput=renderSkillTable;
  $("#mealSearch").oninput=renderMealGrid;$("#mealIngredientFilter").onchange=renderMealGrid;
  $("#monsterSearch").oninput=renderMonster;$("#monsterSelect").onchange=renderMonster;$("#monsterRankFilter").onchange=renderMonster;
  $("#dragonSearch").oninput=renderDragon;
  $("#itemSearch").oninput=renderItemTable;
  $("#composeSearch").oninput=renderCompose;
  $("#questSearch").oninput=renderQuest;$("#questLevelFilter").onchange=renderQuest;$("#questKeyOnly").onchange=renderQuest;

  $("#jsonImport").onchange=async e=>{const lines=[];for(const f of e.target.files){try{const json=JSON.parse(await f.text()),type=classifyImported(f.name,json);if(type){data[type]=json;lines.push(`${f.name} → ${type} ${Array.isArray(json)?json.length:"객체"}건`)}else lines.push(`${f.name} → 유형 판별 실패`)}catch{lines.push(`${f.name} → JSON 오류`)}}data.meta={...data.meta,demo:false,version:"browser-import"};rebuildIndexes();$("#importStatus").innerHTML=lines.map(esc).join("<br>");renderAll()};
}

Object.assign(data,await loadSimulatorData());rebuildIndexes();bind();renderAll();
