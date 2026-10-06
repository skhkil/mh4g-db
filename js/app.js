import {loadSimulatorData,loadFullData,loadItemReference,loadSkillReference,loadMonsterReference,loadMonsterReferencesFallback,loadArmorProgression,FULL_DATA_KEYS,classifyImported} from "./data-loader.js?v=0.7.7-chat4-monster-link-hotfix11";
import {PARTS,PART_NAMES,slotsText,calculateBuild,searchBuilds} from "./engine.js?v=0.7.7-chat4-monster-link-hotfix11";

let data={skills:[],armors:[],armorSets:[],decorations:[],decorationUnlocks:{decorations:{}},eventMajorRewards:{quests:{}},weapons:[],weaponSummary:[],melodies:[],items:[],itemReferenceIndex:{items:{}},skillReferenceIndex:{items:{},categories:[]},meals:[],monsterSummary:[],monsterDetails:[],monsterRewards:[],monsterReferenceIndex:{items:{}},dragonExchange:[],dragonSell:[],dragonIncrease:[],compositions:[],quests:[],questReferenceIndex:{quests:{}},siteInfo:{},meta:{},weaponSkillPriorities:{weapons:{}}};
let targets=[];
let latestAutoSearchResults=[];
let latestAutoSearchNearMisses=[];
let currentPage="simulator";
const BUILD_STORAGE_KEY="mh4g-builds-v1";
const OWNED_CHARMS_STORAGE_KEY="mh4g-owned-charms-v1";
const WEAPON_TYPES=["대검","태도","한손검","쌍검","해머","수렵피리","랜스","건랜스","슬래시액스","차지액스","조충곤","라이트보우건","헤비보우건","활"];
const RANGED_TYPES=new Set(["라이트보우건","헤비보우건","활"]);
const WEAPON_SKILL_PRIORITY_NAMES={
  "대검":{"차지단축":5,"발도치명타":5,"장인":3,"예리도":3},
  "태도":{"예리도":5,"장인":4,"투혼":4,"청각보호":2,"달인":2},
  "한손검":{"예리도":4,"장인":4,"회피성능":3,"특수공격":3,"속성공격":3},
  "쌍검":{"예리도":5,"장인":4,"속성공격":4,"속성치명타":3,"회피성능":2},
  "해머":{"통격":5,"투혼":4,"청각보호":3,"장인":2},
  "수렵피리":{"피리":5,"예리도":3,"장인":3,"투혼":3},
  "랜스":{"가드성능":5,"가드강화":3,"회피성능":4,"회피거리":3,"예리도":3,"장인":3},
  "건랜스":{"포술":5,"가드성능":4,"가드강화":3,"예리도":4,"장인":3},
  "슬래시액스":{"회피거리":5,"회피성능":3,"예리도":4,"장인":4,"투혼":3},
  "차지액스":{"포술":5,"가드성능":4,"예리도":4,"장인":3,"투혼":3},
  "조충곤":{"예리도":5,"장인":4,"투혼":4,"통격":3,"청각보호":2},
  "라이트보우건":{"반동":4,"장전속도":3,"통상탄강화":4,"관통탄강화":4,"속성공격":4},
  "헤비보우건":{"관통탄강화":5,"통상탄강화":4,"반동":4,"회피거리":4,"장전속도":3},
  "활":{"차지단축":5,"통상탄강화":4,"산탄강화":4,"관통탄강화":4,"장전수":2}
};
function weaponPreferredSkillWeights(hunterType="blade"){const type=uiState.autoWeaponType||"";const src=(type&&type!=="all"?(data.weaponSkillPriorities?.weapons?.[type]||WEAPON_SKILL_PRIORITY_NAMES[type]):null)||data.weaponSkillPriorities?.hunterTypeDefaults?.[hunterType]||{};const byName=new Map((data.skills||[]).map(x=>[x.name,x.id]));return Object.fromEntries(Object.entries(src).map(([name,w])=>[byName.get(name),w]).filter(([id])=>id))}

const MANUAL_CONTAINERS=["weapon",...PARTS,"charm"];
const uiState={
  targetActivation:"", autoWeaponType:"대검", autoWeaponSlots:0, ownedCharmsOnly:false, manualSet:"", armorSetSort:"name", manualWeapon:"", manualWeaponType:"all", manualWeaponRank:"all", manualWeaponElement:"all", manualWeaponSlots:"all",
  charmSkill1:"",charmPoint1:0,charmSkill2:"",charmPoint2:0,charmSlots:0,
  manual:Object.fromEntries(PARTS.map(p=>[p,""])),
  manualDecorations:Object.fromEntries(MANUAL_CONTAINERS.map(c=>[c,[]]))
};
let sourceView="main";
let armorViewMode="all";
let decoView="type";
let monsterView="basic";
let dragonView="exchange";
let questView="key";
let selectedItemId="";
let restoringHistory=false;
let historyRestoreToken=0;
try{history.scrollRestoration="manual"}catch{}

const APP_VERSION="0.7.7-chat4-monster-link-hotfix11";
const boundEventGroups=new Set();
let appEventsBound=false;
function ensureRuntimeStatus(){
  let box=document.getElementById("appRuntimeStatus");
  if(box)return box;
  box=document.createElement("div");
  box.id="appRuntimeStatus";
  box.className="app-runtime-status";
  box.hidden=true;
  box.setAttribute("role","status");
  const main=document.querySelector("main.content");
  const topbar=main?.querySelector(".topbar");
  if(main)main.insertBefore(box,topbar?.nextSibling||main.firstChild);
  else document.body.prepend(box);
  return box;
}
function showRuntimeStatus(message,level="error"){
  const box=ensureRuntimeStatus();
  box.className=`app-runtime-status ${level}`;
  box.textContent=String(message||"");
  box.hidden=!message;
}
function clearRuntimeStatus(){
  const box=document.getElementById("appRuntimeStatus");
  if(box){box.hidden=true;box.textContent="";box.className="app-runtime-status";}
}
function reportAppError(scope,error,{visible=true}={}){
  const detail=error?.message||String(error||"알 수 없는 오류");
  console.error(`[MH4G:${scope}]`,error);
  if(visible)showRuntimeStatus(`일부 기능 초기화에 실패했습니다. (${scope}: ${detail}) · 메뉴와 다른 기능은 계속 사용할 수 있습니다.`,"error");
}
function safeUiHandler(scope,handler){
  return function(...args){
    try{
      const result=handler.apply(this,args);
      if(result&&typeof result.then==="function")result.catch(err=>reportAppError(scope,err));
      return result;
    }catch(err){reportAppError(scope,err);}
  };
}
function bindEventGroup(name,fn){
  if(boundEventGroups.has(name))return true;
  try{fn();boundEventGroups.add(name);return true;}catch(err){reportAppError(`이벤트:${name}`,err);return false;}
}
function safeInitStep(name,fn){
  try{return fn();}catch(err){reportAppError(`초기화:${name}`,err);return undefined;}
}

// Weapon tree is isolated from app startup. A failure here must never break global navigation.
let weaponTreeIndex={items:{}};
let weaponTreeIndexPromise=null;
const WEAPON_TREE_VERSION="0.7.7-chat4-weapontree7-focusfull";
async function ensureWeaponTreeIndex(){
  if(weaponTreeIndexPromise)return weaponTreeIndexPromise;
  weaponTreeIndexPromise=(async()=>{
    try{
      const r=await fetch(`./data/weapon_tree_index.json?v=${WEAPON_TREE_VERSION}`,{cache:"force-cache"});
      if(!r.ok)throw new Error(`weapon tree index ${r.status}`);
      const x=await r.json();
      weaponTreeIndex=(x&&typeof x==="object"&&!Array.isArray(x))?x:{items:{}};
    }catch(e){console.error("weapon tree index load failed",e);weaponTreeIndex={items:{}};}
    return weaponTreeIndex;
  })();
  return weaponTreeIndexPromise;
}
async function loadWeaponReferenceLocal(weaponId){
  const key=String(weaponId||"").trim();
  if(!key)return {id:key,pathIds:[],finalIds:[],cumulativeMaterials:[]};
  try{
    const r=await fetch(`./data/weapon_refs/${encodeURIComponent(key)}.json?v=${WEAPON_TREE_VERSION}`,{cache:"force-cache"});
    if(!r.ok)throw new Error(`weapon ref ${r.status}`);
    const x=await r.json();
    return (x&&typeof x==="object"&&!Array.isArray(x))?x:{id:key,pathIds:[],finalIds:[],cumulativeMaterials:[]};
  }catch(e){console.error("weapon ref load failed",key,e);return {id:key,pathIds:[],finalIds:[],cumulativeMaterials:[]};}
}

// v0.7.2: 반복 배열 검색과 옵션 재생성을 줄이기 위한 인덱스/캐시
let skillById=new Map(),armorById=new Map(),weaponById=new Map(),decorationByIdMap=new Map(),armorSetById=new Map(),armorSetByPieceId=new Map(),itemByName=new Map(),itemById=new Map();
let itemSearchCorpusById=new Map(),itemDetailHtmlCache=new Map(),itemReferenceCache=new Map(),skillReferenceCache=new Map(),monsterReferenceCache=new Map(),monsterFallbackPromise=null;
let armorSearchQueryContextCache=new Map(),armorSearchCorpusCache=new Map(),armorRowHtmlCache=new Map(),armorProgressionHtmlCache=new Map();
const optionCache={armorByPart:new Map(),weaponByType:new Map(),armorSets:null,skillPicker:null,activation:null,weaponTypes:null};
function rebuildIndexes(){
  skillById=new Map((data.skills||[]).map(x=>[x.id,x]));
  armorById=new Map((data.armors||[]).map(x=>[x.id,x]));
  weaponById=new Map((data.weapons||[]).map(x=>[x.id,x]));
  decorationByIdMap=new Map((data.decorations||[]).map(x=>[x.id,x]));
  armorSetById=new Map((data.armorSets||[]).map(x=>[x.id,x]));
  armorSetByPieceId=new Map();
  for(const set of data.armorSets||[]) for(const piece of set.pieces||[]) armorSetByPieceId.set(piece.id,set);
  itemByName=new Map(); for(const x of data.items||[]){if(x.name)itemByName.set(x.name,x);for(const a of x.aliases||[])if(a&&!itemByName.has(a))itemByName.set(a,x);}
  itemById=new Map((data.items||[]).map(x=>[String(x.id),x]));
  rebuildItemReferenceIndexes();
  optionCache.armorByPart.clear();optionCache.weaponByType.clear();
  optionCache.armorSets=null;optionCache.skillPicker=null;optionCache.activation=null;optionCache.weaponTypes=null;
  armorSetMaterialCache.clear();armorSearchQueryContextCache.clear();armorSearchCorpusCache.clear();armorRowHtmlCache.clear();armorProgressionHtmlCache.clear();
}

const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
const rankName=r=>({low:"하위",high:"상위",g:"G급",all:"전체"}[r]||r||"-");
const hunterName=t=>({blade:"검사",gunner:"거너",both:"공용"}[t]||t||"-");
const resistText=r=>`화 ${r?.fire??0} / 수 ${r?.water??0} / 뇌 ${r?.thunder??0} / 빙 ${r?.ice??0} / 용 ${r?.dragon??0}`;


const PLANNER_STORAGE_KEY="mh4g-planner-v1";
let plannerMemoryStorage="";
function plannerStorageGet(){try{return localStorage.getItem(PLANNER_STORAGE_KEY)}catch{return plannerMemoryStorage||null}}
function plannerStorageSet(value){plannerMemoryStorage=String(value||"");try{localStorage.setItem(PLANNER_STORAGE_KEY,plannerMemoryStorage);return true}catch{return false}}
const EMPTY_PLANNER_STATE=()=>({favorites:{weapon:[],armor:[],recommend:[],quest:[]},craft:{},inventory:{}});
function loadPlannerState(){
  const base=EMPTY_PLANNER_STATE();
  try{
    const raw=plannerStorageGet();if(!raw)return base;
    const x=JSON.parse(raw)||{};
    for(const k of Object.keys(base.favorites))base.favorites[k]=Array.isArray(x.favorites?.[k])?[...new Set(x.favorites[k].map(String))]:[];
    base.craft=x.craft&&typeof x.craft==="object"&&!Array.isArray(x.craft)?x.craft:{};
    base.inventory=x.inventory&&typeof x.inventory==="object"&&!Array.isArray(x.inventory)?x.inventory:{};
  }catch(err){console.warn("planner storage load failed",err);}
  return base;
}
let plannerState=loadPlannerState();
function savePlannerState(){return plannerStorageSet(JSON.stringify(plannerState))}
function plannerFavoriteList(kind){return plannerState.favorites[kind]||(plannerState.favorites[kind]=[])}
function isPlannerFavorite(kind,id){return plannerFavoriteList(kind).includes(String(id))}
function recommendPlannerId(weaponType,rank,index){return `${weaponType}|${rank}|${Number(index)||0}`}
function parseRecommendPlannerId(id){const [weaponType,rank,index]=String(id||"").split("|");return {weaponType,rank,index:Number(index)||0}}
function plannerIconButton(kind,id,{craft=false,label=""}={}){
  const fav=isPlannerFavorite(kind,id);
  const favorite=`<button type="button" class="planner-inline-action ${fav?"is-active":""}" data-planner-favorite-kind="${esc(kind)}" data-planner-favorite-id="${esc(id)}" title="${fav?"즐겨찾기 해제":"즐겨찾기 추가"}" aria-label="${fav?"즐겨찾기 해제":"즐겨찾기 추가"}">${fav?"★":"☆"}</button>`;
  const craftButton=craft?`<button type="button" class="planner-inline-action craft" data-planner-craft-kind="${esc(kind)}" data-planner-craft-id="${esc(id)}" title="제작 목록에 추가" aria-label="제작 목록에 추가">＋</button>`:"";
  return `<span class="planner-inline-actions"${label?` aria-label="${esc(label)}"`:""}>${favorite}${craftButton}</span>`;
}
function parseCraftMaterials(text){
  const out=[];const raw=String(text||"").trim();if(!raw)return out;
  const re=/(.*?)(?:[×*x]\s*(\d+))(?=\s|$)/g;let m;
  while((m=re.exec(raw))){const name=m[1].trim();const count=Number(m[2])||0;if(name&&count)out.push({name,count});}
  return out;
}
function weaponPlannerRecipe(w){
  const rows=(w?.craft||[]).filter(x=>x&&x.materials);
  if(!rows.length)return {label:"소재 정보 없음",materials:[]};
  const row=rows.find(x=>String(x.method||"").includes("생산"))||rows.find(x=>String(x.method||"").includes("강화"))||rows[0];
  return {label:row.method||"제작",materials:parseCraftMaterials(row.materials)};
}
function plannerCraftKey(kind,id){return `${kind}:${id}`}
function addPlannerCraft(kind,id){
  if(!["weapon","armor"].includes(kind))return;
  const key=plannerCraftKey(kind,id),cur=plannerState.craft[key];
  plannerState.craft[key]={kind,id:String(id),qty:Math.max(1,Number(cur?.qty)||0)+(!cur?0:1)};
  savePlannerState();
  if(currentPage==="planner")renderPlanner();
  showRuntimeStatus("제작 목록에 추가했습니다.","success");setTimeout(()=>{if(document.getElementById("appRuntimeStatus")?.classList.contains("success"))clearRuntimeStatus()},1200);
}
function togglePlannerFavorite(kind,id){
  if(!plannerState.favorites[kind])return;
  const key=String(id),list=plannerFavoriteList(kind),idx=list.indexOf(key);
  if(idx>=0)list.splice(idx,1);else list.push(key);
  savePlannerState();
  if(currentPage==="weapon")renderWeaponTrees();
  else if(currentPage==="armor"){armorRowHtmlCache.clear();renderArmorTable();}
  else if(currentPage==="recommend")renderRecommendedLoadouts();
  else if(currentPage==="quest")renderQuest();
  else if(currentPage==="planner")renderPlanner();
}
function plannerCraftEntries(){return Object.values(plannerState.craft||{}).filter(x=>x&&["weapon","armor"].includes(x.kind)&&x.id).map(x=>({...x,qty:Math.max(1,Number(x.qty)||1)}));}
function plannerCraftEntity(entry){return entry.kind==="weapon"?weaponById.get(String(entry.id)):armorById.get(String(entry.id));}
function plannerMaterialTotals(){
  const totals=new Map();
  for(const entry of plannerCraftEntries()){
    const entity=plannerCraftEntity(entry);if(!entity)continue;
    const mats=entry.kind==="weapon"?weaponPlannerRecipe(entity).materials:parseCraftMaterials(entity.materials);
    for(const m of mats)totals.set(m.name,(totals.get(m.name)||0)+m.count*entry.qty);
  }
  return [...totals.entries()].map(([name,need])=>{const owned=Math.max(0,Number(plannerState.inventory[name])||0);return {name,need,owned,missing:Math.max(0,need-owned)}}).sort((a,b)=>b.missing-a.missing||a.name.localeCompare(b.name,"ko"));
}
function plannerFavoriteCard(kind,id){
  if(kind==="weapon"){
    const w=weaponById.get(String(id));if(!w)return "";
    return `<div class="planner-fav-card"><div><span class="planner-kind">무기 · ${esc(w.weaponType||"")}</span><strong>${esc(w.name)}</strong><small>${rankName(w.rank)} · 공격 ${w.attack??"-"} · ${slotsText(w.slots)}</small></div><div class="planner-card-actions">${refButton("열기","weapon",{name:w.name,weapontype:w.weaponType})}${plannerIconButton(kind,id,{craft:true})}</div></div>`;
  }
  if(kind==="armor"){
    const a=armorById.get(String(id));if(!a)return "";
    return `<div class="planner-fav-card"><div><span class="planner-kind">방어구 · ${esc(PART_NAMES[a.part]||a.part)}</span><strong>${esc(a.name)}</strong><small>${rankName(a.rank)} · ${hunterName(a.hunterType)} · DEF ${a.defense||0}</small></div><div class="planner-card-actions">${refButton("열기","armor",{name:a.name})}${plannerIconButton(kind,id,{craft:true})}</div></div>`;
  }
  if(kind==="quest"){
    const q=(data.quests||[]).find(x=>String(x.id)===String(id));if(!q)return "";
    return `<div class="planner-fav-card"><div><span class="planner-kind">퀘스트 · ${esc(q.questTypeLabel||q.questType||"")}</span><strong>${esc(q.name)}</strong><small>${esc(q.level||"")} · ${esc(q.location||"")}</small></div><div class="planner-card-actions">${refButton("열기","quest",{name:q.name,questtype:q.questType})}${plannerIconButton(kind,id)}</div></div>`;
  }
  if(kind==="recommend"){
    const key=parseRecommendPlannerId(id),entry=(data.recommendedLoadouts?.entries||[]).find(x=>x.weaponType===key.weaponType&&x.rank===key.rank),v=entry?.variants?.[key.index];if(!entry||!v)return "";
    return `<div class="planner-fav-card"><div><span class="planner-kind">추천 장비 · ${esc(entry.weaponType)} · ${esc(entry.rankLabel||rankName(entry.rank))}</span><strong>${esc(v.label)}</strong><small>${esc(v.style||"")} · DEF ${Number(v.build?.defense||0)}</small></div><div class="planner-card-actions"><button type="button" class="xref-link" data-planner-open-recommend="${esc(id)}">열기</button>${plannerIconButton(kind,id)}</div></div>`;
  }
  return "";
}
function renderPlanner(){
  const summary=$("#plannerSummary"),favRoot=$("#plannerFavorites"),craftRoot=$("#plannerCraftList"),matRoot=$("#plannerMaterials");if(!summary||!favRoot||!craftRoot||!matRoot)return;
  const favCount=Object.values(plannerState.favorites).reduce((n,x)=>n+(x?.length||0),0),craft=plannerCraftEntries(),mats=plannerMaterialTotals(),missing=mats.reduce((n,x)=>n+x.missing,0);
  summary.innerHTML=`<span>즐겨찾기 <b>${favCount}</b></span><span>제작 장비 <b>${craft.reduce((n,x)=>n+x.qty,0)}</b></span><span>필요 소재 <b>${mats.length}종</b></span><span>부족 합계 <b>${missing}</b></span>`;
  const sections=[['weapon','무기'],['armor','방어구'],['recommend','추천 장비'],['quest','퀘스트']].map(([kind,label])=>{const cards=plannerFavoriteList(kind).map(id=>plannerFavoriteCard(kind,id)).filter(Boolean).join("");return cards?`<section class="planner-fav-group"><h3>${label}</h3>${cards}</section>`:""}).join("");
  favRoot.innerHTML=sections||'<div class="result-empty">아직 즐겨찾기가 없습니다. 무기·방어구·추천 장비·퀘스트에서 ☆ 버튼을 눌러 추가할 수 있습니다.</div>';
  craftRoot.innerHTML=craft.length?craft.map(entry=>{const x=plannerCraftEntity(entry);if(!x)return "";const recipe=entry.kind==="weapon"?weaponPlannerRecipe(x):{label:"생산",materials:parseCraftMaterials(x.materials)};return `<div class="planner-craft-row" data-planner-craft-key="${esc(plannerCraftKey(entry.kind,entry.id))}"><div><span class="planner-kind">${entry.kind==="weapon"?`무기 · ${esc(x.weaponType||"")}`:`방어구 · ${esc(PART_NAMES[x.part]||x.part)}`}</span><strong>${esc(x.name)}</strong><small>${esc(recipe.label)} · ${recipe.materials.length?recipe.materials.map(m=>`${esc(m.name)} ×${m.count}`).join(" · "):"소재 정보 없음"}</small></div><div class="planner-qty"><button type="button" data-planner-craft-delta="-1" aria-label="수량 감소">−</button><input type="number" min="1" max="99" value="${entry.qty}" data-planner-craft-qty="${esc(plannerCraftKey(entry.kind,entry.id))}" aria-label="제작 수량"><button type="button" data-planner-craft-delta="1" aria-label="수량 증가">＋</button><button type="button" class="ghost small" data-planner-craft-remove="${esc(plannerCraftKey(entry.kind,entry.id))}">삭제</button></div></div>`}).join(""):'<div class="result-empty">제작 목록이 비어 있습니다. 무기·방어구의 ＋ 버튼으로 추가하세요.</div>';
  matRoot.innerHTML=mats.length?`<div class="planner-material-head"><span>소재</span><span>필요</span><span>보유</span><span>부족</span></div>${mats.map(m=>`<div class="planner-material-row ${m.missing?"is-missing":"is-complete"}"><div>${itemLink(m.name)}</div><b>${m.need}</b><input type="number" min="0" max="9999" value="${m.owned}" data-planner-inventory="${esc(m.name)}" aria-label="${esc(m.name)} 보유 수량"><strong>${m.missing}</strong></div>`).join("")}`:'<div class="result-empty">제작 목록에 장비를 추가하면 필요한 소재를 합산합니다.</div>';
}
async function openPlannerRecommendation(id){
  const key=parseRecommendPlannerId(id);recommendWeaponType=key.weaponType;recommendRank=key.rank;await navigatePage("recommend",{after:()=>{populateRecommendFilters();$("#recommendWeaponType").value=recommendWeaponType;$("#recommendRank").value=recommendRank;renderRecommendedLoadouts();const cards=$$("#recommendContent .recommend-variant");cards[key.index]?.scrollIntoView({block:"center",behavior:"auto"});}});
}

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
  return [s.name,s.nameJa,s.nameEn,SKILL_SEARCH_ALIASES[s.name]||"",...(s.activations||[]).flatMap(a=>[a.name,a.nameJa,a.nameEn,a.description,Number(a.points)>0?`+${a.points}`:String(a.points)])].map(cleanEffectText).join(" ");
}
function decorationSearchCorpus(d){
  const positiveEffects=Object.entries(d.skills||{}).filter(([,v])=>Number(v)>0).map(([k])=>skillSearchCorpus(k)).join(" ");
  const allSkillNames=Object.keys(d.skills||{}).map(skillName).join(" ");
  return `${d.name||""} ${d.nameJa||""} ${d.nameEn||""} ${allSkillNames} ${positiveEffects} ${d.materials||""}`;
}
function activationOptions(){
  if(optionCache.activation)return optionCache.activation;
  const rows=[{value:"__torso_up__",skillId:"__torso_up__",label:"몸통배가 (방어구 특수효과)",name:"몸통배가",points:0,category:"특수효과",meta:"胴系統倍加 · Torso Up · 몸통 방어구의 스킬 포인트와 장식주 효과를 배가",search:"몸통배가 동계통배가 몸통 배가 胴系統倍加 torso up torso-up 특수효과"}];
  for(const skill of data.skills){
    for(const a of skill.activations||[]){
      if(Number(a.points)>0){const sub=[a.nameJa,a.nameEn].filter(Boolean).join(" · ");rows.push({value:a.id,skillId:skill.id,label:`${a.name} (${a.points}P · ${skill.name})`,name:a.name,points:a.points,category:skill.name,meta:[sub,shortEffect(a.description)].filter(Boolean).join(" · "),search:`${skillSearchCorpus(skill)} ${a.name} ${a.nameJa||""} ${a.nameEn||""} ${a.points}`});}
    }
  }
  optionCache.activation=rows.sort((a,b)=>a.name.localeCompare(b.name,"ko"));
  return optionCache.activation;
}
function skillPickerOptions(){
  if(optionCache.skillPicker)return optionCache.skillPicker;
  optionCache.skillPicker=data.skills.map(s=>({value:s.id,label:s.name,meta:[s.nameJa,s.nameEn].filter(Boolean).join(" · "),search:skillSearchCorpus(s)})).sort((a,b)=>a.label.localeCompare(b.label,"ko"));
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

function mountSearchSelect(selector,options,{value="",placeholder="검색 또는 선택",emptyLabel="선택 안 함",onChange=()=>{},debounceMs=0}={}){
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
    filtered=options.filter(o=>!q||(typeof o.matchQuery==="function"?o.matchQuery(q):o._searchLower.includes(q))).slice(0,120);
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
  let inputTimer=null;
  input.oninput=()=>{
    highlightedIndex=-1;
    if(inputTimer)clearTimeout(inputTimer);
    if(debounceMs>0) inputTimer=setTimeout(()=>draw(input.value),debounceMs);
    else draw(input.value);
  };
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
  if($("#autoWeaponType")){
    $("#autoWeaponType").innerHTML=WEAPON_TYPES.filter(t=>data.weapons.some(w=>w.weaponType===t)).map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("");
    if(!WEAPON_TYPES.includes(uiState.autoWeaponType))uiState.autoWeaponType="대검";
    $("#autoWeaponType").value=uiState.autoWeaponType;
    $("#autoWeaponType").onchange=e=>{uiState.autoWeaponType=e.target.value||"대검"};
  }
  if($("#autoWeaponSlots")){
    const slot=Math.max(0,Math.min(3,Number(uiState.autoWeaponSlots)||0));
    uiState.autoWeaponSlots=slot;
    $("#autoWeaponSlots").value=String(slot);
    $("#autoWeaponSlots").onchange=e=>{uiState.autoWeaponSlots=Math.max(0,Math.min(3,Number(e.target.value)||0))};
  }
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

function getOwnedCharms(){try{const v=JSON.parse(localStorage.getItem(OWNED_CHARMS_STORAGE_KEY)||"[]");return Array.isArray(v)?v:[]}catch{return []}}
function setOwnedCharms(list){try{localStorage.setItem(OWNED_CHARMS_STORAGE_KEY,JSON.stringify(list));return true}catch{return false}}
function normalizeCharmRecord(c={}){const skills={};for(const [id,v] of Object.entries(c.skills||{})){const n=Number(v)||0;if(id&&n)skills[id]=n}return {id:String(c.id||`charm_${Date.now()}_${Math.random().toString(36).slice(2,8)}`),skills,slots:Math.max(0,Math.min(3,Number(c.slots)||0))}}
function charmLabel(c){const ss=Object.entries(c?.skills||{}).map(([id,v])=>`${skillName(id)} ${Number(v)>0?"+":""}${Number(v)}`);return `${ss.length?ss.join(" / "):"스킬 없음"} · ${slotsText(c?.slots||0)}`}
function renderOwnedCharms(){const root=$("#ownedCharmList");if(!root)return;const list=getOwnedCharms();root.innerHTML=list.length?list.map((c,i)=>`<div class="owned-charm-row"><span>${esc(charmLabel(c))}</span><span class="owned-charm-actions"><button type="button" class="ghost small" data-owned-charm-apply="${i}">적용</button><button type="button" class="ghost small" data-owned-charm-remove="${i}">삭제</button></span></div>`).join(""):'<div class="muted">등록된 보유 호석이 없습니다.</div>'}
function saveCurrentCharmToOwned(){const c=normalizeCharmRecord(charm());if(!Object.keys(c.skills).length&&!c.slots){showRuntimeStatus("저장할 호석 스킬 또는 슬롯을 먼저 입력하세요.","info");return}const list=getOwnedCharms();const sig=JSON.stringify({skills:c.skills,slots:c.slots});if(!list.some(x=>JSON.stringify({skills:x.skills||{},slots:Number(x.slots)||0})===sig)){list.push(c);setOwnedCharms(list)}renderOwnedCharms()}
function applyOwnedCharm(index){const c=getOwnedCharms()[Number(index)];if(!c)return;const e=Object.entries(c.skills||{});uiState.charmSkill1=e[0]?.[0]||"";uiState.charmPoint1=Number(e[0]?.[1]||0);uiState.charmSkill2=e[1]?.[0]||"";uiState.charmPoint2=Number(e[1]?.[1]||0);uiState.charmSlots=Number(c.slots||0);renderManualSelectors();renderManualResult();renderOwnedCharms()}
function removeOwnedCharm(index){const list=getOwnedCharms();list.splice(Number(index),1);setOwnedCharms(list);renderOwnedCharms()}
function targetRequirementForActivationIds(ids){const out={};for(const aid of ids||[])for(const sk of data.skills||[])for(const a of sk.activations||[])if(a.id===aid&&Number(a.points)>0)out[sk.id]=Math.max(Number(out[sk.id]||0),Number(a.points)||0);return out}
function scoreOwnedCharm(c,req){let s=Number(c.slots||0)*0.75;for(const [id,need] of Object.entries(req||{}))s+=Math.min(Math.max(0,Number(c.skills?.[id]||0)),Number(need))*4;return s}
function compareMergedAutoResults(a,b){const am=a.metrics||{},bm=b.metrics||{};return (am.negativeSkillCount||0)-(bm.negativeSkillCount||0)||(am.targetWastePoints||0)-(bm.targetWastePoints||0)||(bm.remainingSlots||0)-(am.remainingSlots||0)||(am.usedDecorationSlots||0)-(bm.usedDecorationSlots||0)||(bm.defense||0)-(am.defense||0)}
function requiredCharmConditionFromNear(near){const misses=near?.missing||[];if(!misses.length)return "추가 호석 조건 산출 불가";const parts=misses.map(x=>`${skillName(x.skillId)} +${Number(x.missing||0)}`);return `${parts.join(" / ")} · 슬롯3이면 장식주 보완 여지 증가 (충분 조건)`}

function getSavedBuilds(){try{const v=JSON.parse(localStorage.getItem(BUILD_STORAGE_KEY)||"[]");return Array.isArray(v)?v:[]}catch{return []}}
function setSavedBuilds(list){localStorage.setItem(BUILD_STORAGE_KEY,JSON.stringify(list))}
function renderSavedBuilds(selectedId=""){
  const el=$("#savedBuildSelect"); if(!el)return;
  const list=getSavedBuilds();
  el.innerHTML='<option value="">저장한 세팅</option>'+list.map(b=>`<option value="${esc(b.id)}" ${b.id===selectedId?"selected":""}>${esc(b.name)}</option>`).join("");
}
function saveCurrentBuild(){
  const list=getSavedBuilds();
  const selectedId=$("#savedBuildSelect")?.value||"";
  const existingIndex=selectedId?list.findIndex(x=>x.id===selectedId):-1;
  const name=$("#buildName")?.value.trim()||(existingIndex>=0?list[existingIndex].name:`세팅 ${list.length+1}`);
  const rec={
    id:existingIndex>=0?list[existingIndex].id:`build_${Date.now()}_${Math.random().toString(36).slice(2,7)}`,name,
    targets:[...targets],
    manualSet:uiState.manualSet,manualWeapon:uiState.manualWeapon,manualWeaponType:uiState.manualWeaponType,manualWeaponRank:uiState.manualWeaponRank,manualWeaponElement:uiState.manualWeaponElement,manualWeaponSlots:uiState.manualWeaponSlots,manual:{...uiState.manual},
    charmSkill1:uiState.charmSkill1,charmPoint1:uiState.charmPoint1,charmSkill2:uiState.charmSkill2,charmPoint2:uiState.charmPoint2,charmSlots:uiState.charmSlots,
    manualDecorations:Object.fromEntries(MANUAL_CONTAINERS.map(c=>[c,[...(uiState.manualDecorations[c]||[])]]))
  };
  if(existingIndex>=0) list[existingIndex]=rec; else list.push(rec);
  setSavedBuilds(list);renderSavedBuilds(rec.id);if($("#buildName"))$("#buildName").value=rec.name;
}
function loadSelectedBuild(){
  const rec=getSavedBuilds().find(x=>x.id===$("#savedBuildSelect")?.value);if(!rec)return;
  targets=[...(rec.targets||[])];
  uiState.manualSet=rec.manualSet||"";uiState.manualWeapon=rec.manualWeapon||"";uiState.manualWeaponType=rec.manualWeaponType||"all";uiState.manualWeaponRank=rec.manualWeaponRank||"all";uiState.manualWeaponElement=rec.manualWeaponElement||"all";uiState.manualWeaponSlots=String(rec.manualWeaponSlots??"all");uiState.manual={...Object.fromEntries(PARTS.map(p=>[p,""])),...(rec.manual||{})};
  uiState.charmSkill1=rec.charmSkill1||"";uiState.charmPoint1=Number(rec.charmPoint1||0);uiState.charmSkill2=rec.charmSkill2||"";uiState.charmPoint2=Number(rec.charmPoint2||0);uiState.charmSlots=Number(rec.charmSlots||0);
  uiState.manualDecorations=Object.fromEntries(MANUAL_CONTAINERS.map(c=>[c,[...(rec.manualDecorations?.[c]||[])]]));
  if($("#buildName")) $("#buildName").value=rec.name||"";
  fillSelectors();renderTargets();renderManualSelectors();renderManualResult();
}
function deleteSelectedBuild(){const id=$("#savedBuildSelect")?.value;if(!id)return;setSavedBuilds(getSavedBuilds().filter(x=>x.id!==id));renderSavedBuilds();if($("#buildName"))$("#buildName").value=""}

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
function armorSkillSearchCorpus(a){
  const key=a?.id||a?.name||"";
  const cached=armorSearchCorpusCache.get(key);
  if(cached?.skillText!=null)return cached.skillText;
  const skillIds=Object.keys(a?.skills||{});
  const skillText=skillIds.map(id=>{
    const sk=skillDefinition(id);
    if(!sk)return skillName(id);
    const activationNames=(sk.activations||[]).flatMap(x=>[x.name,x.nameJa,x.nameEn]);
    return [sk.name,sk.nameJa,sk.nameEn,SKILL_SEARCH_ALIASES[sk.name]||"",...activationNames].filter(Boolean).join(" ");
  }).join(" ");
  const normalText=`${a?.name||""} ${a?.nameJa||""} ${a?.nameEn||""} ${hunterName(a?.hunterType)} ${rankName(a?.rank)} ${a?.materials||""}`.toLowerCase();
  armorSearchCorpusCache.set(key,{skillText,skillTextLower:skillText.toLowerCase(),normalText});
  return skillText;
}
const ARMOR_RANK_ORDER={g:0,high:1,low:2};
function armorRankCompare(a,b){
  return (ARMOR_RANK_ORDER[a?.rank]??9)-(ARMOR_RANK_ORDER[b?.rank]??9)
    || String(a?.name||"").localeCompare(String(b?.name||""),"ko");
}
const TORSO_UP_SEARCH_TERMS=["몸통배가","동계통배가","몸통 배가","胴系統倍加","torso up","torso-up"];
function armorSearchQueryContext(query){
  const q=String(query||"").trim().toLowerCase();
  if(armorSearchQueryContextCache.has(q))return armorSearchQueryContextCache.get(q);
  const exactSkillIds=[];
  let looksLikeSkill=false;
  if(q){
    for(const sk of data.skills||[]){
      const exactNames=[sk.name,sk.nameJa,sk.nameEn].filter(Boolean).map(x=>String(x).toLowerCase());
      if(exactNames.includes(q))exactSkillIds.push(sk.id);
      if(!looksLikeSkill&&q.length>=2){
        const names=[sk.name,sk.nameJa,sk.nameEn,SKILL_SEARCH_ALIASES[sk.name]||"",...(sk.activations||[]).flatMap(x=>[x.name,x.nameJa,x.nameEn])].filter(Boolean);
        looksLikeSkill=names.some(x=>String(x).toLowerCase().includes(q));
      }
    }
  }
  const torsoExact=!!q&&TORSO_UP_SEARCH_TERMS.some(term=>term.toLowerCase()===q);
  const torsoLike=q.length>=2&&TORSO_UP_SEARCH_TERMS.some(term=>term.toLowerCase().includes(q)||q.includes(term.toLowerCase()));
  const ctx={q,exactSkillIds,looksLikeSkill,torsoExact,torsoLike};
  if(armorSearchQueryContextCache.size>80)armorSearchQueryContextCache.clear();
  armorSearchQueryContextCache.set(q,ctx);
  return ctx;
}
function armorSkillQueryIds(query){return armorSearchQueryContext(query).exactSkillIds}
function armorLooksLikeSkillQuery(query){return armorSearchQueryContext(query).looksLikeSkill}
function armorIsTorsoUpQuery(query){return armorSearchQueryContext(query).torsoExact}
function armorLooksLikeTorsoUpQuery(query){return armorSearchQueryContext(query).torsoLike}
function armorMatchesSearch(a,query){
  const ctx=armorSearchQueryContext(query);
  if(!ctx.q)return true;
  if(ctx.torsoExact)return !!a.torsoUp;
  if(ctx.exactSkillIds.length)return ctx.exactSkillIds.some(id=>Object.prototype.hasOwnProperty.call(a.skills||{},id));
  if(ctx.torsoLike)return !!a.torsoUp;
  const key=a?.id||a?.name||"";
  let cached=armorSearchCorpusCache.get(key);
  if(!cached){armorSkillSearchCorpus(a);cached=armorSearchCorpusCache.get(key)}
  if(ctx.looksLikeSkill)return (cached?.skillTextLower||"").includes(ctx.q);
  return (cached?.normalText||"").includes(ctx.q);
}
function armorPickerOptions(part){
  if(optionCache.armorByPart.has(part))return optionCache.armorByPart.get(part);
  const opts=data.armors.filter(a=>a.part===part).sort(armorRankCompare).map(a=>{
    const torso=a.torsoUp?" · 몸통배가":"",torsoSearch=a.torsoUp?"몸통배가 동계통배가 胴系統倍加 Torso Up":"";
    const skills=a.torsoUp?"몸통배가":skillPointsPlain(a.skills||{},"스킬 없음");
    return {
      value:a.id,label:a.name,
      meta:`${rankName(a.rank)} · ${hunterName(a.hunterType)} · ${skills} · 슬롯 ${slotsText(a.slots)} · DEF ${a.defense} · 내성 ${resistText(a.resistances)}${torso}`,
      search:`${a.name} ${a.nameJa||""} ${a.nameEn||""} ${hunterName(a.hunterType)} ${rankName(a.rank)} ${armorSkillSearchCorpus(a)} ${torsoSearch} ${a.materials||""}`,
      matchQuery:q=>armorMatchesSearch(a,q)
    };
  });
  optionCache.armorByPart.set(part,opts);return opts;
}
function manualWeaponTypeOptions(){
  if(optionCache.weaponTypes)return optionCache.weaponTypes;
  optionCache.weaponTypes=WEAPON_TYPES.filter(t=>data.weapons.some(w=>w.weaponType===t));return optionCache.weaponTypes;
}
const WEAPON_RANK_ORDER={g:0,high:1,low:2};
function weaponRankCompare(a,b){
  return (WEAPON_RANK_ORDER[a?.rank]??9)-(WEAPON_RANK_ORDER[b?.rank]??9)
    || String(a?.weaponType||"").localeCompare(String(b?.weaponType||""),"ko")
    || String(a?.name||"").localeCompare(String(b?.name||""),"ko");
}
function weaponSharpnessText(w){
  if(RANGED_TYPES.has(w?.weaponType))return "";
  const colors={red:"빨강",orange:"주황",yellow:"노랑",green:"초록",blue:"파랑",white:"흰색",purple:"보라"};
  const segs=w?.sharpness?.normal?.segments||[];
  const colored=segs.filter(x=>x?.color&&x.color!=="gray"&&Number(x.length||0)>0);
  const top=colored[colored.length-1];
  return top?.color?`예리도 ${colors[top.color]||top.color}`:"";
}
function weaponPropertyBits(w){
  const bits=[];
  for(const p of [w?.elementPrimary,w?.elementSecondary]) if(p?.type&&Number(p?.value||0)) bits.push(`속성 ${p.type} ${Number(p.value)}`);
  if(w?.awakenElement?.type&&Number(w?.awakenElement?.value||0)) bits.push(`각성 ${w.awakenElement.type} ${Number(w.awakenElement.value)}`);
  if(Number(w?.defenseBonus||0)) bits.push(`방어 +${Number(w.defenseBonus)}`);
  if(!bits.length&&w?.element) bits.push(`속성/효과 ${w.element}`);
  return bits;
}
function weaponAffinityText(w){
  const raw=String(w?.affinityText??w?.affinity??0).trim()||"0";
  if(raw.includes("/"))return `${raw}%`;
  const n=Number(raw);return `${Number.isFinite(n)&&n>0?"+":""}${raw}%`;
}
function weaponPickerMeta(w){
  const bits=[rankName(w.rank),`슬롯 ${slotsText(w.slots)}`,`공격 ${w.attack??"-"}`,...weaponPropertyBits(w)];
  if(String(w?.affinityText??w?.affinity??0)!=="0")bits.push(`회심 ${weaponAffinityText(w)}`);
  const sharp=weaponSharpnessText(w);if(sharp)bits.push(sharp);
  const extra=weaponExtra(w);if(extra)bits.push(`특성 ${extra}`);
  if(Array.isArray(w.melodyEffects)&&w.melodyEffects.length)bits.push(`선율효과 ${w.melodyEffects.join(" / ")}`);
  return bits.join(" · ");
}
function manualWeaponElementTypes(w){
  return [w?.elementPrimary?.type,w?.elementSecondary?.type,w?.awakenElement?.type].filter(Boolean);
}
function weaponMatchesManualFilters(w){
  const type=uiState.manualWeaponType||"all";
  const rank=uiState.manualWeaponRank||"all";
  const element=uiState.manualWeaponElement||"all";
  const slots=String(uiState.manualWeaponSlots??"all");
  if(type!=="all"&&w.weaponType!==type)return false;
  if(rank!=="all"&&w.rank!==rank)return false;
  const types=manualWeaponElementTypes(w);
  if(element==="none"&&types.length)return false;
  if(element!=="all"&&element!=="none"&&!types.includes(element))return false;
  if(slots!=="all"&&Number(w.slots||0)!==Number(slots))return false;
  return true;
}
function weaponPickerOptions(){
  const key=[uiState.manualWeaponType||"all",uiState.manualWeaponRank||"all",uiState.manualWeaponElement||"all",String(uiState.manualWeaponSlots??"all")].join("|");
  if(optionCache.weaponByType.has(key))return optionCache.weaponByType.get(key);
  const opts=data.weapons
    .filter(weaponMatchesManualFilters)
    .sort(weaponRankCompare)
    .map(w=>({
      value:w.id,
      label:w.name,
      meta:weaponPickerMeta(w),
      // 외국어 이름은 선택창에 표시하지 않고 기존 검색 호환용으로만 유지한다.
      search:`${w.name} ${w.nameJa||""} ${w.nameEn||""} ${w.weaponType} ${rankName(w.rank)} ${w.tree||""} ${w.element||""} ${weaponPropertyBits(w).join(" ")} ${weaponExtra(w)} ${(w.melodyEffects||[]).join(" ")}`
    }));
  optionCache.weaponByType.set(key,opts);return opts;
}
const ARMOR_SET_RESIST_LABELS={fire:"화",water:"수",thunder:"뇌",ice:"빙",dragon:"용"};
function armorSetPickerOptions(){
  const sortKey=uiState.armorSetSort||"name";
  const list=data.armorSets.slice();
  list.sort((a,b)=>{
    if(sortKey==="defense")return Number(b.maxDefense||b.defense||0)-Number(a.maxDefense||a.defense||0)||Number(b.defense||0)-Number(a.defense||0)||a.name.localeCompare(b.name,"ko");
    if(ARMOR_SET_RESIST_LABELS[sortKey])return Number(b.resistances?.[sortKey]||0)-Number(a.resistances?.[sortKey]||0)||Number(b.maxDefense||b.defense||0)-Number(a.maxDefense||a.defense||0)||a.name.localeCompare(b.name,"ko");
    return a.name.localeCompare(b.name,"ko");
  });
  return list.map(s=>({
    value:s.id,
    label:s.name,
    meta:`${hunterName(s.hunterType)} · ${rankName(s.rank)} · 방어 ${Number(s.defense||0)}/${Number(s.maxDefense||s.defense||0)} · ${resistText(s.resistances)} · 슬롯 ${Number(s.slots||0)}칸`,
    search:`${s.name} ${hunterName(s.hunterType)} ${rankName(s.rank)} 방어 ${s.defense||0} ${s.maxDefense||0} ${resistText(s.resistances)} ${Object.keys(s.skills||{}).map(skillName).join(" ")}`
  }));
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
  return data.decorations
    .filter(d=>Number(d.slots||0)>0&&Number(d.slots||0)<=remain)
    .sort((a,b)=>Number(a.slots)-Number(b.slots)||a.name.localeCompare(b.name,"ko"))
    .map(d=>{
      const effects=Object.entries(d.skills||{})
        .sort(([,av],[,bv])=>Number(bv)-Number(av))
        .map(([k,v])=>`${skillName(k)} ${Number(v)>0?"+":""}${v}`)
        .join(" · ");
      return {
        value:d.id,
        label:d.name,
        meta:`${effects||"스킬 포인트 없음"} · 필요 ${d.slots}칸`,
        search:decorationSearchCorpus(d)
      };
    });
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
  const armorSetSortEl=$("#armorSetSort");
  if(armorSetSortEl){
    armorSetSortEl.value=["name","defense","fire","water","thunder","ice","dragon"].includes(uiState.armorSetSort)?uiState.armorSetSort:"name";
    armorSetSortEl.onchange=()=>{uiState.armorSetSort=armorSetSortEl.value||"name";renderManualSelectors();};
  }

  const box=$("#manualEquipmentBuilder");
  box.innerHTML=
    `<div class="manual-equipment-card weapon-card"><div class="manual-equipment-main"><span class="equipment-label">무기</span><div class="manual-weapon-tools"><div class="manual-weapon-filters"><select id="manualWeaponTypeFilter" aria-label="시뮬레이터 무기 종류"><option value="all">전체 무기</option>${manualWeaponTypeOptions().map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join("")}</select><select id="manualWeaponRankFilter" aria-label="무기 등급"><option value="all">전체 등급</option><option value="g">G급</option><option value="high">상위</option><option value="low">하위</option></select><select id="manualWeaponElementFilter" aria-label="무기 속성"><option value="all">전체 속성</option><option value="불">불</option><option value="물">물</option><option value="번개">번개</option><option value="얼음">얼음</option><option value="용">용</option><option value="독">독</option><option value="마비">마비</option><option value="수면">수면</option><option value="폭파">폭파</option><option value="none">무속성</option></select><select id="manualWeaponSlotFilter" aria-label="무기 슬롯"><option value="all">전체 슬롯</option><option value="3">슬롯 3</option><option value="2">슬롯 2</option><option value="1">슬롯 1</option><option value="0">슬롯 0</option></select><button type="button" id="manualWeaponSearchButton" class="manual-weapon-search-btn">검색</button></div><div id="manual-weapon" class="search-select manual-weapon-results"></div></div>${skillPointsHtml(containerSkillPoints("weapon"),"equipment-skill-points")}</div><div id="deco-editor-weapon" class="manual-deco-editor"></div></div>`+
    PARTS.map(p=>equipmentCard(PART_NAMES[p],p,`manual-${p}`)).join("")+
    `<div class="manual-equipment-card charm-card"><div class="manual-equipment-main charm-main"><span class="equipment-label">호석</span><div class="manual-charm-inline"><span class="inline-field-label">스킬1</span><div id="charmSkill1Picker" class="search-select compact"></div><input id="charmPoint1" class="charm-point" type="number" min="-20" max="20" value="${uiState.charmPoint1}" /><span class="inline-field-label">스킬2</span><div id="charmSkill2Picker" class="search-select compact"></div><input id="charmPoint2" class="charm-point" type="number" min="-20" max="20" value="${uiState.charmPoint2}" /><span class="inline-field-label">슬롯</span><select id="charmSlots" class="charm-slot-select"><option value="0">---</option><option value="1">O--</option><option value="2">OO-</option><option value="3">OOO</option></select></div>${skillPointsHtml(containerSkillPoints("charm"),"equipment-skill-points")}<div class="owned-charm-inline"><div class="owned-charm-controls"><button type="button" class="ghost small" data-save-owned-charm>현재 호석 저장</button><label><input id="ownedCharmsOnly" type="checkbox" ${uiState.ownedCharmsOnly?"checked":""}/> 자동조합에서 보유 호석만 사용</label></div><div id="ownedCharmList" class="owned-charm-list"></div></div></div><div id="deco-editor-charm" class="manual-deco-editor"></div></div>`;

  const manualTypeEl=$("#manualWeaponTypeFilter");
  const manualRankEl=$("#manualWeaponRankFilter");
  const manualElementEl=$("#manualWeaponElementFilter");
  const manualSlotEl=$("#manualWeaponSlotFilter");
  const manualSearchBtn=$("#manualWeaponSearchButton");
  if(manualTypeEl&&manualRankEl&&manualElementEl&&manualSlotEl&&manualSearchBtn){
    const availableTypes=manualWeaponTypeOptions();
    manualTypeEl.value=availableTypes.includes(uiState.manualWeaponType)?uiState.manualWeaponType:"all";
    manualRankEl.value=["all","g","high","low"].includes(uiState.manualWeaponRank)?uiState.manualWeaponRank:"all";
    manualElementEl.value=["all","불","물","번개","얼음","용","독","마비","수면","폭파","none"].includes(uiState.manualWeaponElement)?uiState.manualWeaponElement:"all";
    manualSlotEl.value=["all","3","2","1","0"].includes(String(uiState.manualWeaponSlots))?String(uiState.manualWeaponSlots):"all";
    manualSearchBtn.onclick=()=>{
      uiState.manualWeaponType=manualTypeEl.value||"all";
      uiState.manualWeaponRank=manualRankEl.value||"all";
      uiState.manualWeaponElement=manualElementEl.value||"all";
      uiState.manualWeaponSlots=manualSlotEl.value||"all";
      const current=selectedWeapon();
      if(current&&!weaponMatchesManualFilters(current)){uiState.manualWeapon="";uiState.manualDecorations.weapon=[];}
      mountManualWeaponSearch();refreshManualContainer("weapon");renderManualResult();
    };
  }
  mountManualWeaponSearch();
  for(const p of PARTS){
    const opts=armorPickerOptions(p);
    mountSearchSelect(`#manual-${p}`,opts,{value:uiState.manual[p],placeholder:`${PART_NAMES[p]} 검색 (${opts.length}개)`,emptyLabel:`선택 안 함 (${opts.length}개)`,debounceMs:60,onChange:v=>{
      uiState.manual[p]=v;uiState.manualDecorations[p]=[];refreshManualContainer(p);renderManualResult();
    }});
  }
  mountSearchSelect("#charmSkill1Picker",skillPickerOptions(),{value:uiState.charmSkill1,placeholder:"스킬 검색",emptyLabel:"없음",onChange:v=>{uiState.charmSkill1=v;renderManualResult()}});
  mountSearchSelect("#charmSkill2Picker",skillPickerOptions(),{value:uiState.charmSkill2,placeholder:"스킬 검색",emptyLabel:"없음",onChange:v=>{uiState.charmSkill2=v;renderManualResult()}});
  $("#charmPoint1").oninput=e=>{uiState.charmPoint1=Number(e.target.value||0);renderManualResult()};
  $("#charmPoint2").oninput=e=>{uiState.charmPoint2=Number(e.target.value||0);renderManualResult()};
  $("#charmSlots").value=String(uiState.charmSlots||0);$("#charmSlots").onchange=e=>{uiState.charmSlots=Number(e.target.value||0);pruneDecorations("charm");refreshManualContainer("charm");renderManualResult()};
  if($("#ownedCharmsOnly"))$("#ownedCharmsOnly").onchange=e=>{uiState.ownedCharmsOnly=!!e.target.checked};
  renderOwnedCharms();
  MANUAL_CONTAINERS.forEach(mountDecorationEditor);
}

function renderSkillResult(calc,{compact=false}={}){
  const validName=v=>{const t=String(v??"").trim();return t&&t!=="undefined"&&t!=="null"?t:""};
  const activeRows=(calc.activated||[]).filter(a=>validName(a?.name)).sort((a,b)=>{
    const an=Number(a?.threshold),bn=Number(b?.threshold);
    const ar=an>0?0:1,br=bn>0?0:1;
    return ar-br||validName(a.name).localeCompare(validName(b.name),"ko");
  });
  const active=activeRows.length?activeRows.map(a=>{const st=currentSkillStatus(a.skillId,a.points);return `<span class="skill-active ${Number(a.threshold)<0?"skill-negative":""}" title="${esc(st.effect)}">${esc(validName(a.name))}</span>`}).join(""):'<span class="muted">발동 스킬 없음</span>';
  const rows=Object.entries(calc.points||{}).sort((a,b)=>{
    const pointDiff=Number(b[1]||0)-Number(a[1]||0);
    return pointDiff||skillName(a[0]).localeCompare(skillName(b[0]),"ko");
  }).map(([id,p])=>{
    const st=currentSkillStatus(id,p),activeName=validName(st.active?.name),nextName=validName(st.next?.name);
    const trigger=activeName?`${Number(st.active.points)>0?"+":""}${Number(st.active.points)}`:(nextName?`${Number(st.next.points)>0?"+":""}${Number(st.next.points)}`:"-");
    let applied="",effect="";
    if(activeName){applied=`<strong>${esc(activeName)}</strong><small>${trigger} 발동</small>`;effect=st.effect||"효과 설명 없음"}
    else if(nextName&&st.tone==="pending"){applied=`<span>미발동</span><small>다음 ${trigger} → ${esc(nextName)}</small>`;effect=st.effect?`다음 효과: ${st.effect}`:"다음 발동 효과 설명 없음"}
    else{applied='<span>미발동</span>';effect=st.effect||"-"}
    return compact?`<tr><td>${skillLink(id,skillName(id))}</td><td>${Number(p)>0?"+":""}${Number(p)}</td><td>${applied}</td></tr>`:`<tr><td>${skillLink(id,skillName(id))}</td><td>${Number(p)>0?"+":""}${Number(p)}</td><td>${applied}</td><td>${esc(effect)}</td></tr>`;
  }).join("");
  if(compact)return `<div class="skill-summary">${active}</div><div class="muted">방어력 ${calc.defense} · ${resistText(calc.resist)} · 몸통배가 ${calc.torsoUpCount}개</div><div class="skill-result-table-wrap compact"><table class="skill-points"><colgroup><col class="col-tree"><col class="col-point"><col class="col-active"></colgroup><thead><tr><th>스킬 계통</th><th>포인트</th><th>발동 스킬</th></tr></thead><tbody>${rows||'<tr><td colspan="3" class="skill-empty-row">포인트 없음</td></tr>'}</tbody></table></div>`;
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
    const armorMeta=a?`<small>${slotsText(a.slots)}</small><small class="loadout-resist">DEF ${Number(a.defense||0)} · ${esc(resistText(a.resistances))}</small>`:"";
    gear.push(`<div><b>${PART_NAMES[p]}</b><span>${esc(a?.name||"-")} ${armorMeta}</span>${skillCell(p)}</div>`);
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
  const decolines={};for(const p of b.decorations){const did=typeof p.deco==="string"?p.deco:p.deco?.id;const key=`${p.container}:${did}`;decolines[key]=(decolines[key]||0)+1}
  const decoText=Object.entries(decolines).map(([key,n])=>{const [container,id]=key.split(":"),d=data.decorations.find(x=>x.id===id),label={weapon:"무기",head:"머리",body:"몸통",arms:"팔",waist:"허리",legs:"다리",charm:"호석"}[container]||container;return `${label} ${d?.name||id} ×${n}`}).join(" · ");
  const resistTotal=Object.values(b.calc?.resist||{}).reduce((sum,v)=>sum+Number(v||0),0);
  return `<article class="build-card build-card-clickable" data-auto-build="${i}" tabindex="0" role="button" aria-label="조합 ${i+1}을 시뮬레이터에 적용"><h3><span>조합 ${i+1}</span><span class="score">DEF ${b.calc.defense} · 내성합 ${resistTotal>=0?"+":""}${resistTotal}</span></h3><div class="build-equipment"><span class="label">무기</span><span>${esc(b.autoWeapon?.name||autoWeaponType())} <span class="slots">${slotsText(b.autoWeapon?.slots||b.autoWeaponRequiredSlots||0)}</span>${b.autoWeaponRequiredSlots?` <small>필요 ${b.autoWeaponRequiredSlots}슬롯</small>`:""}</span>${PARTS.map(p=>{const a=b.armors.find(x=>x.part===p);return `<span class="label">${PART_NAMES[p]}</span><span>${esc(a?.name||"-")} <span class="slots">${slotsText(a?.slots)}</span></span>`}).join("")}</div><div class="deco-line">${b.searchCharm?`사용 호석: ${esc(charmLabel(b.searchCharm))}<br>`:""}${decoText?`장식주: ${esc(decoText)}`:"장식주 없음"}</div>${renderSkillResult(b.calc,{compact:true})}<div class="build-card-action">카드 클릭 → 시뮬레이터에 적용</div></article>`;
}
const AUTO_RANK_VALUE={low:0,high:1,g:2};
function autoWeaponType(){return uiState.autoWeaponType||"대검"}
function autoHunterType(){return RANGED_TYPES.has(autoWeaponType())?"gunner":"blade"}
function autoWeaponPool(progression="g"){const max=AUTO_RANK_VALUE[progression]??2;return data.weapons.filter(w=>w.weaponType===autoWeaponType()&&(AUTO_RANK_VALUE[w.rank]??9)<=max)}
function autoSearchWeaponSlots(){return Math.max(0,Math.min(3,Number(uiState.autoWeaponSlots)||0))}
function autoWeaponForSlots(requiredSlots=0,progression="g"){const req=Math.max(0,Number(requiredSlots)||0),fixed=autoSearchWeaponSlots();if(req>fixed)return null;const pool=autoWeaponPool(progression).filter(w=>Number(w.slots||0)===fixed);pool.sort((a,b)=>(AUTO_RANK_VALUE[b.rank]??-1)-(AUTO_RANK_VALUE[a.rank]??-1)||Number(b.attack||0)-Number(a.attack||0)||Number(b.affinity||0)-Number(a.affinity||0)||String(a.name).localeCompare(String(b.name),"ko"));return pool[0]||null}
function weaponSlotsUsedByBuild(b){return (b?.decorations||[]).reduce((n,p)=>n+(p.container==="weapon"?Number((typeof p.deco==="string"?decorationByIdMap.get(p.deco):p.deco)?.slots||0):0),0)}
function attachAutoWeapons(result,progression,includeTorsoUp=true){const fixed=autoSearchWeaponSlots();for(const b of [...(result.results||[]),...(result.nearMisses||[])]){const need=weaponSlotsUsedByBuild(b);b.autoWeapon=autoWeaponForSlots(need,progression);b.autoWeaponRequiredSlots=need;b.autoWeaponSelectedSlots=fixed;if(b.autoWeapon){b.calc=calculateBuild({armors:b.armors||[],charm:b.searchCharm||charm(),weaponSlots:fixed,decorations:b.decorations||[]},data,includeTorsoUp)}}result.results=(result.results||[]).filter(b=>b.autoWeapon);result.nearMisses=(result.nearMisses||[]).filter(b=>b.autoWeapon);return result}

function autoSearchConditionText(){
  const progression=$("#autoProgressionRank")?.value||"g";
  const fixedSlots=autoSearchWeaponSlots();
  const c=charm();
  const charmSkills=Object.entries(c.skills||{}).filter(([,v])=>Number(v)!==0).map(([id,v])=>`${skillName(id)} ${Number(v)>0?"+":""}${Number(v)}`);
  return `무기종 ${esc(autoWeaponType())} · 무기 슬롯 ${fixedSlots} 고정 · ${uiState.ownedCharmsOnly?`보유 호석만 사용 (${getOwnedCharms().length}개)`:`호석 ${charmSkills.length?charmSkills.map(esc).join(" / "):"스킬 없음"} · 호석 슬롯 ${Number(c.slots||0)}`}`;
}
function renderNearMissCard(b,i){
  const missing=(b.missing||[]).map(x=>`${skillName(x.skillId)} ${Number(x.have||0)}/${Number(x.need||0)} (${Number(x.missing||0)}pt 부족)`).join(" · ");
  const decoCount=(b.decorations||[]).length;
  const slot=b.slotCompletion||{};
  const completion=slot.slotOnlyCompletable
    ? (Number(slot.minAdditionalSlots||0)>0?`슬롯만 보강 시 최소 +${Number(slot.minAdditionalSlots)}슬롯 필요`:`현재 남은 슬롯 재배치로 완성 가능`)
    : `추가 9슬롯 이내 장식주만으로는 완성 어려움 · 호석 스킬 자체 보강 필요`;
  const free=`현재 미사용 슬롯 ${Number(slot.currentFreeSlots||0)}칸`;
  return `<article class="build-card near-miss-card build-card-clickable" data-auto-near="${i}" tabindex="0" role="button" aria-label="근접 후보 ${i+1}을 시뮬레이터에 적용"><h3><span>근접 후보 ${i+1}</span><span class="score">목표 미완성</span></h3><div class="build-equipment"><span class="label">무기</span><span>${esc(b.autoWeapon?.name||autoWeaponType())} <span class="slots">${slotsText(b.autoWeapon?.slots||b.autoWeaponRequiredSlots||0)}</span>${b.autoWeaponRequiredSlots?` <small>필요 ${b.autoWeaponRequiredSlots}슬롯</small>`:""}</span>${PARTS.map(p=>{const a=b.armors.find(x=>x.part===p);return `<span class="label">${PART_NAMES[p]}</span><span>${esc(a?.name||"-")} <span class="slots">${slotsText(a?.slots)}</span></span>`}).join("")}</div>${b.searchCharm?`<div class="near-miss-deficit"><b>검토 호석</b> ${esc(charmLabel(b.searchCharm))}</div>`:""}<div class="near-miss-deficit"><b>추가 필요</b> ${esc(missing||"목표 포인트 부족")}</div><div class="near-miss-deficit"><b>완성 가능성</b> ${esc(completion)} · ${esc(free)}</div><div class="near-miss-deficit"><b>필요 호석 충분 조건</b> ${esc(requiredCharmConditionFromNear(b))}</div><div class="muted">현재 조건에서 배치한 장식주 ${decoCount}개 · DEF ${Number(b.calc?.defense||0)} · ${esc(resistText(b.calc?.resist||{}))}</div><div class="build-card-action">근접 후보 적용 → 시뮬레이터에서 직접 보완</div></article>`;
}
function applyAutoBuildRecordToSimulator(b){
  if(!b)return;
  if(b.searchCharm){const e=Object.entries(b.searchCharm.skills||{});uiState.charmSkill1=e[0]?.[0]||"";uiState.charmPoint1=Number(e[0]?.[1]||0);uiState.charmSkill2=e[1]?.[0]||"";uiState.charmPoint2=Number(e[1]?.[1]||0);uiState.charmSlots=Number(b.searchCharm.slots||0)}
  if(b.autoWeapon){uiState.manualWeapon=b.autoWeapon.id;uiState.manualWeaponType=b.autoWeapon.weaponType||"all"}
  uiState.manualSet="";
  for(const p of PARTS){const a=b.armors.find(x=>x.part===p);uiState.manual[p]=a?.id||"";}
  uiState.manualDecorations=Object.fromEntries(MANUAL_CONTAINERS.map(c=>[c,[]]));
  for(const placed of b.decorations||[]){
    const id=typeof placed.deco==="string"?placed.deco:placed.deco?.id;
    if(id&&uiState.manualDecorations[placed.container])uiState.manualDecorations[placed.container].push(id);
  }
  renderManualSelectors();renderManualResult();
  document.querySelector("#manualEquipmentBuilder")?.scrollIntoView({behavior:"smooth",block:"start"});
}
function applyAutoBuildToSimulator(index){applyAutoBuildRecordToSimulator(latestAutoSearchResults[Number(index)])}
function applyAutoNearMissToSimulator(index){applyAutoBuildRecordToSimulator(latestAutoSearchNearMisses[Number(index)])}
async function searchAutoWithCharmMode(baseOptions){
  const ownedOnly=uiState.ownedCharmsOnly===true;
  if(!ownedOnly)return await searchBuilds({...baseOptions,charm:charm()},data);
  const owned=getOwnedCharms().map(normalizeCharmRecord);
  if(!owned.length)return {results:[],nearMisses:[],stats:{message:"보유 호석만 사용이 켜져 있지만 등록된 호석이 없습니다."}};
  const req=targetRequirementForActivationIds(targets);
  const ordered=[...owned].sort((a,b)=>scoreOwnedCharm(b,req)-scoreOwnedCharm(a,req));
  const mergedResults=[],mergedNear=[];let elapsedMs=0,eligible=0,checkedFinalists=0,finalists=0,timedOut=false;
  const perBudget=Math.max(1600,Math.floor(12000/Math.max(1,ordered.length)));
  for(let i=0;i<ordered.length;i++){
    const c=ordered[i];
    baseOptions.onProgress?.({phase:"ownedCharm",current:i+1,total:ordered.length,label:charmLabel(c)});
    const r=await searchBuilds({...baseOptions,charm:c,timeBudgetMs:perBudget,limit:Math.min(12,Number(baseOptions.limit||20))},data);
    elapsedMs+=Number(r.stats?.elapsedMs||0);eligible=Math.max(eligible,Number(r.stats?.eligible||0));checkedFinalists+=Number(r.stats?.checkedFinalists||0);finalists+=Number(r.stats?.finalists||0);timedOut=timedOut||!!r.stats?.timedOut;
    mergedResults.push(...(r.results||[]).map(x=>({...x,searchCharm:c})));
    mergedNear.push(...(r.nearMisses||[]).map(x=>({...x,searchCharm:c})));
  }
  mergedResults.sort(compareMergedAutoResults);
  mergedNear.sort((a,b)=>Number(!a.slotCompletion?.slotOnlyCompletable)-Number(!b.slotCompletion?.slotOnlyCompletable)||Number(a.slotCompletion?.minAdditionalSlots??99)-Number(b.slotCompletion?.minAdditionalSlots??99)||(a.missingTotal||0)-(b.missingTotal||0));
  return {results:mergedResults.slice(0,Number(baseOptions.limit||20)),nearMisses:mergedNear.slice(0,3),stats:{eligible,checkedFinalists,finalists,timedOut,elapsedMs,ownedCharmsSearched:ordered.length,profile:"owned-charms"}};
}

async function runSearch(){
  if(!targets.length){$("#searchResults").innerHTML='<div class="result-empty">먼저 원하는 스킬을 추가하세요.</div>';return}
  const btn=$("#runSearch");btn.disabled=true;btn.textContent="검색 중…";
  const conditionText=autoSearchConditionText();
  $("#searchStats").textContent=`검색 준비 중 · ${conditionText}`;
  try{
    const simHunter=autoHunterType();
    const progression=$("#autoProgressionRank")?.value||"g";
    const progressionLabel={low:"하위",high:"상위",g:"G급"}[progression]||"전체";
    const fixedWeaponSlots=autoSearchWeaponSlots();
    if(!autoWeaponPool(progression).some(w=>Number(w.slots||0)===fixedWeaponSlots)){
      $("#searchStats").textContent=`${progressionLabel} ${autoWeaponType()} 중 ${fixedWeaponSlots}슬롯 무기가 없어 검색할 수 없습니다.`;
      $("#searchResults").innerHTML='<div class="result-empty">선택한 진행도·무기종에 해당 슬롯 수의 무기가 없습니다. 무기 슬롯 조건을 바꿔주세요.</div>';
      return;
    }
    const r=await searchAutoWithCharmMode({
      targetActivationIds:targets,
      hunterType:simHunter,
      rank:progression,
      weaponSlots:autoSearchWeaponSlots(),
      allowDecorations:$("#allowDecorations").checked,
      includeTorsoUp:$("#includeTorsoUp").checked,
      limit:Number($("#resultLimit").value||20),
      preferredSkillWeights:weaponPreferredSkillWeights(simHunter),
      onProgress:p=>{
        if(p.phase==="armor")$("#searchStats").textContent=`방어구 후보 계산 ${p.current}/${p.total} · 후보 ${p.beam||0}개 · ${conditionText}`;
        else if(p.phase==="decorate")$("#searchStats").textContent=`장식주 조합 검증 ${p.current}/${p.total} · 완성 ${p.exact||0}개 · ${conditionText}`;
        else if(p.phase==="ownedCharm")$("#searchStats").textContent=`보유 호석 비교 ${p.current}/${p.total} · ${p.label||""}`;
      }
    });
    attachAutoWeapons(r,progression,$("#includeTorsoUp").checked);
    latestAutoSearchResults=r.results||[];
    latestAutoSearchNearMisses=r.nearMisses||[];
    const sec=(Number(r.stats?.elapsedMs||0)/1000).toFixed(1);
    const statusBase=`검색 타입 ${hunterName(simHunter)} · 진행도 ${progressionLabel} · 대상 방어구 ${r.stats.eligible||0}개 · 검증 후보 ${r.stats.checkedFinalists??r.stats.finalists??0}/${r.stats.finalists||0} · ${sec}초 · ${conditionText}`;
    if(r.stats.message){
      $("#searchStats").textContent=r.stats.message;
    }else if(latestAutoSearchResults.length){
      $("#searchStats").textContent=`${statusBase}${r.stats.timedOut?" · 시간 제한 내 발견된 결과만 표시":""} · 고속 후보검색(완전탐색 아님)`;
    }else{
      $("#searchStats").textContent=`${statusBase} · ${r.stats.timedOut?"시간 제한 내 완성 조합 미발견":"완성 조합 미발견"} · 고속 후보검색(완전탐색 아님)`;
    }
    if(latestAutoSearchResults.length){
      $("#searchResults").innerHTML=latestAutoSearchResults.map(renderBuildCard).join("");
    }else if((r.nearMisses||[]).length){
      const top=r.nearMisses[0];
      const missing=(top.missing||[]).map(x=>`${skillName(x.skillId)} +${Number(x.missing||0)}pt`).join(" · ");
      const slot=top.slotCompletion||{};
      const slotGuide=slot.slotOnlyCompletable
        ? (Number(slot.minAdditionalSlots||0)>0?`장식주 기준 최소 ${Number(slot.minAdditionalSlots)}슬롯을 더 확보하면 완성 가능한 후보입니다.`:`남은 슬롯의 장식주 배치를 다시 최적화하면 완성 가능성이 있습니다.`)
        : `추가 슬롯만으로는 해결하기 어려워 목표 스킬이 붙은 호석 자체가 필요합니다.`;
      const nextStep=`${slotGuide} 필요 호석 충분 조건: ${requiredCharmConditionFromNear(top)}`;
      $("#searchResults").innerHTML=`<div class="search-guidance"><b>현재 조건에서 완성 조합을 찾지 못했습니다.</b><p>가장 가까운 후보 기준으로 <strong>${esc(missing||"추가 스킬 포인트")}</strong>가 더 필요합니다. ${esc(nextStep)}</p><p class="muted">자동조합은 선택한 무기종·진행도·무기 슬롯 수를 고정해서 실제 무기를 함께 찾고, 호석 스킬/슬롯도 통합 계산합니다.</p></div>${r.nearMisses.map(renderNearMissCard).join("")}`;
    }else{
      $("#searchResults").innerHTML='<div class="result-empty">현재 조건의 고속 탐색 범위에서 완성 조합을 찾지 못했습니다. 호석 스킬 또는 무기/호석 슬롯을 추가한 뒤 다시 검색해 보세요.</div>';
    }
  }catch(e){
    console.error("auto search failed",e);
    $("#searchStats").textContent="자동조합 계산 중 오류가 발생했습니다.";
    $("#searchResults").innerHTML=`<div class="result-empty">검색을 완료하지 못했습니다. ${esc(e?.message||String(e))}</div>`;
  }finally{btn.disabled=false;btn.textContent="조합 검색"}
}

function decorateResponsiveTable(table){
  if(!table)return;
  table.classList.add("responsive-table");
  const headers=[...table.querySelectorAll("thead th")].map(th=>th.textContent.trim());
  const wideLabels=new Set([
    "명칭","퀘스트","클리어 조건","서브퀘스트","특수조건","비고","효과/비고",
    "스킬","스킬 합계","발동 조건","효과 및 비고","획득/제작 역추적","내성","내성 합계","입수","특성",
    "생산 소재","세트 제작 소재","생산/강화 소재","필요 아이템","해금 조건/퀘스트","선율 효과","해당 무기",
    "리로드/반동/흔들림","속사","특수","모으기","병","선율/효과","벌레","예리도"
  ]);
  table.querySelectorAll("tbody tr").forEach(tr=>{
    if(tr.classList.contains('armor-detail-row'))return;
    [...tr.children].forEach((td,i)=>{
      if(td.tagName!=="TD"||td.classList.contains("result-empty"))return;
      const label=headers[i]||"";
      td.dataset.label=label;
      if(i===0)td.classList.add("mobile-title-cell");
      if(wideLabels.has(label)||td.classList.contains("wrap-cell")||td.classList.contains("col-craft")||td.classList.contains("col-sharpness"))td.classList.add("mobile-wide-cell");
      const text=td.textContent.trim();
      if(!text||text==="-")td.dataset.empty="true";
    });
  });
}
function decorateResponsiveTables(root=document){root.querySelectorAll("table.data-table").forEach(decorateResponsiveTable)}
function renderTable(el,headers,rows){
  const root=$(el);
  root.innerHTML=`<table class="data-table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.length?rows.join(""):`<tr><td colspan="${headers.length}" class="result-empty">검색 결과 없음</td></tr>`}</tbody></table>`;
  decorateResponsiveTables(root);
  bindInlineItemLinks(root);
}
function localizedNameSub(x){
  const main=String(x?.name||"").trim();
  const names=[x?.nameJa,x?.nameEn].map(v=>String(v||"").trim()).filter((v,i,a)=>v&&v!==main&&a.indexOf(v)===i);
  return names.length?`<small>${names.map(esc).join(" · ")}</small>`:"";
}

function progressionQuestNavMeta(src={}){
  const rawType=String(src.questType||"").toLowerCase();
  const rawLevel=String(src.level||"");
  const m=rawLevel.match(/(\d+)/);
  const star=m?Number(m[1]):0;
  let questtype="",level="",label="퀘스트";
  if(rawType==="caravan"||rawType==="village"){questtype="village";level=star?`★${star}`:"";label=star?`여단 ★${star}`:"여단";}
  else if(rawType==="guild"||rawType==="hub"){
    if(star>=8){questtype="g";level=`★${star-7}`;label=`G★${star-7}`;}
    else{questtype="hub";level=star?`★${star}`:"";label=star?`집회소 ★${star}`:"집회소";}
  }else if(rawType==="g"){questtype="g";level=star?`★${star}`:"";label=star?`G★${star}`:"G급";}
  else if(rawType==="event"){questtype="event";level=rawLevel.startsWith("G★")?rawLevel:(star>=8?`G★${star-7}`:(star?`★${star}`:""));label=level?`이벤트 ${level}`:"이벤트";}
  else if(rawType==="challenge"){questtype="challenge";level=rawLevel;label=rawLevel?`챌린지 ${rawLevel}`:"챌린지";}
  else if(rawType==="guildquest"){questtype="";level="";label=rawLevel||"길드퀘스트";}
  else{level=rawLevel;label=rawLevel||"퀘스트";}
  return {questtype,level,label};
}
function progressionQuestFilterButton(src,material,labelOverride=""){
  const meta=progressionQuestNavMeta(src);
  const label=labelOverride||meta.label;
  const materialName=typeof material==="string"?material:(material?.name||"");
  const monster=typeof material==="object"?(material?.sources||[]).find(x=>x?.type==="monster"&&x?.navMonster)?.navMonster||"":"";
  return refButton(label,"questfilter",{questtype:meta.questtype,level:meta.level,reward:materialName,monster,source:src?.name||""});
}

function armorProgressionSourceHtml(src,material){
  const type=src?.type||"";
  if(type==="monster"){
    const methodKo={"Body Carve":"몸통 갈무리","Capture":"포획","Shiny Drop":"유실물","Tail Carve":"꼬리 갈무리","Break Head":"머리 파괴","Mining Back":"등 채굴","Break Back":"등 파괴","Break Horn":"뿔 파괴","Break Fin":"지느러미 파괴","Break Blowhole":"분기공 파괴","Break Wing":"날개 파괴","Break Belly":"배 파괴","Break Chest":"가슴 파괴","Break Tail":"꼬리 파괴","Break Front Leg":"앞다리 파괴","Mining Scale":"비늘 채굴","Break Wing Leg":"날개다리 파괴","Mining Ore":"광석 채굴","Mouth Carve":"입 갈무리","Break Claw":"발톱 파괴","Break Cover Skin":"외피 파괴","Break Poison Stinger":"독침 파괴","Break Eye":"눈 파괴","Break Body":"몸통 파괴","Break Antenna":"더듬이 파괴","Break Talon":"갈고리발톱 파괴","Break Ear":"귀 파괴"};
    const methods=(src.methods||[]).slice(0,3).map(v=>String(v).replace(/^([^·]+?)(?= ·|$)/,m=>methodKo[m.trim()]||m.trim())).join(" / ");
    const label=esc(src.name||"몬스터");
    const monsterLink=src.navMonster?refButton(src.name||"몬스터","monster",{monster:src.navMonster,item:material.name}):`<b>${label}</b>`;
    return `<li><span class="armor-progress-kind">몬스터</span>${monsterLink}${src.rank?` <small>${esc(src.rank)}</small>`:""}${methods?`<small>${esc(methods)}</small>`:""}</li>`;
  }
  if(type==="quest"){
    if(src.id){
      const label=`${src.level||""} ${src.name||"퀘스트"}`.trim();
      return `<li><span class="armor-progress-kind ${src.questType==="event"?"event":""}">${src.questType==="event"?"이벤트":"퀘스트"}</span>${refButton(label,"quest",{name:src.name,questtype:src.questType})}${src.note?`<small>${esc(src.note)}</small>`:""}</li>`;
    }
    if(src.questType==="event"){
      const label=`${src.level||""} ${src.name||"이벤트 퀘스트"}`.trim();
      return `<li><span class="armor-progress-kind event">이벤트</span>${progressionQuestFilterButton(src,material,label)}${src.note?`<small>${esc(src.note)}</small>`:""}</li>`;
    }
    const meta=progressionQuestNavMeta(src);
    const link=progressionQuestFilterButton(src,material,`${meta.label} 보수`);
    return `<li><span class="armor-progress-kind">퀘스트</span>${link}<small>해당 등급과 보상 소재로 프로젝트 퀘스트를 바로 필터링합니다.</small></li>`;
  }
  if(type==="event"){
    const qsrc={...src,questType:"event"};
    const label=`${src.level||""} ${src.name||"이벤트 퀘스트"}`.trim();
    return `<li><span class="armor-progress-kind event">이벤트</span>${progressionQuestFilterButton(qsrc,material,label)}${src.note?`<small>${esc(src.note)}</small>`:""}</li>`;
  }
  if(type==="exchange"){
    const req=src.required?itemLink(src.required):"교환 재료";
    const unlock=src.unlockQuestId?refButton(`${src.unlockLevel||""} ${src.unlockQuest||"해금 퀘스트"}`.trim(),"quest",{name:src.unlockQuest,questtype:"g"}):esc(src.unlockQuest||"");
    return `<li><span class="armor-progress-kind exchange">용인교환</span><span class="armor-exchange-route"><b>교환 재료</b> ${req}<span class="armor-exchange-arrow">→</span><b>획득</b> ${itemLink(material.name)}</span>${unlock?`<small>해금: ${unlock}</small>`:""}</li>`;
  }
  if(type==="facility"){
    const unlock=src.unlockQuestId?refButton(`${src.unlockLevel||""} ${src.unlockQuest||"해금 퀘스트"}`.trim(),"quest",{name:src.unlockQuest,questtype:"g"}):esc(src.unlockQuest||"");
    return `<li><span class="armor-progress-kind facility">특수입수</span><b>${esc(src.label||"특수 입수")}</b>${unlock?`<small>해금: ${unlock}</small>`:""}${src.note?`<small>${esc(src.note)}</small>`:""}</li>`;
  }
  if(type==="arena")return `<li><span class="armor-progress-kind arena">투기대회</span><b>${esc(src.name||"투기대회")}</b><small>${src.probability!=null?`${src.probability}%`:""}</small></li>`;
  if(type==="shop")return `<li><span class="armor-progress-kind shop">상점</span><span>${esc(src.label||"상점에서 직접 구입")}</span></li>`;
  if(type==="gather")return `<li><span class="armor-progress-kind gather">채집</span><b>${esc(src.label||"필드 채집")}</b>${src.note?`<small>${esc(src.note)}</small>`:""}</li>`;
  if(type==="special")return `<li><span class="armor-progress-kind special">해금조건</span><b>${esc(src.label||"특수조건")}</b>${src.note?`<small>${esc(src.note)}</small>`:""}</li>`;
  if(type==="unknown")return `<li><span class="armor-progress-kind unknown">확인필요</span><b>${esc(src.label||"입수 경로 추가 확인 필요")}</b>${src.note?`<small>${esc(src.note)}</small>`:""}</li>`;
  return `<li><span class="armor-progress-kind">입수</span><span>${esc(src.label||src.note||"입수처 확인")}</span></li>`;
}
function armorProgressionHtml(a,p){
  const cacheKey=a?.id||a?.name||"";
  if(cacheKey&&armorProgressionHtmlCache.has(cacheKey))return armorProgressionHtmlCache.get(cacheKey);
  if(!p?.materials?.length)return '<div class="armor-progress-empty muted">제작 진행 데이터가 없습니다.</div>';
  const eventQs=(p.targets?.quests||[]).filter(q=>q.questType==="event");
  const mons=(p.targets?.monsters||[]).slice(0,6);
  const quick=[];
  if(eventQs.length)quick.push(`<div class="armor-progress-quick"><b>이벤트</b>${eventQs.slice(0,4).map(q=>q.id?refButton(`${q.level||""} ${q.name}`.trim(),"quest",{name:q.name,questtype:q.questType}):progressionQuestFilterButton(q,"",`${q.level||""} ${q.name}`.trim())).join(" ")}</div>`);
  if(mons.length)quick.push(`<div class="armor-progress-quick"><b>주요 몬스터</b>${mons.map(m=>{const x=typeof m==="string"?{name:m,navMonster:m}:m;return x.navMonster?refButton(x.name,"monster",{monster:x.navMonster}):`<span>${esc(x.name)}</span>`}).join(" ")}</div>`);
  const mats=p.materials.map(m=>`<section class="armor-progress-material"><div class="armor-progress-material-head">${itemLink(m.name)} <b>×${Number(m.count)||1}</b></div><ul>${(m.sources||[]).map(src=>armorProgressionSourceHtml(src,m)).join("")||'<li><span class="muted">입수 경로 데이터 없음</span></li>'}</ul></section>`).join("");
  const html=`<div class="armor-progress-panel"><div class="armor-progress-panel-head"><b>${esc(a.name)} 제작 진행</b><span>소재 ${p.materials.length}종</span></div>${quick.length?`<div class="armor-progress-quick-row">${quick.join("")}</div>`:""}<div class="armor-progress-material-grid">${mats}</div></div>`;
  if(cacheKey)armorProgressionHtmlCache.set(cacheKey,html);
  return html;
}

function armorRowHtml(a){
  const key=a?.id||a?.name||"";
  if(key&&armorRowHtmlCache.has(key))return armorRowHtmlCache.get(key);
  const aid=esc(a.id||key);
  const main=`<tr class="armor-db-row" data-armor-id="${aid}" tabindex="0" role="button" aria-expanded="false" title="행을 클릭하면 제작 진행을 펼칩니다"><td><span class="armor-row-chevron" aria-hidden="true">▶</span><strong>${esc(a.name)}</strong>${localizedNameSub(a)}${plannerIconButton("armor",a.id,{craft:true,label:`${a.name} 즐겨찾기/제작`})}</td><td>${hunterName(a.hunterType)}</td><td>${PART_NAMES[a.part]||a.part}</td><td>${a.rare||"-"}</td><td>${a.defense||0} / ${a.maxDefense||a.defense||0}</td><td class="slots">${slotsText(a.slots)}</td><td>${a.torsoUp?"몸통배가":Object.entries(a.skills||{}).map(([k,v])=>`${skillLink(k,skillName(k))} ${v>0?"+":""}${v}`).join(", ")}</td><td>${resistText(a.resistances)}</td><td>${rankName(a.rank)}</td><td class="wrap-cell">${materialLinks(a.materials||"")}</td></tr>`;
  const detail=`<tr class="armor-detail-row" data-armor-detail="${aid}" hidden><td colspan="10"><div class="armor-detail-host"></div></td></tr>`;
  const html=main+detail;
  if(key)armorRowHtmlCache.set(key,html);
  return html;
}
async function toggleArmorProgressRow(row,force){
  if(!row)return;
  const detail=row.nextElementSibling;
  if(!detail?.matches?.('.armor-detail-row'))return;
  const open=force==null?detail.hidden:Boolean(force);
  if(open){
    const host=detail.querySelector('.armor-detail-host');
    if(host&&!host.dataset.hydrated&&!host.dataset.loading){
      host.dataset.loading='1';
      host.innerHTML='<div class="armor-progress-empty muted">제작 진행 불러오는 중…</div>';
      const a=armorById.get(row.dataset.armorId)||data.armors.find(x=>x.id===row.dataset.armorId);
      try{
        const p=a?await loadArmorProgression(a.id):null;
        host.innerHTML=a?armorProgressionHtml(a,p):'<div class="armor-progress-empty muted">장비 데이터를 찾지 못했습니다.</div>';
        host.dataset.hydrated='1';
      }catch(err){
        reportAppError("방어구 제작 진행",err);
        host.innerHTML='<div class="armor-progress-empty muted">제작 진행 데이터를 불러오지 못했습니다. 다른 기능은 계속 사용할 수 있습니다.</div>';
      }finally{delete host.dataset.loading;}
    }
  }
  detail.hidden=!open;row.setAttribute('aria-expanded',open?'true':'false');row.classList.toggle('expanded',open);
}
const ARMOR_RENDER_BATCH=180;
let armorRenderLimit=ARMOR_RENDER_BATCH;
let armorRenderQueryKey="";
function renderArmorTable(){
  const q=$("#armorSearch").value.trim().toLowerCase(),part=$("#armorPartFilter").value;
  const queryCtx=armorSearchQueryContext(q); // 검색 의도 판정은 렌더링당 한 번만 계산
  const queryKey=[q,part,$("#hunterType")?.value||"both",$("#rankFilter")?.value||"all",armorViewMode].join("|");
  if(queryKey!==armorRenderQueryKey){armorRenderQueryKey=queryKey;armorRenderLimit=ARMOR_RENDER_BATCH;}
  const matches=data.armors.filter(a=>(part==="all"||a.part===part)&&armorEligible(a)&&(armorViewMode!=="other"||(a.source||"").endsWith("/armor/etc.htm")))
    .filter(a=>armorMatchesSearch(a,queryCtx.q)).sort(armorRankCompare);
  const shown=matches.slice(0,armorRenderLimit);
  renderTable("#armorTable",["명칭","타입","부위","RARE","방어(초기/최대)","슬롯","스킬","내성","등급","생산 소재"],shown.map(armorRowHtml));
  const root=$("#armorTable");
  if(!root)return;
  const remain=Math.max(0,matches.length-shown.length);
  const footer=document.createElement("div");
  footer.className="armor-result-footer";
  footer.innerHTML=`<span>검색 결과 ${matches.length.toLocaleString("ko-KR")}개 · 현재 ${shown.length.toLocaleString("ko-KR")}개 표시</span>${remain?`<button type="button" class="ghost small" id="armorLoadMore">더 보기 (${Math.min(ARMOR_RENDER_BATCH,remain)}개)</button>`:""}`;
  root.appendChild(footer);
  const more=$("#armorLoadMore");
  if(more)more.onclick=safeUiHandler("방어구 더 보기",()=>{armorRenderLimit+=ARMOR_RENDER_BATCH;renderArmorTable();});
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
function itemLink(name,label=name){
  const key=String(name||"").trim();
  if(!key||!itemByName.has(key))return esc(label||key||"-");
  return `<button type="button" class="inline-item-link" data-open-item="${esc(key)}">${esc(label||key)}</button>`;
}
function materialLinks(text){
  const raw=String(text||""); if(!raw)return "-";
  const re=/(.*?)([×*]\s*\d+)(?=\s|$)/g;let out="",last=0,m;
  while((m=re.exec(raw))){
    const prefix=m[1],count=m[2],leading=(prefix.match(/^\s*/)||[""])[0],name=prefix.slice(leading.length).trim();
    out+=esc(raw.slice(last,m.index))+esc(leading)+(itemByName.has(name)?itemLink(name):esc(name))+esc(count);last=re.lastIndex;
  }
  out+=esc(raw.slice(last));
  return out||esc(raw);
}
function parseMaterialCounts(text){
  const raw=String(text||"").trim(),out=[];if(!raw)return out;
  const re=/(.*?)[×*]\s*(\d+)(?=\s|$)/g;let m;
  while((m=re.exec(raw))){
    const name=String(m[1]||"").trim();
    if(name)out.push([name,Number(m[2])||0]);
  }
  return out;
}
const armorSetMaterialCache=new Map();
function armorSetMaterials(set){
  const key=String(set?.id||set?.name||"");
  if(key&&armorSetMaterialCache.has(key))return armorSetMaterialCache.get(key);
  const counts=new Map();
  for(const piece of set?.pieces||[]){
    const armor=armorById.get(piece.id);
    for(const [name,count] of parseMaterialCounts(armor?.materials||""))counts.set(name,(counts.get(name)||0)+count);
  }
  const text=[...counts.entries()].map(([name,count])=>`${name}*${count}`).join(" ");
  if(key)armorSetMaterialCache.set(key,text);
  return text;
}
function captureAppHistoryState(){
  return {
    mh4g:true,page:currentPage,selectedItemId:String(selectedItemId||""),itemSearch:$("#itemSearch")?.value||"",
    monsterSelected:$("#monsterSelect")?.value||"all",sourceView,armorViewMode,decoView,monsterView,dragonView,questView,
    recommendWeaponType,recommendRank,scrollY:Math.max(0,Math.round(window.scrollY||0))
  };
}
function replaceCurrentHistoryState(){
  if(restoringHistory)return;
  try{history.replaceState(captureAppHistoryState(),"",location.href)}catch{}
}
function pushCurrentHistoryState(){
  if(restoringHistory)return;
  try{history.pushState(captureAppHistoryState(),"",location.href)}catch{}
}
async function navigatePage(page,{source=null,after=null}={}){
  if(restoringHistory){
    if(source)sourceView=source;
    await openPage(page);
    if(after)await after();
    return;
  }
  replaceCurrentHistoryState();
  if(source)sourceView=source;
  await openPage(page);
  if(after)await after();
  pushCurrentHistoryState();
}
async function restoreAppHistoryState(state){
  if(!state?.mh4g)return;
  const restoreToken=++historyRestoreToken;
  restoringHistory=true;
  try{
    sourceView=state.sourceView||sourceView;armorViewMode=state.armorViewMode||armorViewMode;decoView=state.decoView||decoView;
    monsterView=state.monsterView||monsterView;dragonView=state.dragonView||dragonView;questView=state.questView||questView;
    recommendWeaponType=state.recommendWeaponType||recommendWeaponType;recommendRank=state.recommendRank||recommendRank;
    if($("#itemSearch"))$("#itemSearch").value=state.itemSearch||"";
    selectedItemId=String(state.selectedItemId||"");
    await openPage(state.page||"simulator");
    if(state.page==="monster"&&$("#monsterSelect")){const wanted=state.monsterSelected||"all";if([...$("#monsterSelect").options].some(o=>o.value===wanted))$("#monsterSelect").value=wanted;renderMonster();}
    requestAnimationFrame(()=>window.scrollTo({top:Number(state.scrollY)||0,behavior:"auto"}));
  }finally{if(restoreToken===historyRestoreToken)restoringHistory=false}
}
async function openItemByName(name){
  await ensureFullData(["items","itemReferenceIndex"]);
  const item=itemByName.get(String(name||"").trim());if(!item)return;
  replaceCurrentHistoryState();
  $("#itemSearch").value=item.name;
  selectedItemId=String(item.id);
  if(currentPage!=="item")await openPage("item"); else renderItemTable();
  await renderItemDetail(item.id,{scroll:true});
  pushCurrentHistoryState();
}
// 인라인 아이템 링크는 document 단일 위임 핸들러에서 처리한다.
function bindInlineItemLinks(){ }

function renderCraft(w){
  const craft=w.craft||[];
  if(!craft.length)return '<span class="muted">-</span>';
  return `<div class="craft-list">${craft.map(c=>`<div class="craft-line"><span class="craft-method">${esc(c.method||"소재")}</span><span class="craft-materials">${materialLinks(c.materials||"-")}</span></div>`).join("")}</div>`;
}
function renderWeaponSubNav(){
  const box=$("#weaponSubNav");if(!box)return;
  const types=WEAPON_TYPES.filter(t=>data.weapons.some(w=>w.weaponType===t));
  const buttons=[];
  for(const t of types){
    buttons.push(`<button type="button" class="weapon-sub-btn" data-weapon-type="${esc(t)}">${esc(t)}</button>`);
    if(t==="수렵피리") buttons.push(`<button type="button" class="weapon-sub-btn sub-special melody-under-horn" data-special-page="melody">┗ 선율표</button>`);
  }
  buttons.push(`<button type="button" class="weapon-sub-btn sub-special weapon-summary-link" data-special-page="weapon-summary">속성별 무기요약</button>`);
  box.innerHTML=buttons.join("");
  box.querySelectorAll('[data-weapon-type]').forEach(b=>b.onclick=e=>{e.stopPropagation();armorViewMode="all";$("#weaponTypeFilter").value=b.dataset.weaponType;syncWeaponSubActive();void navigatePage("weapon")});
  box.querySelectorAll('[data-special-page]').forEach(b=>b.onclick=e=>{e.stopPropagation();void navigatePage(b.dataset.specialPage)});
}
function syncWeaponSubActive(){const t=$("#weaponTypeFilter")?.value||"all";$$('[data-weapon-type]').forEach(b=>b.classList.toggle('active',b.dataset.weaponType===t))}
const WEAPON_ELEMENT_FILTERS={
  fire:"불",water:"물",thunder:"번개",ice:"얼음",dragon:"용",
  poison:"독",paralysis:"마비",sleep:"수면",blast:"폭파"
};
const SHARPNESS_RANK={red:0,orange:1,yellow:2,green:3,blue:4,white:5,purple:6};
function weaponElementCategory(w){
  const props=[w?.elementPrimary,w?.elementSecondary,w?.awakenElement].filter(Boolean);
  const map={"불":"fire","화":"fire","물":"water","번개":"thunder","뇌":"thunder","얼음":"ice","빙":"ice","용":"dragon","독":"poison","마비":"paralysis","수면":"sleep","폭파":"blast"};
  for(const p of props){const key=map[String(p?.type||"")];if(key)return key;}
  const text=String(w?.element||"").replace(/[()]/g," ");
  if(!text.trim())return "none";
  for(const [key,word] of Object.entries(WEAPON_ELEMENT_FILTERS)) if(new RegExp(`${word}\\s*\\d+`).test(text)) return key;
  return "none";
}
function weaponElementValue(w){
  const vals=[w?.elementPrimary,w?.elementSecondary,w?.awakenElement].filter(Boolean).map(p=>Number(p?.value)||0);
  if(vals.length)return Math.max(...vals);
  if(weaponElementCategory(w)==="none")return 0;
  const nums=String(w?.element||"").match(/\d+/g)||[];
  return nums.length?Math.max(...nums.map(Number)):0;
}
function sharpnessKey(w,plus=false){
  const bar=plus?w?.sharpness?.plus:w?.sharpness?.normal;
  if(!bar?.segments?.length)return [-1,0,0];
  let top=-1,topLen=0;
  for(const seg of bar.segments){
    const rank=SHARPNESS_RANK[seg.color]??-1,len=Number(seg.length)||0;
    if(len>0&&rank>=top){top=rank;topLen=len;}
  }
  const total=Number(bar.total)||bar.segments.reduce((sum,x)=>sum+(Number(x.length)||0),0);
  return [top,total?topLen/total:0];
}
function compareTupleDesc(a,b){for(let i=0;i<Math.max(a.length,b.length);i++){const d=(b[i]||0)-(a[i]||0);if(d)return d}return 0}
function weaponComparator(mode){
  return (a,b)=>{
    let d=0;
    if(mode==="attack-desc")d=(Number(b.attack)||0)-(Number(a.attack)||0);
    else if(mode==="attack-asc")d=(Number(a.attack)||0)-(Number(b.attack)||0);
    else if(mode==="sharpness-desc")d=compareTupleDesc(sharpnessKey(a,false),sharpnessKey(b,false));
    else if(mode==="sharpness-plus-desc")d=compareTupleDesc(sharpnessKey(a,true),sharpnessKey(b,true));
    else if(mode==="element-desc")d=weaponElementValue(b)-weaponElementValue(a);
    else if(mode==="affinity-desc")d=(Number(b.affinity)||0)-(Number(a.affinity)||0);
    else if(mode==="slots-desc")d=(Number(b.slots)||0)-(Number(a.slots)||0);
    else if(mode==="name")d=String(a.name||"").localeCompare(String(b.name||""),"ko");
    else d=(a.rowOrder??0)-(b.rowOrder??0);
    return d||String(a.name||"").localeCompare(String(b.name||""),"ko");
  };
}
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
    return `${prefix}${w.isFinal?'<span class="final-mark">■</span> ':''}<strong>${esc(w.name)}</strong>${localizedNameSub(w)}${plannerIconButton("weapon",w.id,{craft:true,label:`${w.name} 즐겨찾기/제작`})}`;
  }
  if(col.key==="attack") return w.attack??"-";
  if(col.key==="element") return esc(weaponPropertyBits(w).join(" · ")||"-");
  if(col.key==="affinity") return weaponAffinityText(w);
  if(col.key==="slots") return slotsText(w.slots);
  if(col.key==="sharpness") return renderSharpness(w);
  if(col.key==="rank") return rankName(w.rank);
  if(col.key==="craft") return renderCraft(w);
  const f=weaponFeatureColumns(w.weaponType).find(x=>x.key===col.key);
  return f?f.render(w):"-";
}
function weaponRow(w,cols){
  return `<tr class="weapon-db-row" data-weapon-row="${esc(w.id)}" tabindex="0" aria-expanded="false">${cols.map(col=>`<td class="${col.key==="name"?"weapon-name-cell ":""}${col.key==="slots"?"slots ":""}${col.key==="sharpness"?"sharpness-cell ":""}${esc(col.className||"")}">${weaponCell(w,col)}</td>`).join("")}</tr>`;
}
function weaponTreeMeta(id){return weaponTreeIndex?.items?.[String(id)]||{};}
function weaponNavButton(id,label){const w=weaponById.get(String(id));return w?`<button type="button" class="xref-link weapon-tree-nav" data-open-weapon="${esc(id)}">${esc(label||w.name)}</button>`:"-";}
function weaponMaterialSummary(list=[]){return list.length?`<div class="weapon-total-materials">${list.map(x=>`<span>${itemLink(x.name)} <b>×${Number(x.count)||0}</b></span>`).join("")}</div>`:'<span class="muted">집계 가능한 소재 없음</span>';}
function buildWeaponTreeDetail(w,ref){
  const meta=weaponTreeMeta(w.id),path=(ref.pathIds||[]).map(String).filter(id=>weaponById.has(id)),children=(meta.childIds||[]).map(String).filter(id=>weaponById.has(id)),finals=(ref.finalIds||[]).map(String).filter(id=>weaponById.has(id));
  const parent=meta.parentId&&weaponById.has(String(meta.parentId))?String(meta.parentId):null;
  const route=path.map((id,i)=>`${i?'<span class="weapon-route-arrow">→</span>':''}${weaponNavButton(id)}`).join('');
  const next=children.length?`<div class="weapon-nav-list">${children.map(id=>weaponNavButton(id)).join('')}</div>`:'<span class="muted">최종 단계</span>';
  const finalList=finals.length?`<div class="weapon-nav-list">${finals.map(id=>weaponNavButton(id)).join('')}</div>`:'<span class="muted">-</span>';
  const direct=(w.craft||[]).filter(c=>c.method==='생산');
  return `<div class="weapon-tree-detail"><div class="weapon-detail-grid"><section><h4>강화 경로</h4><div class="weapon-route">${route||weaponNavButton(w.id)}</div></section><section><h4>이전 강화</h4><div>${parent?weaponNavButton(parent):'<span class="muted">트리 시작</span>'}</div></section><section><h4>다음 강화</h4><div>${next}</div></section><section><h4>최종 강화</h4><div>${finalList}</div></section></div>${direct.length?`<div class="weapon-direct-create"><b>직접 생산</b> ${direct.map(c=>materialLinks(c.materials||'')).join(' / ')}</div>`:''}<details class="weapon-material-total" open><summary>현재 무기까지 누적 필요 소재 <b>${(ref.cumulativeMaterials||[]).length}종</b></summary>${weaponMaterialSummary(ref.cumulativeMaterials||[])}</details><div class="weapon-tree-source-note">트리 관계: ${esc(meta.match||'local')} · MH4U parent_id 기준${meta.mh4uId?` · #${meta.mh4uId}`:''}</div></div>`;
}
let openWeaponRow=null,openWeaponDetailRow=null;
function closeWeaponDetail(){if(openWeaponRow){openWeaponRow.classList.remove('is-open');openWeaponRow.setAttribute('aria-expanded','false');}openWeaponDetailRow?.remove();openWeaponRow=null;openWeaponDetailRow=null;}
async function openWeaponDetail(row){
  if(!row)return;const id=String(row.dataset.weaponRow||''),w=weaponById.get(id);if(!w)return;
  if(openWeaponRow===row){closeWeaponDetail();return;}closeWeaponDetail();
  const tr=document.createElement('tr');tr.className='weapon-detail-row';const td=document.createElement('td');td.colSpan=row.children.length;td.innerHTML='<div class="weapon-tree-detail"><span class="muted">트리 정보를 불러오는 중…</span></div>';tr.appendChild(td);row.after(tr);
  row.classList.add('is-open');row.setAttribute('aria-expanded','true');openWeaponRow=row;openWeaponDetailRow=tr;
  await ensureWeaponTreeIndex();const ref=await loadWeaponReferenceLocal(id);if(openWeaponRow!==row||!tr.isConnected)return;td.innerHTML=buildWeaponTreeDetail(w,ref);
}
async function navigateWeapon(id){
  const w=weaponById.get(String(id||''));if(!w)return;if(currentPage!=="weapon")await openPage("weapon");await ensureWeaponTreeIndex();
  if($("#weaponTypeFilter"))$("#weaponTypeFilter").value=w.weaponType;renderWeaponTreeFilter();if($("#weaponTreeFilter"))$("#weaponTreeFilter").value=w.tree||"all";if($("#weaponElementFilter"))$("#weaponElementFilter").value="all";if($("#weaponSort"))$("#weaponSort").value="tree";if($("#weaponSearch"))$("#weaponSearch").value="";renderWeaponTrees();
  const row=[...document.querySelectorAll('[data-weapon-row]')].find(x=>String(x.dataset.weaponRow)===String(w.id));if(row){await openWeaponDetail(row);row.scrollIntoView({block:'center',behavior:'auto'});}
}
function renderWeaponTrees(){
  closeWeaponDetail();
  const q=$("#weaponSearch").value.trim().toLowerCase(),tree=$("#weaponTreeFilter").value;
  const element=$("#weaponElementFilter")?.value||"all",sortMode=$("#weaponSort")?.value||"tree";
  const cmp=weaponComparator(sortMode);
  let rows=weaponFilteredBase().filter(w=>(tree==="all"||w.tree===tree)&&(element==="all"||weaponElementCategory(w)===element)&&(!q||`${w.name} ${w.nameJa||""} ${w.nameEn||""} ${w.element||""} ${weaponPropertyBits(w).join(" ")} ${w.tree||""} ${weaponExtra(w)} ${(w.craft||[]).map(c=>c.materials).join(" ")}`.toLowerCase().includes(q)));
  const groups=new Map();for(const w of rows){const k=w.tree||"기타";if(!groups.has(k))groups.set(k,[]);groups.get(k).push(w)}
  for(const list of groups.values())list.sort(cmp);
  const ordered=[...groups.entries()].sort((a,b)=>sortMode==="tree"?((a[1][0]?.treeOrder??9999)-(b[1][0]?.treeOrder??9999)||a[0].localeCompare(b[0],"ko")):(cmp(a[1][0],b[1][0])||a[0].localeCompare(b[0],"ko")));
  const elementLabel=$("#weaponElementFilter")?.selectedOptions?.[0]?.textContent||"전체 속성";
  const sortLabel=$("#weaponSort")?.selectedOptions?.[0]?.textContent||"파생 순서";
  $("#weaponResultInfo").textContent=`${rows.length.toLocaleString()}개 무기 · ${ordered.length.toLocaleString()}개 파생 · ${elementLabel} · ${sortLabel}`;
  $("#weaponTrees").innerHTML=ordered.length?ordered.map(([name,list],i)=>{
    const sorted=list;
    const type=sorted[0]?.weaponType||"";
    const cols=weaponTableColumns(type);
    return `<details class="weapon-tree-group" ${(q||tree!=="all"||element!=="all"||sortMode!=="tree"||i===0)?"open":""}><summary><span>${esc(name)}</span><span class="tree-meta">${esc(type)} · ${list.length}개</span></summary><div class="weapon-tree-table-wrap"><table class="data-table weapon-data-table ${RANGED_TYPES.has(type)?"ranged-table":"melee-table"}"><thead><tr>${cols.map(c=>`<th class="${esc(c.className||"")}">${esc(c.label)}</th>`).join("")}</tr></thead><tbody>${sorted.map(w=>weaponRow(w,cols)).join("")}</tbody></table></div></details>`;
  }).join(""):'<div class="panel result-empty">검색 결과 없음</div>';
  decorateResponsiveTables($("#weaponTrees"));
  bindInlineItemLinks($("#weaponTrees"));
  syncWeaponSubActive();
}

function skillReferenceMeta(skillId){return data.skillReferenceIndex?.items?.[String(skillId)]||{};}
async function getSkillReference(skillId){
  const key=String(skillId||"");
  if(skillReferenceCache.has(key))return skillReferenceCache.get(key);
  const meta=skillReferenceMeta(key),file=meta.file||`${key}.json`;
  const promise=loadSkillReference(file).catch(()=>({decorations:[],armors:[]}));
  skillReferenceCache.set(key,promise);return promise;
}
function skillLink(skillId,label){return `<button type="button" class="xref-link skill-inline-link" data-open-skill="${esc(skillId)}">${esc(label||skillName(skillId))}</button>`;}
function decoLink(name){return `<button type="button" class="xref-link" data-open-deco="${esc(name)}">${esc(name)}</button>`;}
function decorationSkillHtml(d){return Object.entries(d.skills||{}).map(([k,v])=>`${skillLink(k,skillName(k))} <b>${v>0?"+":""}${v}</b>`).join(", ");}
function armorSourceLabel(a){return `${PART_NAMES[a.part]||a.part||""} · ${rankName(a.rank)} · RARE ${a.rare||"-"} · ${a.points>0?"+":""}${a.points}`;}
function groupSkillArmorsBySet(armors=[]){
  const groups=new Map();
  for(const a of armors){
    const set=armorSetByPieceId.get(a.id);
    const key=set?.id||`solo:${a.id}`;
    if(!groups.has(key))groups.set(key,{id:key,name:set?.name||a.name,hunterType:set?.hunterType||a.hunterType,rank:set?.rank||a.rank,rare:set?.rare||a.rare,pieces:[]});
    groups.get(key).pieces.push(a);
  }
  return [...groups.values()].sort((a,b)=>rankOrder(a.rank)-rankOrder(b.rank)||Number(a.rare||0)-Number(b.rare||0)||a.name.localeCompare(b.name,"ko"));
}
function rankOrder(r){return ({low:0,high:1,g:2})[r]??9;}
function buildSkillSourceHtml(s,ref){
  const meta=skillReferenceMeta(s.id),decos=ref.decorations||[],armors=ref.armors||[],components=meta.components||[];
  const composite=meta.composite&&components.length?`<div class="skill-composite-box"><b>복합 효과</b><span>${components.map(esc).join(" + ")}</span></div>`:"";
  const decoBlock=decos.length?`<details class="skill-source-group"><summary>장식주로 확보 <b>${decos.length}종</b></summary><div class="skill-source-list">${decos.map(d=>`<div class="skill-source-row"><div>${decoLink(d.name)} <span class="slots">${d.slots}슬롯</span> <b>+${d.points}</b></div><small>${rankName(d.rank)} · ${materialLinks(d.materials||"")}</small></div>`).join("")}</div></details>`:"";
  const armorGroups=groupSkillArmorsBySet(armors);
  const armorBlock=armorGroups.length?`<details class="skill-source-group"><summary>방어구로 확보 <b>${armorGroups.length}세트 · ${armors.length}부위</b></summary><div class="skill-armor-set-list">${armorGroups.map(g=>`<details class="skill-armor-set"><summary><span>${esc(g.name)}</span><small>${hunterName(g.hunterType)} · ${rankName(g.rank)} · RARE ${g.rare||"-"} · ${g.pieces.length}부위</small></summary><div class="skill-source-list skill-armor-source-list">${g.pieces.sort((a,b)=>PARTS.indexOf(a.part)-PARTS.indexOf(b.part)).map(a=>`<div class="skill-source-row"><div><button type="button" class="xref-link" data-item-nav="armor" data-nav-name="${esc(a.name)}">${esc(a.name)}</button> <b>${a.points>0?"+":""}${a.points}</b></div><small>${esc(armorSourceLabel(a))}${a.materials?` · 제작: ${materialLinks(a.materials)}`:""}</small></div>`).join("")}</div></details>`).join("")}</div></details>`:"";
  return `${composite}${decoBlock}${armorBlock}`;
}
async function openSkillDetail(skillId,row){
  const table=row?.closest("table"); if(!table)return;
  const current=table.querySelector("tr.skill-db-row.is-open");
  const currentDetail=table.querySelector("tr.skill-detail-row:not([hidden])");
  if(current&&current!==row){current.classList.remove("is-open","ui-selected-row");current.setAttribute("aria-expanded","false");}
  if(currentDetail&&currentDetail.previousElementSibling!==row)currentDetail.hidden=true;
  const detail=row.nextElementSibling;
  if(!detail?.classList.contains("skill-detail-row"))return;
  const willOpen=!row.classList.contains("is-open");
  if(!willOpen){row.classList.remove("is-open","ui-selected-row");row.setAttribute("aria-expanded","false");detail.hidden=true;return;}
  selectUiRow(row);
  row.classList.add("is-open");row.setAttribute("aria-expanded","true");detail.hidden=false;
  const body=detail.querySelector(".skill-source-body");
  if(detail.dataset.loaded==="1")return;
  body.innerHTML='<p class="muted">연결 데이터 불러오는 중…</p>';
  const skill=skillById.get(skillId); if(!skill)return;
  const ref=await getSkillReference(skillId);
  if(!detail.isConnected||detail.hidden)return;
  body.innerHTML=buildSkillSourceHtml(skill,ref);detail.dataset.loaded="1";bindInlineItemLinks(body);
}

function decorationCategories(d){
  const cats=new Set();
  for(const [skillId,points] of Object.entries(d.skills||{})){
    if(Number(points)<=0)continue;
    const cat=skillReferenceMeta(skillId).category;
    if(cat)cats.add(cat);
  }
  return cats;
}

function decorationUnlockRouteHtml(d){
  const ref=data.decorationUnlocks?.decorations?.[d.id];
  if(!ref)return '<span class="muted">확인된 해금 정보 없음</span>';
  const mats=ref.materials||[];
  const explicit=mats.flatMap(m=>(m.unlocks||[]).map(u=>({material:m.name,unlock:u})));
  const keyMaterial=mats.find(m=>!/원주$/.test(m.name||"")&&(m.quests||[]).length)||mats.find(m=>(m.quests||[]).length);
  const bits=[];
  if(explicit.length){const x=explicit[0];bits.push(`<div><b>해금 연계</b> ${itemLink(x.material)} · ${esc(x.unlock)}</div>`)}
  if(keyMaterial){const q=keyMaterial.quests[0];bits.push(`<div><b>소재 경로</b> ${itemLink(keyMaterial.name)} → ${refButton(`${q.level||""} ${q.name||"퀘스트"}`.trim(),"quest",{name:q.name,questtype:q.questType})}</div>`)}
  if(!bits.length)return '<span class="muted">생산 소재 확인 · 별도 퀘스트 해금은 확인되지 않음</span>';
  return bits.join("");
}
function renderDecoTable(){
  const q=$("#decoSearch").value.trim().toLowerCase();
  const rank=$("#decoRankFilter")?.value||"all",slot=$("#decoSlotFilter")?.value||"all",cat=$("#decoCategoryFilter")?.value||"all";
  const list=data.decorations.filter(d=>{
    if(rank!=="all"&&d.rank!==rank)return false;
    if(slot!=="all"&&Number(d.slots)!==Number(slot))return false;
    if(cat!=="all"&&!decorationCategories(d).has(cat))return false;
    return !q||decorationSearchCorpus(d).toLowerCase().includes(q);
  });
  list.sort((a,b)=>decoView==="slot"?(a.slots-b.slots||a.name.localeCompare(b.name,"ko")):(Object.keys(a.skills||{}).map(skillName).join("").localeCompare(Object.keys(b.skills||{}).map(skillName).join(""),"ko")||a.name.localeCompare(b.name,"ko")));
  const rows=list.map(d=>`<tr><td><strong>${esc(d.name)}</strong>${localizedNameSub(d)}</td><td>${d.slots}</td><td>${decorationSkillHtml(d)}</td><td>${rankName(d.rank)}</td><td class="wrap-cell">${materialLinks(d.materials||"")}</td><td class="wrap-cell deco-unlock-route">${decorationUnlockRouteHtml(d)}</td></tr>`);
  renderTable("#decoTable",["장식주","필요 슬롯","스킬 포인트","등급","생산 소재","해금/소재 경로"],rows);
  const info=$("#decoResultInfo");if(info)info.textContent=`${list.length} / ${data.decorations.length}개 장식주`;
}
function renderSkillTable(){
  const q=$("#skillSearch").value.trim().toLowerCase(),cat=$("#skillCategoryFilter")?.value||"all",type=$("#skillTypeFilter")?.value||"all";
  const list=data.skills.filter(s=>{const m=skillReferenceMeta(s.id);if(q&&!skillSearchCorpus(s).toLowerCase().includes(q))return false;if(cat!=="all"&&m.category!==cat)return false;if(type==="composite"&&!m.composite)return false;if(type==="normal"&&m.composite)return false;if(type==="no-deco"&&m.hasDecoration)return false;if(type==="with-deco"&&!m.hasDecoration)return false;return true;});
  const root=$("#skillTable");
  const rows=list.map(s=>{const m=skillReferenceMeta(s.id);const main=`<tr class="skill-db-row" data-skill-row="${esc(s.id)}" tabindex="0" aria-expanded="false"><td><strong>${esc(s.name)}</strong>${localizedNameSub(s)}<div class="skill-badges"><span class="skill-category-badge">${esc(m.category||"미분류")}</span>${m.composite?'<span class="skill-composite-badge">복합</span>':""}</div></td><td>${(s.activations||[]).map(a=>`${a.points>0?"+":""}${a.points} → <strong>${esc(a.name)}</strong>${localizedNameSub(a)}`).join("<br>")}</td><td>${(s.activations||[]).map(a=>a.description?`<div><strong>${esc(a.name)}</strong>: ${esc(cleanEffectText(a.description))}</div>`:"").filter(Boolean).join("")}</td></tr>`;const detail=`<tr class="skill-detail-row" data-skill-detail="${esc(s.id)}" hidden><td colspan="3"><div class="skill-source-body"></div></td></tr>`;return main+detail;}).join("");
  root.innerHTML=`<table class="data-table skill-db-table"><colgroup><col class="skill-col-tree"><col class="skill-col-activation"><col class="skill-col-effect"></colgroup><thead><tr><th>스킬 계통</th><th>발동 조건</th><th>효과 및 비고</th></tr></thead><tbody>${rows||'<tr><td colspan="3" class="result-empty">검색 결과 없음</td></tr>'}</tbody></table>`;
  decorateResponsiveTables(root);bindInlineItemLinks(root);const info=$("#skillResultInfo");if(info)info.textContent=`${list.length} / ${data.skills.length}개 스킬 · 분야는 탐색용 편의 분류`;
}

function itemReferenceCount(item){
  const row=data.itemReferenceIndex?.items?.[item?.id]||data.itemReferenceIndex?.items?.[String(item?.id)]||{};
  return {acquire:Number(row.acquire)||0,uses:Number(row.uses)||0};
}
function rebuildItemReferenceIndexes(){
  // 검색은 아이템 기본 필드만 사용한다. 1.8MB 역참조 전체를 검색용 문자열로 재조합하지 않는다.
  itemSearchCorpusById=new Map();
  itemDetailHtmlCache.clear();
  for(const item of data.items||[]){
    const corpus=`${item.name||""} ${(item.aliases||[]).join(" ")} ${item.nameJa||""} ${item.nameEn||""} ${item.acquire||""} ${item.note||""}`.toLowerCase();
    itemSearchCorpusById.set(String(item.id),corpus);
  }
}
function itemReferenceCorpus(item){
  const key=String(item?.id??"");
  return itemSearchCorpusById.get(key)||`${item?.name||""} ${(item?.aliases||[]).join(" ")} ${item?.nameJa||""} ${item?.nameEn||""} ${item?.acquire||""} ${item?.note||""}`.toLowerCase();
}
async function getItemReference(itemId){
  const key=String(itemId||"");
  if(itemReferenceCache.has(key)) return itemReferenceCache.get(key);
  const promise=loadItemReference(key).then(ref=>({acquire:ref?.acquire||[],uses:ref?.uses||[]})).catch(()=>({acquire:[],uses:[]}));
  itemReferenceCache.set(key,promise);
  return promise;
}
function refButton(label,type,attrs={}){
  const dataAttrs=Object.entries(attrs).filter(([,v])=>v!==undefined&&v!==null&&String(v)!=="").map(([k,v])=>` data-nav-${k}="${esc(String(v))}"`).join("");
  return `<button type="button" class="xref-link" data-item-nav="${esc(type)}"${dataAttrs}>${esc(label)}</button>`;
}
function acquireRefHtml(x,itemName){
  if(x.type==="monster")return `<li>${refButton(x.monster||"몬스터","monster",{monster:x.monster,item:itemName})}<span>${esc([x.method,x.count,x.rank?rankName(x.rank):"",x.probability].filter(Boolean).join(" · "))}</span></li>`;
  if(x.type==="quest")return `<li>${refButton(`${x.level||""} ${x.name||"퀘스트"}`.trim(),"quest",{name:x.name,questtype:x.questType})}<span>${esc([x.location,x.objective].filter(Boolean).join(" · "))}</span></li>`;
  if(x.type==="compose")return `<li>${refButton(`조합 No.${x.no}: ${x.materialA} + ${x.materialB}`,"compose",{name:itemName})}<span>${esc([x.successRate,x.yield?`생산 ${x.yield}`:""].filter(Boolean).join(" · "))}</span></li>`;
  if(x.type==="exchange")return `<li>${refButton(`용인 교환: ${x.required} → ${itemName}`,"dragon",{view:"exchange",name:itemName})}<span>${esc(x.unlock||"")}</span></li>`;
  if(x.type==="dragonSell")return `<li>${refButton(`용인 판매: ${x.line||"목록"}`,"dragon",{view:"sell",name:itemName})}<span>${esc(x.points?`${x.points} 여단P`:"")}</span></li>`;
  if(x.type==="dragonIncrease")return `<li>${refButton(`용인 증식: ${x.market||"시장"}`,"dragon",{view:"increase",name:itemName})}<span>${esc([x.successRate,x.points?`${x.points} 여단P`:""].filter(Boolean).join(" · "))}</span></li>`;
  return `<li><span>${esc(x.type||"입수처")}</span></li>`;
}
function useRefHtml(x){
  if(x.type==="externalUse")return `<li><a class="xref-link" href="${esc(x.url||"#")}" target="_blank" rel="noopener noreferrer">${esc(x.name||"외부 사용처")}</a><span>${esc([x.category,x.count?`×${x.count}`:"",x.note||""].filter(Boolean).join(" · "))}</span></li>`;
  if(x.type==="weapon")return `<li>${refButton(`${x.weaponType||"무기"} · ${x.name}`,"weapon",{name:x.name,weapontype:x.weaponType})}<span>${esc([x.method,x.count?`×${x.count}`:""].filter(Boolean).join(" · "))}</span></li>`;
  if(x.type==="armor")return `<li>${refButton(x.name||"방어구","armor",{name:x.name})}<span>${esc([PART_NAMES[x.part]||x.part,x.hunterType?hunterName(x.hunterType):"",x.count?`×${x.count}`:""].filter(Boolean).join(" · "))}</span></li>`;
  if(x.type==="decoration")return `<li>${refButton(x.name||"장식주","decoration",{name:x.name})}<span>${esc([x.slots?`${x.slots}슬롯`:"",x.count?`×${x.count}`:""].filter(Boolean).join(" · "))}</span></li>`;
  if(x.type==="compose")return `<li>${refButton(`조합 재료 → ${x.result}`,"compose",{name:x.result})}<span>${esc(x.successRate||"")}</span></li>`;
  if(x.type==="exchange")return `<li>${refButton(`용인 교환 재료 → ${x.result}`,"dragon",{view:"exchange",name:x.result})}<span>${esc(x.unlock||"")}</span></li>`;
  return `<li><span>${esc(x.type||"사용처")}</span></li>`;
}
function selectedItemName(){return itemById.get(String(selectedItemId))?.name||""}
function xrefLazyGroup(title,kind,count){
  if(!count)return "";
  return `<details class="xref-group xref-lazy" data-xref-kind="${esc(kind)}"><summary><strong>${esc(title)}</strong><span>${count.toLocaleString()}건</span></summary><div class="xref-lazy-body"><p class="muted xref-lazy-hint">펼치면 상세 목록을 표시합니다.</p></div></details>`;
}
function buildItemDetailHtml(item,ref){
  const acq=ref?.acquire||[],uses=ref?.uses||[];
  const count=t=>acq.reduce((n,x)=>n+(t(x)?1:0),0);
  const useCount=t=>uses.reduce((n,x)=>n+(t(x)?1:0),0);
  const acqGroups=[
    ["퀘스트 보수","acq-quest",count(x=>x.type==="quest")],
    ["몬스터 갈무리/보수","acq-monster",count(x=>x.type==="monster")],
    ["조합","acq-compose",count(x=>x.type==="compose")],
    ["용인족 도매상","acq-dragon",count(x=>["exchange","dragonSell","dragonIncrease"].includes(x.type))]
  ].filter(([, ,n])=>n);
  const useGroups=[
    ["무기 생산/강화","use-weapon",useCount(x=>x.type==="weapon")],
    ["방어구 생산","use-armor",useCount(x=>x.type==="armor")],
    ["장식주 생산","use-decoration",useCount(x=>x.type==="decoration")],
    ["조합 재료","use-compose",useCount(x=>x.type==="compose")],
    ["용인 교환 재료","use-exchange",useCount(x=>x.type==="exchange")],
    ["오토모·기타 장비","use-external",useCount(x=>x.type==="externalUse")]
  ].filter(([, ,n])=>n);
  return `<section class="panel item-detail-card"><div class="item-detail-head"><div><span class="item-detail-kicker">아이템 상세 · 역참조</span><h2>${esc(item.name)}</h2>${localizedNameSub(item)}</div><button type="button" class="item-detail-close" aria-label="상세 닫기">×</button></div><div class="item-detail-meta"><span>RARE <strong>${item.rare||"-"}</strong></span><span>소지 <strong>${item.maxStack||"-"}</strong></span><span>구매 <strong>${esc(item.buyPrice||"-")}</strong></span><span>판매 <strong>${esc(item.sellPrice||"-")}</strong></span><span>입수 연결 <strong>${acq.length.toLocaleString()}</strong></span><span>사용 연결 <strong>${uses.length.toLocaleString()}</strong></span></div>${item.acquire||item.note?`<div class="item-detail-note">${item.acquire?`<p><b>기본 입수</b> ${esc(item.acquire)}</p>`:""}${item.note?`<p><b>효과/비고</b> ${esc(item.note)}</p>`:""}</div>`:""}<div class="item-xref-columns"><div><h3>어디서 얻나</h3>${acqGroups.length?acqGroups.map(([t,k,n])=>xrefLazyGroup(t,k,n)).join(""):'<p class="muted xref-empty">현재 구조화 데이터에서 확인되는 입수처가 없습니다.</p>'}</div><div><h3>어디에 쓰나</h3>${useGroups.length?useGroups.map(([t,k,n])=>xrefLazyGroup(t,k,n)).join(""):'<p class="muted xref-empty">현재 구조화 데이터에서 확인되는 사용처가 없습니다.</p>'}</div></div><p class="xref-footnote">※ 역참조는 현재 프로젝트의 퀘스트·몬스터 보수·조합·용인족 도매상·무기·방어구·장식주 데이터를 연결해 표시합니다.</p></section>`;
}
function xrefItemsForKind(ref,kind){
  const acq=ref?.acquire||[],uses=ref?.uses||[];
  if(kind==="acq-quest")return [acq.filter(x=>x.type==="quest"),"acquire"];
  if(kind==="acq-monster")return [acq.filter(x=>x.type==="monster"),"acquire"];
  if(kind==="acq-compose")return [acq.filter(x=>x.type==="compose"),"acquire"];
  if(kind==="acq-dragon")return [acq.filter(x=>["exchange","dragonSell","dragonIncrease"].includes(x.type)),"acquire"];
  if(kind==="use-weapon")return [uses.filter(x=>x.type==="weapon"),"use"];
  if(kind==="use-armor")return [uses.filter(x=>x.type==="armor"),"use"];
  if(kind==="use-decoration")return [uses.filter(x=>x.type==="decoration"),"use"];
  if(kind==="use-compose")return [uses.filter(x=>x.type==="compose"),"use"];
  if(kind==="use-exchange")return [uses.filter(x=>x.type==="exchange"),"use"];
  if(kind==="use-external")return [uses.filter(x=>x.type==="externalUse"),"use"];
  return [[],"use"];
}
async function hydrateXrefGroup(details){
  if(!details?.open||details.dataset.loaded==="1")return;
  const item=itemById.get(String(selectedItemId));if(!item)return;
  const ref=await getItemReference(item.id);
  if(!details.isConnected||!details.open)return;
  const [items,kind]=xrefItemsForKind(ref,details.dataset.xrefKind||"");
  const body=details.querySelector(".xref-lazy-body");if(!body)return;
  const renderer=kind==="acquire"?(x=>acquireRefHtml(x,item.name)):useRefHtml;
  body.innerHTML=`<ul>${items.map(renderer).join("")}</ul>`;
  details.dataset.loaded="1";
}
function removeItemDetailRow(){
  document.querySelector("#itemTable .item-detail-inline")?.remove();
  document.querySelector("#itemTable .item-list-row.item-row-selected")?.classList.remove("item-row-selected");
}
async function renderItemDetail(id,{scroll=false}={}){
  const key=String(id),item=itemById.get(key);if(!item){removeItemDetailRow();selectedItemId="";return false}
  const row=document.querySelector(`#itemTable .item-list-row[data-item-row="${CSS.escape(key)}"]`);if(!row)return false;
  removeItemDetailRow();selectedItemId=key;row.classList.add("item-row-selected");
  const detail=document.createElement("div");detail.className="item-detail-inline";detail.dataset.itemDetailFor=key;
  detail.innerHTML='<div class="item-detail-loading">역참조 불러오는 중…</div>';
  row.insertAdjacentElement("afterend",detail);
  // 레이아웃 변경을 먼저 화면에 반영한 뒤 작은 개별 JSON만 읽는다.
  await new Promise(resolve=>requestAnimationFrame(resolve));
  const ref=await getItemReference(key);
  if(selectedItemId!==key||!detail.isConnected)return false;
  let html=itemDetailHtmlCache.get(key);
  if(!html){html=buildItemDetailHtml(item,ref);itemDetailHtmlCache.set(key,html);}
  detail.innerHTML=html;
  if(scroll){const r=row.getBoundingClientRect();if(r.top<70||r.bottom>window.innerHeight)row.scrollIntoView({behavior:"auto",block:"nearest"});}
  return true;
}
async function followItemReference(btn){
  const type=btn.dataset.itemNav,name=btn.dataset.navName||"";
  if(type==="weapon"){
    await openPage("weapon"); $("#weaponTypeFilter").value=btn.dataset.navWeapontype||"all"; $("#weaponSearch").value=name; renderWeaponTreeFilter();renderWeaponTrees();
  }else if(type==="armor"){
    await openPage("armor"); $("#hunterType").value="both";$("#rankFilter").value="all";$("#armorPartFilter").value="all";$("#armorSearch").value=name;renderArmorTable();
  }else if(type==="decoration"){
    await openPage("decoration");
    $("#decoRankFilter").value="all";$("#decoSlotFilter").value="all";$("#decoCategoryFilter").value="all";
    $("#decoSearch").value=name;renderDecoTable();
  }else if(type==="compose"){
    await openPage("compose");$("#composeSearch").value=name;renderCompose();
  }else if(type==="dragon"){
    dragonView=btn.dataset.navView||"exchange";await openPage("dragon");$("#dragonSearch").value=name;renderDragon();
  }else if(type==="monster"){
    monsterView="rewards";await openPage("monster");const mon=canonicalMonsterName(btn.dataset.navMonster||"");if([...$("#monsterSelect").options].some(o=>o.value===mon))$("#monsterSelect").value=mon;$("#monsterSearch").value="";$("#monsterRankFilter").value="all";renderMonster();
  }else if(type==="questfilter"){
    const qt=btn.dataset.navQuesttype||"",level=btn.dataset.navLevel||"",reward=btn.dataset.navReward||"",monster=btn.dataset.navMonster||"",source=btn.dataset.navSource||"";
    questView=qt==="event"?"event-all":qt==="challenge"?"challenge":qt==="village"?"village-detail":qt==="hub"?"hub-detail":qt==="g"?"g-detail":"key";
    await openPage("quest");
    if($("#questTypeFilter"))$("#questTypeFilter").value=qt||"all";
    populateQuestLevels();
    if($("#questLevelFilter"))$("#questLevelFilter").value=[...$("#questLevelFilter").options].some(o=>o.value===level)?level:"all";
    if($("#questKeyOnly"))$("#questKeyOnly").checked=false;
    if($("#questLocationFilter"))$("#questLocationFilter").value="all";
    if($("#questMonsterFilter")){const mon=$("#questMonsterFilter");mon.value=[...mon.options].some(o=>o.value===monster)?monster:"all";}
    const exactSource=source&&data.quests.some(q=>q.name===source||q.nameEn===source||q.nameJa===source||(q.aliases||[]).includes(source));
    if($("#questSearch"))$("#questSearch").value=exactSource?source:"";
    const rewardMatch=reward&&data.quests.some(q=>(!qt||q.questType===qt)&&(!level||q.level===level)&&(questRef(q).rewardItems||[]).includes(reward));
    if($("#questRewardFilter"))$("#questRewardFilter").value=rewardMatch?reward:"";
    renderQuest();
  }else if(type==="quest"){
    const qt=btn.dataset.navQuesttype||"";questView=qt==="event"?"event-all":qt==="challenge"?"challenge":qt==="village"?"village-detail":qt==="hub"?"hub-detail":qt==="g"?"g-detail":"key";await openPage("quest");$("#questSearch").value=name;$("#questLevelFilter").value="all";$("#questKeyOnly").checked=false;if($("#questTypeFilter"))$("#questTypeFilter").value="all";if($("#questLocationFilter"))$("#questLocationFilter").value="all";if($("#questMonsterFilter"))$("#questMonsterFilter").value="all";if($("#questRewardFilter"))$("#questRewardFilter").value="";renderQuest();
  }
}
function renderItemTable(){
  const q=$("#itemSearch").value.trim().toLowerCase();
  const list=data.items.filter(i=>!q||itemReferenceCorpus(i).includes(q));
  const rows=list.map(i=>{
    const c=itemReferenceCount(i),count=c.acquire+c.uses;
    return `<div class="item-list-row" data-item-row="${esc(i.id)}"><div class="item-cell item-cell-name" data-label="아이템"><button type="button" class="item-name-link" data-item-id="${esc(i.id)}"><strong>${esc(i.name)}</strong>${localizedNameSub(i)}</button></div><div class="item-cell" data-label="RARE">${i.rare||"-"}</div><div class="item-cell" data-label="소지수">${i.maxStack||"-"}</div><div class="item-cell" data-label="구매">${esc(i.buyPrice||"-")}</div><div class="item-cell" data-label="판매">${esc(i.sellPrice||"-")}</div><div class="item-cell item-cell-wide" data-label="입수">${esc(i.acquire||"")}</div><div class="item-cell item-cell-wide" data-label="효과/비고">${esc(i.note||"")}${count?`<small class="xref-count">연결 ${count.toLocaleString()}건</small>`:""}</div></div>`;
  }).join("");
  $("#itemTable").innerHTML=`<div class="item-list"><div class="item-list-head"><span>아이템</span><span>RARE</span><span>소지수</span><span>구매</span><span>판매</span><span>입수</span><span>효과/비고</span></div>${rows||'<div class="item-list-empty">검색 결과 없음</div>'}</div>`;
  if(selectedItemId)void renderItemDetail(selectedItemId);
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
  const rows=data.armorSets.filter(armorSetEligible).filter(s=>{const mats=armorSetMaterials(s);return !q||`${s.name} ${(s.pieces||[]).map(p=>p.name).join(" ")} ${Object.keys(s.skills||{}).map(skillName).join(" ")} ${mats}`.toLowerCase().includes(q)})
    .map(s=>{const mats=armorSetMaterials(s);return `<tr><td><strong>${esc(s.name)}</strong><small>${(s.pieces||[]).map(p=>`${PART_NAMES[p.part]||p.part}:${p.name}`).map(esc).join(" · ")}</small></td><td>${hunterName(s.hunterType)}</td><td>${rankName(s.rank)}</td><td>${s.rare||"-"}</td><td>${s.defense||0} / ${s.maxDefense||s.defense||0}</td><td>${s.slots||0}</td><td>${Object.entries(s.skills||{}).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${skillLink(k,skillName(k))} ${v>0?"+":""}${v}`).join(", ")}</td><td>${resistText(s.resistances)}</td><td class="wrap-cell">${materialLinks(mats)}</td></tr>`});
  renderTable("#armorSetTable",["세트","타입","등급","RARE","방어(초기/최대)","총 슬롯","스킬 합계","내성 합계","세트 제작 소재"],rows);
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

const MONSTER_CANONICAL_ALIASES=Object.freeze({
  "오오나즈치":"오나즈치",
  "맹폭 브라키디오스":"임계 브라키디오스",
  "혼돈에 신음하는 고어·마가라":"혼돈의 고어·마가라",
  "밀라보레아스 (흑룡)":"밀라보레아스",
  "밀라보레아스 (선조룡)":"밀라보레아스 (조룡)"
});
const MONSTER_DETAIL_ALIASES=Object.freeze({
  "임계 브라키디오스":"맹폭 브라키디오스",
  "혼돈의 고어·마가라":"혼돈에 신음하는 고어·마가라",
  "밀라보레아스":"밀라보레아스 (흑룡)",
  "밀라보레아스 (조룡)":"밀라보레아스 (선조룡)"
});
const MONSTER_REWARD_ALIASES=Object.freeze({
  "오나즈치":"오오나즈치",
  "임계 브라키디오스":"맹폭 브라키디오스",
  "혼돈의 고어·마가라":"혼돈에 신음하는 고어·마가라"
});
function canonicalMonsterName(name){return MONSTER_CANONICAL_ALIASES[String(name||"").trim()]||String(name||"").trim()}
function populateMonsterSelect(){
  const el=$("#monsterSelect"); if(!el) return;
  const old=canonicalMonsterName(el.value||"all");
  const names=(data.monsterSummary||[]).map(x=>x.name).filter(Boolean).sort((a,b)=>a.localeCompare(b,"ko"));
  el.innerHTML='<option value="all">전체 몬스터</option>'+names.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join("");
  el.value=names.includes(old)?old:"all";
}
function monsterSummaryRow(name){const key=canonicalMonsterName(name);return (data.monsterSummary||[]).find(x=>x.name===key)||null}
function monsterDetailRow(name){const key=MONSTER_DETAIL_ALIASES[canonicalMonsterName(name)]||canonicalMonsterName(name);return (data.monsterDetails||[]).find(x=>x.name===key)||null}
function selectedMonsterName(){const v=$("#monsterSelect")?.value||"all";return v==="all"?"":v}
function monsterSearchMatch(mon,q){
  if(!q)return true;
  return `${mon.name||""} ${mon.nameEn||""} ${mon.species||""} ${mon.materialName||""} ${mon.traits||""}`.toLowerCase().includes(q);
}
function renderMonsterRoster(){
  const q=$("#monsterSearch").value.trim().toLowerCase();
  const list=(data.monsterSummary||[]).filter(x=>monsterSearchMatch(x,q));
  $("#monsterRankFilter").style.display="none";
  $("#monsterContent").innerHTML=`<div class="monster-roster">${list.map(x=>`<button type="button" class="panel monster-roster-card" data-monster-card="${esc(x.name)}"><span class="monster-roster-text"><strong>${esc(x.name)}</strong><small>${esc(x.nameEn||"")}</small><span>${esc(x.species||"")}</span><em>절 ${esc(x.weakspots?.cut||"-")} · 타 ${esc(x.weakspots?.impact||"-")} · 탄 ${esc(x.weakspots?.shot||"-")}</em></span></button>`).join("")||'<div class="panel result-empty">검색 결과 없음</div>'}</div>`;
}
function monsterTabs(){
  const tabs=[["basic","기본정보"],["detail","육질"],["rewards","보수·소재"],["quests","등장 퀘스트"],["uses","제작 사용처"]];
  return `<div class="monster-tabs">${tabs.map(([v,l])=>`<button type="button" data-monster-tab="${v}" class="${monsterView===v?"active":""}">${l}</button>`).join("")}</div>`;
}
function renderMonsterBasic(mon){
  const el=mon.elements||{},ail=mon.ailments||{},tr=mon.traps||{},sp=mon.special||{};
  return `<div class="monster-basic-grid"><section class="panel monster-info-card"><h3>약점 / 특성</h3><dl><dt>종족</dt><dd>${esc(mon.species||"-")}</dd><dt>절단 약점</dt><dd>${esc(mon.weakspots?.cut||"-")}</dd><dt>타격 약점</dt><dd>${esc(mon.weakspots?.impact||"-")}</dd><dt>탄 약점</dt><dd>${esc(mon.weakspots?.shot||"-")}</dd><dt>특성</dt><dd>${esc(mon.traits||"-")}</dd></dl></section><section class="panel monster-info-card"><h3>속성 / 상태이상</h3><dl><dt>불·물·뇌·빙·용</dt><dd>${[el.fire,el.water,el.thunder,el.ice,el.dragon].map(x=>esc(x||"-")).join(" / ")}</dd><dt>독·수면·마비·폭파</dt><dd>${[ail.poison,ail.sleep,ail.paralysis,ail.blast].map(x=>esc(x||"-")).join(" / ")}</dd><dt>함정</dt><dd>${[tr.pitfall,tr.shock,tr.flash,tr.sonic,tr.meat].map(x=>esc(x||"-")).join(" / ")}</dd><dt>포효·풍압·진동</dt><dd>${[sp.roar,sp.wind,sp.tremor].map(x=>esc(x||"-")).join(" / ")}</dd></dl></section></div>`;
}
function hitzoneValue(v){
  const nums=String(v??"").match(/-?\d+(?:\.\d+)?/g);
  return nums?.length?Math.max(...nums.map(Number).filter(Number.isFinite)):0;
}
function renderMonsterHitzone(name){
  const x=monsterDetailRow(name); if(!x)return '<div class="panel result-empty">육질 상세 데이터가 없습니다.</div>';
  const summary=monsterSummaryRow(name)||{};
  const hi=summary.hitzoneHighlights||{};
  const physical=[['cut','절단'],['impact','타격'],['shot','탄'],['stun','기절'],['down','다운']];
  const elements=[['fire','불'],['water','물'],['thunder','뇌'],['ice','빙'],['dragon','용']];
  const partBestElements=hi.partBestElements||{};
  const topElementParts=Array.isArray(hi.topElementParts)?hi.topElementParts:[];
  const topPartSet=new Set(topElementParts);
  // One elemental badge per part. Top 3 parts by their best elemental hitzone also receive a star badge.
  const isPartBestElement=(part,k)=>{
    const best=partBestElements[part.part];
    return Array.isArray(best)?best.includes(k):best===k;
  };
  const partRank=part=>{const i=topElementParts.indexOf(part.part);return i>=0?i+1:0};
  const metric=(part,k,label)=>`<span class="hitzone-metric ${isPartBestElement(part,k)?'best-hitzone':''}"><small>${label}</small><strong>${esc(part[k]??'-')}</strong>${isPartBestElement(part,k)?'<i class="best-badge" title="이 부위의 최고 속성">✨</i>':''}</span>`;
  const parts=x.parts||[];
  const bestPartIndex=Math.max(0,parts.findIndex(p=>p.part===hi.bestPart));
  const partButtons=`<div class="monster-part-strip" role="tablist" aria-label="육질 부위 선택">${parts.map((part,i)=>{const rank=partRank(part);return `<button type="button" class="monster-part-chip ${i===bestPartIndex?'active ':''}${rank?'best-part-chip':''}" data-hitzone-part="${i}" aria-expanded="${i===bestPartIndex?'true':'false'}">${rank?`<i class="part-best-badge" title="속성 육질 상위 3위권(동률 포함)">⭐</i>`:''}<span>${esc(part.part)}</span></button>`}).join('')}</div>`;
  const partPanels=`<div class="monster-part-panels">${parts.map((part,i)=>{const rank=partRank(part);return `<section class="panel monster-part-panel" data-hitzone-panel="${i}" ${i===bestPartIndex?'':'hidden'}><div class="monster-part-panel-title"><strong>${rank?'<i class="part-best-badge panel-badge" title="속성 육질 상위 부위">⭐</i>':''}${esc(part.part)}</strong><span>물리 + 기절/다운 · 속성</span></div><div class="monster-hitzone-line hitzone-line-physical">${physical.map(([k,l])=>metric(part,k,l)).join('')}</div><div class="monster-hitzone-line hitzone-line-element">${elements.map(([k,l])=>metric(part,k,l)).join('')}</div></section>`}).join('')}</div>`;
  const desktopRows=parts.map(part=>{const rank=partRank(part);return `<tr class="${rank?'best-element-part-row':''}"><td>${rank?'<i class="part-best-badge" title="속성 육질 상위 부위">⭐</i>':''}${esc(part.part)}</td>${physical.map(([k])=>`<td>${esc(part[k]??'-')}</td>`).join('')}${elements.map(([k])=>`<td class="${isPartBestElement(part,k)?'best-hitzone':''}">${esc(part[k]??'-')}${isPartBestElement(part,k)?'<i class="best-badge" title="이 부위의 최고 속성">✨</i>':''}</td>`).join('')}</tr>`}).join('');
  const desktopTable=`<div class="monster-hitzone-desktop-view table-panel"><table class="data-table monster-hitzone-pc-table"><thead><tr><th rowspan="2">부위</th><th colspan="5">물리 + 기절/다운</th><th colspan="5">속성</th></tr><tr>${physical.map(([,l])=>`<th>${l}</th>`).join('')}${elements.map(([,l])=>`<th>${l}</th>`).join('')}</tr></thead><tbody>${desktopRows}</tbody></table></div>`;
  const mobileAccordion=`<div class="monster-hitzone-mobile-view">${partButtons}${partPanels}</div>`;
  const meta=x.meta||{};
  const statusRows=(x.statuses||[]).map(st=>`<tr><td>${esc(st.status)}</td><td>${esc(st.durationDamage)}</td><td>${esc(st.initial)}</td><td>${esc(st.increase)}</td><td>${esc(st.max)}</td></tr>`).join('');
  const status=`<details class="panel monster-status-details"><summary><strong>상태이상 내성</strong><span>${(x.statuses||[]).length}종</span></summary><div class="monster-status-body"><div class="table-panel monster-status-table"><table class="data-table"><thead><tr><th>상태</th><th>지속/데미지</th><th>초기내성</th><th>상승치</th><th>최대내성</th></tr></thead><tbody>${statusRows}</tbody></table></div></div></details>`;
  return `<div class="monster-meta">${meta.baseHp?`<span>기본체력 <strong>${esc(meta.baseHp)}</strong></span>`:''}${meta.minCrown?`<span>최소금관 ${esc(meta.minCrown)}</span>`:''}${meta.maxSilver?`<span>최대은관 ${esc(meta.maxSilver)}</span>`:''}${meta.maxGold?`<span>최대금관 ${esc(meta.maxGold)}</span>`:''}</div><section class="monster-hitzone-browser"><div class="monster-hitzone-guide"><strong>부위별 육질</strong><span><i class="best-badge demo">✨</i> 각 부위의 최고 속성(동률 포함) · <i class="part-best-badge">⭐</i> 속성 육질 상위 3위권(동률 포함)</span></div>${desktopTable}${mobileAccordion}</section>${status}`;
}

function monsterRankLabel(rank){return rank==="low"?"하위":rank==="high"?"상위":rank==="g"?"G급":rank==="extreme"?"극한":rank}
function renderMonsterRewards(name){
  const selectedRank=$("#monsterRankFilter").value||"all";
  const rewardName=MONSTER_REWARD_ALIASES[canonicalMonsterName(name)]||canonicalMonsterName(name);
  const rows=(data.monsterRewards||[]).filter(x=>x.monster===rewardName&&(selectedRank==="all"||x.rank===selectedRank));
  const rankOrder=["low","high","g","extreme"];
  const sections=rankOrder.filter(r=>rows.some(x=>x.rank===r)).map(rank=>{
    const rr=rows.filter(x=>x.rank===rank),methods=new Map();
    rr.forEach(x=>{const k=`${x.method||"입수"}|${x.count||""}`;if(!methods.has(k))methods.set(k,[]);methods.get(k).push(x)});
    return `<details class="panel monster-reward-rank"><summary><strong>${monsterRankLabel(rank)}</strong><span>${rr.length.toLocaleString()}건</span></summary><div class="monster-reward-rank-body">${[...methods.entries()].map(([method,list])=>`<div class="monster-reward-method"><h4>${esc(method.replace("|"," ").trim())}</h4><div class="monster-reward-items">${list.map(x=>`<div><strong>${itemLink(x.item)}</strong><span>${esc(x.probability||"-")}</span></div>`).join("")}</div></div>`).join("")}</div></details>`;
  });
  return sections.join("")||'<div class="panel result-empty">보수 데이터가 없습니다.</div>';
}
async function getMonsterReference(name){
  const key=canonicalMonsterName(name);
  const meta=data.monsterReferenceIndex?.items?.[key];
  if(monsterReferenceCache.has(key))return monsterReferenceCache.get(key);
  const promise=(async()=>{
    let ref=null;
    if(meta?.file)try{ref=await loadMonsterReference(meta.file)}catch{}
    if(ref&&Array.isArray(ref.quests)&&Array.isArray(ref.uses))return ref;
    if(!monsterFallbackPromise)monsterFallbackPromise=loadMonsterReferencesFallback().catch(()=>({}));
    const all=await monsterFallbackPromise;
    return all?.[key]||{monster:key,items:[],quests:[],uses:[]};
  })();
  monsterReferenceCache.set(key,promise);
  return promise;
}
function questTypeOrder(x){return ({village:1,hub:2,g:3,event:4,challenge:5}[x]||9)}
async function renderMonsterReferenceTab(name,kind,token){
  const host=$("#monsterTabBody");if(!host)return;
  host.innerHTML='<div class="panel monster-ref-loading">연결 데이터 불러오는 중…</div>';
  const ref=await getMonsterReference(name); if(!host.isConnected||token!==monsterRenderToken||selectedMonsterName()!==name||monsterView!==kind)return;
  if(kind==="quests"){
    const list=[...(ref.quests||[])].sort((a,b)=>questTypeOrder(a.questType)-questTypeOrder(b.questType)||String(a.level).localeCompare(String(b.level),"ko"));
    host.innerHTML=list.length?`<div class="monster-quest-list">${list.map(q=>`<div class="panel monster-quest-row">${refButton(`${q.questTypeLabel||"퀘스트"} ${q.level||""} · ${q.name||""}`.trim(),"quest",{name:q.name,questtype:q.questType})}<span>${esc([q.location,q.objective].filter(Boolean).join(" · "))}</span></div>`).join("")}</div>`:'<div class="panel result-empty">등장 퀘스트 연결이 없습니다.</div>';
  }else{
    const uses=ref.uses||[],groups=[["weapon","무기"],["armor","방어구"],["decoration","장식주"]];
    const useLine=x=>useRefHtml(x).replace(/^<li>|<\/li>$/g,"");
    host.innerHTML=groups.map(([type,label])=>{const list=uses.filter(x=>x.type===type);if(!list.length)return "";return `<details class="panel monster-use-group"><summary><strong>${label}</strong><span>${list.length.toLocaleString()}건</span></summary><ul>${list.map(x=>`<li><div class="monster-use-entry">${useLine(x)}</div><small>사용 소재: ${(x.viaItems||[]).map(i=>itemLink(i)).join(" · ")}</small></li>`).join("")}</ul></details>`}).join("")||'<div class="panel result-empty">제작 사용처 연결이 없습니다.</div>';
  }
}
let monsterRenderToken=0;
function renderMonsterDetailShell(name){
  const mon=monsterSummaryRow(name);if(!mon){renderMonsterRoster();return}
  const rankVisible=monsterView==="rewards";$("#monsterRankFilter").style.display=rankVisible?"":"none";
  const token=++monsterRenderToken;
  let body="";
  if(monsterView==="basic")body=renderMonsterBasic(mon);
  else if(monsterView==="detail")body=renderMonsterHitzone(name);
  else if(monsterView==="rewards")body=renderMonsterRewards(name);
  $("#monsterContent").innerHTML=`<section class="panel monster-hero"><div class="monster-hero-copy"><span>${esc(mon.species||"")}</span><h2>${esc(mon.name)}</h2><p>${esc(mon.nameEn||"")}</p><small>${esc(mon.materialName||"")}</small></div><button type="button" class="monster-back-list" data-monster-list>목록</button></section>${monsterTabs()}<div id="monsterTabBody">${body}</div>`;
  if(monsterView==="detail"){const status=$("#monsterTabBody .monster-status-table");if(status)decorateResponsiveTables(status);}
  if(monsterView==="quests"||monsterView==="uses")void renderMonsterReferenceTab(name,monsterView,token);
}
async function setMonsterView(view){
  monsterView=view||"basic";
  await ensureFullData(dataKeysForPage("monster"));
  renderMonster();
  const t=pageTitleForState("monster");$("#pageTitle").textContent=t[0];$("#pageSubtitle").textContent=t[1];
}
function renderMonster(){
  const name=selectedMonsterName();
  if(!name){renderMonsterRoster();return}
  renderMonsterDetailShell(name);
}

function renderDragon(){
  const q=$("#dragonSearch").value.trim().toLowerCase();
  if(dragonView==="exchange"){
    const rows=data.dragonExchange.filter(x=>!q||`${x.result} ${x.required} ${x.unlock}`.toLowerCase().includes(q)).map(x=>`<tr><td>${itemLink(x.result)}</td><td>${itemLink(x.required)}</td><td class="wrap-cell">${esc(x.unlock)}</td></tr>`);
    renderTable("#dragonTable",["교환 아이템","필요 아이템","해금 조건/퀘스트"],rows);
  }else if(dragonView==="sell"){
    const rows=data.dragonSell.filter(x=>!q||`${x.line} ${x.name}`.toLowerCase().includes(q)).map(x=>`<tr><td>${esc(x.line)}</td><td>${itemLink(x.name)}</td><td>${esc(x.points)}</td></tr>`);
    renderTable("#dragonTable",["목록","물품","필요 여단P"],rows);
  }else{
    const rows=data.dragonIncrease.filter(x=>!q||`${x.market} ${x.name}`.toLowerCase().includes(q)).map(x=>`<tr><td>${esc(x.market)}</td><td>${itemLink(x.name)}</td><td>${x.rare}</td><td>${esc(x.successRate)}</td><td>${esc(x.points)}</td></tr>`);
    renderTable("#dragonTable",["시장","아이템","RARE","성공률","필요 여단P"],rows);
  }
}

function renderCompose(){
  const q=$("#composeSearch").value.trim().toLowerCase();
  const rows=data.compositions.filter(x=>!q||`${x.result} ${x.materialA} ${x.materialB}`.toLowerCase().includes(q)).map(x=>`<tr><td>${x.no}</td><td><strong>${itemLink(x.result)}</strong></td><td>${itemLink(x.materialA)}</td><td>${itemLink(x.materialB)}</td><td>${esc(x.successRate)}</td><td>${esc(x.yield)}</td></tr>`);
  renderTable("#composeTable",["No.","조합 결과","소재 A","소재 B","성공확률","생산수"],rows);
}

function questMatchesView(q){
  if(questView==="key")return ["village","hub","g"].includes(q.questType);
  if(questView.startsWith("village"))return q.questType==="village";
  if(questView.startsWith("hub"))return q.questType==="hub";
  if(questView.startsWith("g-"))return q.questType==="g";
  if(questView==="event-all")return q.questType==="event";
  if(questView==="event-low")return q.questType==="event"&&q.eventGroup==="low";
  if(questView==="event-high")return q.questType==="event"&&q.eventGroup==="high";
  if(questView==="event-g")return q.questType==="event"&&q.eventGroup==="g";
  if(questView==="event-episodic")return q.questType==="event"&&q.eventGroup==="episodic";
  if(questView==="challenge")return q.questType==="challenge";
  return true;
}
function questRef(q){return data.questReferenceIndex?.quests?.[q.id]||{monsters:[],rewardItems:[],tags:[]}}
function populateQuestLevels(){
  const el=$("#questLevelFilter");if(!el)return;
  const old=el.value||"all";
  const type=$("#questTypeFilter")?.value||"all";
  const levelBase=type==="all"?data.quests.filter(questMatchesView):data.quests.filter(q=>questTypeFilterMatch(q,type));
  const levels=[...new Set(levelBase.map(q=>q.level))].sort((a,b)=>String(a).localeCompare(String(b),"ko",{numeric:true}));
  el.innerHTML='<option value="all">전체 ★</option>'+levels.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
  el.value=levels.includes(old)?old:"all";
}
function populateQuestAdvancedFilters(){
  const loc=$("#questLocationFilter"),mon=$("#questMonsterFilter"),rewards=$("#questRewardList");
  if(loc){const old=loc.value||"all";const vals=[...new Set(data.quests.map(q=>q.location).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"ko"));loc.innerHTML='<option value="all">전체 맵</option>'+vals.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");loc.value=vals.includes(old)?old:"all";}
  if(mon){const old=mon.value||"all";const vals=(data.monsterSummary||[]).map(x=>x.name).filter(Boolean).sort((a,b)=>a.localeCompare(b,"ko"));mon.innerHTML='<option value="all">전체 몬스터</option>'+vals.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");mon.value=vals.includes(old)?old:"all";}
  if(rewards){const vals=[...new Set([...(Object.values(data.questReferenceIndex?.quests||{}).flatMap(x=>x.rewardItems||[])),...(Object.values(data.eventMajorRewards?.quests||{}).flatMap(x=>x.rewardLabels||[]))])].sort((a,b)=>a.localeCompare(b,"ko"));rewards.innerHTML=vals.map(x=>`<option value="${esc(x)}"></option>`).join("");}
}
function questTargetMonsters(q){
  // The synchronized quest reference is the single source of truth. Re-parsing the
  // objective here used to re-introduce base/subspecies/special-form mistakes that
  // had already been fixed by the quest↔monster audit. Only imported/unindexed
  // quests fall back to text parsing.
  const indexed=questRef(q).monsters;
  if(Array.isArray(indexed)&&indexed.length)return [...new Set(indexed)];
  const norm=v=>String(v||"").toLowerCase().replace(/[\s·・･\.\-_'’“”"()（）:：]/g,"");
  const matchFrom=text=>{
    const hay=norm(text);if(!hay)return [];
    const occupied=Array(hay.length).fill(false),matched=[];
    const candidates=(data.monsterSummary||[]).flatMap(m=>[
      {name:m.name,alias:m.name},{name:m.name,alias:m.nameEn}
    ].filter(x=>x.alias)).sort((a,b)=>norm(b.alias).length-norm(a.alias).length);
    for(const c of candidates){
      const alias=norm(c.alias);if(!alias)continue;
      let pos=hay.indexOf(alias);
      while(pos>=0){
        const end=pos+alias.length;
        if(!occupied.slice(pos,end).some(Boolean)){
          if(!matched.includes(c.name))matched.push(c.name);
          for(let i=pos;i<end;i++)occupied[i]=true;
        }
        pos=hay.indexOf(alias,pos+1);
      }
    }
    return matched;
  };
  const objective=[q?.objective,q?.objectiveEn,q?.subObjective,q?.subObjectiveEn].filter(Boolean).join(" \n ");
  const direct=matchFrom(objective);if(direct.length)return direct;
  const title=matchFrom([q?.name,q?.nameEn].filter(Boolean).join(" \n "));if(title.length)return title;
  return [...new Set(questRef(q).monsters||[])];
}
function questMonsterLinks(q){
  const names=questTargetMonsters(q);if(!names.length)return "-";
  return names.map(n=>refButton(n,"monster",{monster:n})).join(' <span class="muted">·</span> ');
}
function questMajorRewardNames(q){
  const special=data.eventMajorRewards?.quests?.[q.id]?.rewardLabels||[];
  return [...new Set([...(special||[]),...(questRef(q).rewardItems||[])])];
}
function rewardEntityLink(name){
  const key=String(name||"").trim();if(!key)return "-";
  const item=(data.items||[]).find(x=>[x.name,x.nameJa,x.nameEn,...(x.aliases||[])].some(v=>String(v||"").trim()===key));
  if(item)return itemLink(item.name,item.name||key);
  const armor=(data.armors||[]).find(x=>[x.name,x.nameJa,x.nameEn,...(x.aliases||[])].some(v=>String(v||"").trim()===key));
  if(armor)return refButton(armor.name||key,"armor",{name:armor.name||key});
  const weapon=(data.weapons||[]).find(x=>[x.name,x.nameJa,x.nameEn,x.mh4uName,x.mh4uNameJa,...(x.aliases||[])].some(v=>String(v||"").trim()===key));
  if(weapon){const label=String(weapon.name||"").includes("�")?key:(weapon.name||key);return refButton(label,"weapon",{name:weapon.name||key,weapontype:weapon.weaponType||"all"});}
  return esc(key);
}
function questRewardLinks(q){
  const names=questMajorRewardNames(q);if(!names.length)return "-";
  const shown=names.slice(0,4).map(n=>rewardEntityLink(n)).join(' <span class="muted">·</span> ');
  return shown+(names.length>4?` <span class="quest-more-rewards" title="${esc(names.slice(4).join(" · "))}">+${names.length-4}</span>`:"");
}
function questTypeFilterMatch(q,v){
  if(v==="all")return true;
  const r=questRef(q),tags=r.tags||[];
  if(v==="key")return !!q.key;
  if(v==="urgent")return tags.includes("urgent");
  if(v==="event")return q.questType==="event";
  if(v==="episodic")return q.questType==="event"&&q.eventGroup==="episodic";
  if(v==="challenge")return q.questType==="challenge";
  if(v==="village"||v==="hub"||v==="g")return q.questType===v;
  return true;
}
function renderQuest(){
  populateQuestLevels();populateQuestAdvancedFilters();
  const qtext=$("#questSearch").value.trim().toLowerCase(),level=$("#questLevelFilter").value;
  const type=$("#questTypeFilter")?.value||"all",location=$("#questLocationFilter")?.value||"all",monster=$("#questMonsterFilter")?.value||"all",rewardText=($("#questRewardFilter")?.value||"").trim().toLowerCase();
  const eventView=questView.startsWith("event-")||questView==="challenge"||["event","episodic","challenge"].includes(type);
  const keyBox=$("#questKeyOnly"),keyLabel=keyBox?.closest("label");
  if(keyLabel)keyLabel.style.display=eventView?"none":"";
  const keyOnly=!eventView&&((questView==="key"&&type==="all")||keyBox?.checked);
  const list=data.quests.filter(q=>{
    const ref=questRef(q),search=`${q.name||""} ${q.nameJa||""} ${q.nameEn||""} ${(q.aliases||[]).join(" ")} ${q.objective||""} ${q.objectiveEn||""} ${q.subObjective||""} ${q.subObjectiveEn||""} ${q.location||""} ${q.eventSeries||""} ${q.note||""} ${questTargetMonsters(q).join(" ")} ${questMajorRewardNames(q).join(" ")}`.toLowerCase();
    return (type==="all"?questMatchesView(q):true)&&(level==="all"||q.level===level)&&(!keyOnly||q.key)&&questTypeFilterMatch(q,type)&&(location==="all"||q.location===location)&&(monster==="all"||questTargetMonsters(q).includes(monster))&&(!rewardText||questMajorRewardNames(q).some(x=>x.toLowerCase().includes(rewardText)))&&(!qtext||search.includes(qtext));
  });
  if(eventView){
    const questRoot=$("#questTable");if(questRoot)questRoot.className="quest-table-mode quest-table-event";
    const rows=list.map(q=>`<tr><td>${esc(q.questTypeLabel||q.questType)}</td><td>${esc(q.level)}</td><td><strong>${esc(q.name)}</strong>${localizedNameSub(q)}${plannerIconButton("quest",q.id,{label:`${q.name} 즐겨찾기`})}</td><td class="wrap-cell">${esc(q.objective||"-")}</td><td class="wrap-cell quest-monsters">${questMonsterLinks(q)}</td><td class="wrap-cell quest-rewards">${questRewardLinks(q)}</td><td>${esc(q.location||"-")}</td><td>${esc(q.fee||"-")}</td><td>${esc(q.reward||"-")}</td><td>${esc(q.hrp||"-")}</td><td>${esc(q.time||"-")}</td><td class="wrap-cell">${esc(q.subObjective||"-")}</td><td>${esc(q.subReward||"-")}</td><td>${esc(q.subHrp||"-")}</td><td class="wrap-cell">${esc(q.conditions||"-")}</td></tr>`);
    renderTable("#questTable",["구분","레벨","퀘스트","클리어 조건","몬스터","주요 보상","장소","계약금","보수금","HRP","시간","서브퀘스트","서브 보수","서브 HRP","특수조건"],rows);return;
  }
  const detail=questView.endsWith("detail")||questView==="key";
  const questRoot=$("#questTable");if(questRoot)questRoot.className=`quest-table-mode ${detail?"quest-table-detail":"quest-table-summary"}`;
  const rows=list.map(q=>detail?`<tr><td>${esc(q.questTypeLabel)}</td><td>${esc(q.level)}</td><td>${q.key?"○":""}</td><td><strong>${esc(q.name)}</strong>${localizedNameSub(q)}${plannerIconButton("quest",q.id,{label:`${q.name} 즐겨찾기`})}</td><td class="wrap-cell">${esc(q.objective)}</td><td class="wrap-cell quest-monsters">${questMonsterLinks(q)}</td><td class="wrap-cell quest-rewards">${questRewardLinks(q)}</td><td>${esc(q.location)}</td><td>${esc(q.fee)}</td><td>${esc(q.reward)}</td><td>${esc(q.time)}</td><td>${esc(q.conditions)}</td><td>${esc(q.note)}</td></tr>`:`<tr><td>${esc(q.level)}</td><td>${q.key?"○":""}</td><td><strong>${esc(q.name)}</strong>${localizedNameSub(q)}${plannerIconButton("quest",q.id,{label:`${q.name} 즐겨찾기`})}</td><td class="wrap-cell">${esc(q.objective)}</td><td class="wrap-cell quest-monsters">${questMonsterLinks(q)}</td><td class="wrap-cell quest-rewards">${questRewardLinks(q)}</td><td>${esc(q.location)}</td><td>${esc(q.note)}</td></tr>`);
  renderTable("#questTable",detail?["구분","레벨","키","퀘스트","클리어 조건","몬스터","주요 보상","장소","계약금","보수금","시간","특수조건","비고"]:["레벨","키","퀘스트","클리어 조건","몬스터","주요 보상","장소","비고"],rows);
}

function eventViewTitleText(view){
  if(view.startsWith("event-")||view==="challenge")return "이벤트 퀘스트의 한글명과 일본어/영어 원문, 목표·보수·HRP·서브퀘스트 정보를 조회합니다.";
  return "키퀘·클리어 조건·장소·보수 정보를 조회합니다.";
}
function pageTitleForState(page){
  if(page==="source") return sourceView==="history"?["이력","원본 MH4G DB 업데이트 이력"]:["메인","원본 MH4G DB 안내"];
  if(page==="armor-set") return [`${hunterName($("#hunterType").value)} 방어구 세트`,"5부위 세트의 방어·슬롯·스킬 합계를 조회합니다."];
  if(page==="weapon-summary") return ["속성별 무기요약","무기별 속성 및 각성 필요 여부를 비교합니다."];
  if(page==="melody") return ["수렵피리 선율표","음색 조합별 선율 효과와 해당 무기를 조회합니다."];
  if(page==="meal") return ["식사","식재료 조합과 조리법에 따른 식사효과·야옹스킬을 조회합니다."];
  if(page==="monster"){
    const t={basic:"몬스터",detail:"몬스터 · 육질",rewards:"몬스터 · 보수·소재",quests:"몬스터 · 등장 퀘스트",uses:"몬스터 · 제작 사용처"}[monsterView]||"몬스터";
    return [t,"몬스터 정보·육질·랭크별 보수·소재·등장 퀘스트·제작 사용처를 한 화면에서 조회합니다."];
  }
  if(page==="dragon"){
    const t={exchange:"교환소재",sell:"판매물품",increase:"아이템증식"}[dragonView];
    return [`용인족 도매상 · ${t}`,"교환·판매·증식 정보를 조회합니다."];
  }
  if(page==="compose") return ["조합서","아이템 조합식과 성공확률·생산수를 조회합니다."];
  if(page==="quest"){
    const t={key:"키퀘스트","village-detail":"여단상세","hub-detail":"집회소상세","g-detail":"G급상세","event-all":"이벤트 전체","event-low":"이벤트 하위","event-high":"이벤트 상위","event-g":"이벤트 G급","event-episodic":"에피소드","challenge":"다운로드 챌린지"}[questView];
    return [`퀘스트 · ${t||"전체"}`,eventViewTitleText(questView)];
  }
  return null;
}

async function handleRoute(btn){
  const route=btn.dataset.route;
  if(route==="armor-set"){
    armorViewMode="all";$("#hunterType").value=btn.dataset.hunter;$("#rankFilter").value="all";await openPage("armor-set");
  }else if(route==="armor-detail"){
    armorViewMode="all";$("#hunterType").value=btn.dataset.hunter;$("#rankFilter").value=btn.dataset.rank;await openPage("armor");
  }else if(route==="armor-other"){
    armorViewMode="other";$("#hunterType").value="both";$("#rankFilter").value="all";await openPage("armor");
  }else if(route==="decoration-view"){
    decoView=btn.dataset.decoView||"type";await openPage("decoration");
  }else if(route==="monster-view"){
    monsterView=btn.dataset.monsterView||"basic";await openPage("monster");
  }else if(route==="dragon-view"){
    dragonView=btn.dataset.dragonView||"exchange";await openPage("dragon");
  }else if(route==="quest-view"){
    questView=btn.dataset.questView||"key";$("#questKeyOnly").checked=questView==="key";await openPage("quest");
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
  const badge=$("#datasetBadge");
  if(badge){const isDemo=Boolean(data.meta?.demo);badge.textContent=isDemo?"샘플 데이터":`실데이터 v${data.meta?.version||""}`;badge.className=`badge ${isDemo?"warning":"good"}`;}
}

let recommendWeaponType="대검", recommendRank="low";
function populateRecommendFilters(){
  const w=$("#recommendWeaponType"),r=$("#recommendRank");if(!w||!r)return;
  const types=data.recommendedLoadouts?.weaponTypes?.length?data.recommendedLoadouts.weaponTypes:WEAPON_TYPES;
  w.innerHTML=types.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
  if(!types.includes(recommendWeaponType))recommendWeaponType=types[0]||"대검";
  w.value=recommendWeaponType;r.value=recommendRank;
}
function recommendPieceHtml(a){return `<div class="recommend-piece"><span>${esc(PART_NAMES[a.part]||a.part)}</span>${refButton(a.name,"armor",{name:a.name})}<small>DEF ${Number(a.defense||0)} · ${slotsText(a.slots)}</small></div>`;}
function recommendGuideChip(text){
  const raw=String(text||"").trim();if(!raw)return "";
  const decoName=raw.split(/[×/]/)[0].trim().replace(/\s+\d+$/,'');
  const exists=(data.decorations||[]).some(d=>d.name===decoName);
  return exists?refButton(raw,"decoration",{name:decoName}):`<span class="recommend-guide-chip">${esc(raw)}</span>`;
}
function recommendVariantHtml(v,idx){
  const b=v.build||{},decos=b.decorations||[],activated=b.activated||[],src=v.source||{},foreign=v.foreignSource||{};
  const domesticLink=src.url?`<a class="recommend-source-link" href="${esc(src.url)}" target="_blank" rel="noopener noreferrer">국내 근거 ↗</a>`:"";
  const foreignLink=foreign.url?`<a class="recommend-source-link foreign" href="${esc(foreign.url)}" target="_blank" rel="noopener noreferrer">해외 비교 ↗</a>`:"";
  const reco=(v.recommendedDecorations||[]).map(recommendGuideChip).join("");
  const applied=decos.length?`<div class="recommend-decos"><b>검증 예시 장식주</b>${decos.map(d=>refButton(`${d.name} ×${d.count}`,"decoration",{name:d.name})).join("")}</div>`:"";
  const finalExample=(v.finalSkillsExample||[]).map(x=>`<span class="recommend-guide-chip">${esc(x)}</span>`).join("");
  const guides=`${reco?`<div class="recommend-decos recommend-guide"><b>추천 장식주</b>${reco}</div>`:""}${v.talismanGuide?`<div class="recommend-guide-line"><b>호석</b><span>${esc(v.talismanGuide)}</span></div>`:""}${v.talismanSocketGuide?`<div class="recommend-guide-line"><b>호석 슬롯</b><span>${esc(v.talismanSocketGuide)}</span></div>`:""}${v.decorationPlacementExample?`<div class="recommend-guide-line"><b>배치 예시</b><span>${esc(v.decorationPlacementExample)}</span></div>`:""}${finalExample?`<div class="recommend-decos recommend-guide recommend-final"><b>최종 스킬 예시</b>${finalExample}</div>`:""}${v.exampleEvidence?`<div class="recommend-guide-line recommend-evidence"><b>예시 근거</b><span>${esc(v.exampleEvidence)}</span></div>`:""}${v.usageGuide?`<div class="recommend-guide-line"><b>활용</b><span>${esc(v.usageGuide)}</span></div>`:""}${v.foreignComparison?`<div class="recommend-compare"><b>국내↔해외</b><span>${esc(v.foreignComparison)}</span></div>`:""}`;
  return `<article class="panel recommend-variant"><div class="recommend-variant-head"><div><div class="recommend-kind">${esc(v.style||"")}${v.kind?` · ${esc(v.kind)}`:""}</div><h3>${esc(v.label)}</h3></div><div class="recommend-head-actions"><strong>DEF ${Number(b.defense||0)}</strong>${plannerIconButton("recommend",recommendPlannerId(recommendWeaponType,recommendRank,idx),{label:`${v.label} 즐겨찾기`})}</div></div><div class="recommend-active-skills"><b>검증 예시 발동</b>${activated.map(x=>`<button type="button" class="skill-active" data-open-skill="${esc(x.skillId)}">${esc(x.name)}</button>`).join("")||'<span class="muted">없음</span>'}</div><div class="recommend-pieces">${(b.armors||[]).map(recommendPieceHtml).join("")}</div>${applied}${guides}<div class="recommend-card-foot"><div class="recommend-source-links">${domesticLink}${foreignLink}<span class="recommend-engine-badge">엔진 검증</span></div><div class="recommend-sim-actions"><small>장식주·호석·무기 자동입력 없음</small><button type="button" class="ghost recommend-open-sim" data-recommend-sim="${idx}">방어구 5부위 불러오기</button></div></div></article>`;
}
function renderRecommendedLoadouts(){
  populateRecommendFilters();const root=$("#recommendContent");if(!root)return;
  const entry=(data.recommendedLoadouts?.entries||[]).find(x=>x.weaponType===recommendWeaponType&&x.rank===recommendRank);
  if(!entry){root.innerHTML='<div class="panel result-empty">추천 장비 데이터가 없습니다.</div>';return;}
  const vars=entry.variants||[];
  const heading=`<div class="recommend-heading"><h2>${esc(entry.weaponType)} · ${esc(entry.rankLabel)}</h2></div>`;
  if(!vars.length){root.innerHTML=`${heading}<div class="panel result-empty">${esc(entry.researchNote||"검증된 추천 자료를 추가 확인 중입니다.")}</div>`;return;}
  root.innerHTML=`${heading}<section class="recommend-section"><div class="recommend-variants recommend-grid-3">${vars.map((v,i)=>recommendVariantHtml(v,i)).join("")}</div></section>`;
}

async function openRecommendationInSimulator(index){
  const entry=(data.recommendedLoadouts?.entries||[]).find(x=>x.weaponType===recommendWeaponType&&x.rank===recommendRank);if(!entry)return;
  const v=entry.variants?.[Number(index)||0];if(!v)return;
  await navigatePage("simulator",{after:async()=>{
    // 추천 카드는 방어구 5부위만 불러온다. 사용자가 가진 무기·호석·장식주는 임의로 가정하지 않는다.
    uiState.manualSet="";
    for(const p of PARTS)uiState.manual[p]="";
    for(const a of v.build?.armors||[])if(PARTS.includes(a.part))uiState.manual[a.part]=a.id;
    renderManualSelectors();renderManualResult();
    document.querySelector('.manual-panel')?.scrollIntoView({block:'start',behavior:'auto'});
  }});
}

function updateHeaderFilterVisibility(){
  const typePages=new Set(["simulator","armor","armor-set","weapon"]),rankPages=new Set(["simulator","armor","armor-set","weapon"]);
  $("#hunterTypeWrap").classList.toggle("hidden-filter",!typePages.has(currentPage));
  $("#rankFilterWrap").classList.toggle("hidden-filter",!rankPages.has(currentPage));
}
const loadedFullKeys=new Set(["skills","decorations","meta"]);
let pageLoadToken=0;
function dataKeysForPage(page){
  if(page==="source")return ["siteInfo"];
  if(page==="recommend")return ["recommendedLoadouts"];
  if(page==="planner")return ["weapons","armors","items","quests","questReferenceIndex","recommendedLoadouts"];
  if(page==="armor")return ["armors"];
  if(page==="armor-set")return ["armorSets"];
  if(page==="weapon")return ["weapons","items"];
  if(page==="weapon-summary")return ["weaponSummary"];
  if(page==="decoration")return ["decorations","decorationUnlocks","items","itemReferenceIndex","skillReferenceIndex"];
  if(page==="skill")return ["items","skillReferenceIndex"];
  if(page==="melody")return ["melodies"];
  if(page==="meal")return ["meals"];
  if(page==="monster"){
    if(monsterView==="detail")return ["monsterSummary","monsterDetails"];
    if(monsterView==="rewards")return ["monsterSummary","monsterRewards","items"];
    if(monsterView==="quests")return ["monsterSummary","monsterReferenceIndex"];
    if(monsterView==="uses")return ["monsterSummary","monsterReferenceIndex","items"];
    return ["monsterSummary"];
  }
  if(page==="dragon")return dragonView==="exchange"?["dragonExchange","items"]:dragonView==="sell"?["dragonSell","items"]:["dragonIncrease","items"];
  if(page==="item")return ["items","itemReferenceIndex"];
  if(page==="compose")return ["compositions","items"];
  if(page==="quest")return ["quests","questReferenceIndex","eventMajorRewards","monsterSummary","items"];
  if(page==="data")return FULL_DATA_KEYS;
  return [];
}
async function ensureFullData(keys){
  const missing=[...new Set(keys)].filter(k=>!loadedFullKeys.has(k));
  if(!missing.length)return false;
  const patch=await loadFullData(missing);
  Object.assign(data,patch);missing.forEach(k=>loadedFullKeys.add(k));
  if(missing.some(k=>["skills","armors","armorSets","decorations","weapons","items"].includes(k)))rebuildIndexes();
  else if(missing.includes("itemReferenceIndex"))rebuildItemReferenceIndexes();
  if(missing.includes("skillReferenceIndex"))skillReferenceCache.clear();
  if(missing.includes("meals"))populateMealIngredientFilter();
  if(missing.includes("monsterSummary"))populateMonsterSelect();
  if(missing.includes("quests")){populateQuestLevels();populateQuestAdvancedFilters();}
  if(missing.includes("questReferenceIndex")||missing.includes("monsterSummary"))populateQuestAdvancedFilters();
  return true;
}
function renderPageData(page){
  if(page==="source")renderSourcePage();
  else if(page==="recommend")renderRecommendedLoadouts();
  else if(page==="planner")renderPlanner();
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
  const titles={simulator:["스킬 시뮬레이터","방어구 + 호석 + 장식주 조합을 계산합니다."],recommend:["추천 장비","무기종·진행도별 장비 구성을 확인합니다."],planner:["즐겨찾기 · 제작","저장한 장비·퀘스트와 제작 소재 체크리스트를 관리합니다."],armor:["방어구 상세","타입·등급·부위 조건으로 방어구를 조회합니다."],weapon:["무기 DB","무기 종류·파생·예리도와 제작 정보를 조회합니다."],decoration:[decoView==="slot"?"장신구 · 소켓별":"장신구 · 종류별","슬롯·스킬 포인트·생산소재를 조회합니다."],skill:["스킬 DB","스킬 계통과 발동 조건·효과를 조회합니다."],item:["아이템 DB","아이템 입수방법과 효과를 조회합니다."],data:["데이터 관리","실제 JSON 데이터 상태와 업데이트 방법을 확인합니다."]};
  const dynamic=pageTitleForState(page);
  const title=dynamic||titles[page]||["MH4G DB",""];
  if($("#pageTitle"))$("#pageTitle").textContent=title[0];
  if($("#pageSubtitle"))$("#pageSubtitle").textContent=title[1];
  safeInitStep("헤더 필터",updateHeaderFilterVisibility);
  const token=++pageLoadToken;
  const keys=dataKeysForPage(page);
  if(keys.some(k=>!loadedFullKeys.has(k))){
    if($("#pageSubtitle"))$("#pageSubtitle").textContent=`${title[1]} · 데이터 불러오는 중…`;
    try{await ensureFullData(keys);}catch(err){reportAppError(`${title[0]} 데이터 로드`,err);}
    if(token!==pageLoadToken||currentPage!==page)return;
    if($("#pageSubtitle"))$("#pageSubtitle").textContent=title[1];
  }
  try{
    if(page==="data")renderSummary();
    renderPageData(page);
  }catch(err){
    reportAppError(`${title[0]} 화면 렌더링`,err);
  }
}
function renderAll(){fillSelectors();renderSavedBuilds();renderManualSelectors();renderTargets();renderManualResult();renderSummary();updateHeaderFilterVisibility()}

// Mobile/Fold sidebar: independent columns prevent one open submenu from stretching sibling rows.
function setupResponsiveNavColumns(){
  const nav=$("#mainNav");
  if(!nav)return;
  const originalItems=[...nav.children];
  let columnCount=0;
  const mobileQuery=window.matchMedia("(max-width: 1180px) and (hover: none) and (pointer: coarse)");

  function restoreOriginal(){
    nav.classList.remove("mobile-independent-columns");
    nav.querySelectorAll(":scope > .nav-mobile-column").forEach(col=>col.remove());
    originalItems.forEach(item=>nav.appendChild(item));
    columnCount=0;
  }

  function applyColumns(){
    if(!mobileQuery.matches){
      if(columnCount)restoreOriginal();
      return;
    }
    const wanted=window.innerWidth>=600?3:2;
    if(columnCount===wanted&&nav.classList.contains("mobile-independent-columns"))return;

    nav.querySelectorAll(":scope > .nav-mobile-column").forEach(col=>col.remove());
    originalItems.forEach(item=>item.remove());
    const cols=Array.from({length:wanted},(_,i)=>{
      const col=document.createElement("div");
      col.className="nav-mobile-column";
      col.dataset.column=String(i+1);
      nav.appendChild(col);
      return col;
    });
    originalItems.forEach((item,i)=>cols[i%wanted].appendChild(item));
    nav.classList.add("mobile-independent-columns");
    columnCount=wanted;
  }

  applyColumns();
  mobileQuery.addEventListener?.("change",applyColumns);
  let resizeFrame=0;
  window.addEventListener("resize",()=>{
    cancelAnimationFrame(resizeFrame);
    resizeFrame=requestAnimationFrame(applyColumns);
  },{passive:true});
}

const rowFocusQuery=window.matchMedia("(max-width:820px), (pointer:coarse) and (max-width:1180px)");
let selectedUiRow=null;
function clearUiSelectedRows(except=null){
  if(selectedUiRow&&selectedUiRow!==except){selectedUiRow.classList.remove("ui-selected-row");}
  if(!except)selectedUiRow=null;
}
function selectUiRow(row){
  if(!row||!rowFocusQuery.matches)return;
  clearUiSelectedRows(row);
  row.classList.add("ui-selected-row");
  selectedUiRow=row;
}
rowFocusQuery.addEventListener?.("change",e=>{if(!e.matches)clearUiSelectedRows();});

const mobileJumpQuery=window.matchMedia("(max-width:820px), (hover:none) and (pointer:coarse) and (max-width:1180px)");
function setupMobilePageJump(){
  const host=$("#mobilePageJump"),topBtn=$("#pageJumpTop"),bottomBtn=$("#pageJumpBottom");
  if(!host||!topBtn||!bottomBtn)return;
  let ticking=false;
  const update=()=>{
    ticking=false;
    const mobile=mobileJumpQuery.matches;
    const doc=document.documentElement;
    const maxScroll=Math.max(0,doc.scrollHeight-window.innerHeight);
    const useful=maxScroll>Math.max(320,window.innerHeight*.45);
    host.classList.toggle("is-visible",mobile&&useful);
    topBtn.classList.toggle("is-hidden",!mobile||!useful||window.scrollY<120);
    bottomBtn.classList.toggle("is-hidden",!mobile||!useful||window.scrollY>maxScroll-120);
  };
  const schedule=()=>{if(!ticking){ticking=true;requestAnimationFrame(update)}};
  topBtn.addEventListener("click",e=>{e.preventDefault();window.scrollTo({top:0,left:0,behavior:"auto"});schedule()});
  bottomBtn.addEventListener("click",e=>{e.preventDefault();const doc=document.documentElement;window.scrollTo({top:doc.scrollHeight,left:0,behavior:"auto"});schedule()});
  window.addEventListener("scroll",schedule,{passive:true});
  window.addEventListener("resize",schedule,{passive:true});
  mobileJumpQuery.addEventListener?.("change",schedule);
  if("ResizeObserver" in window)new ResizeObserver(schedule).observe(document.body);
  schedule();
}

function bind(){
  if(appEventsBound)return true;
  const results=[];
  results.push(bindEventGroup("document-delegates",()=>{
  document.addEventListener('click',safeUiHandler('document.click',e=>{
    closePickers();
    const visualRow=e.target.closest?.('.data-table tbody tr:not(.skill-detail-row):not(.armor-detail-row), .item-list-row, .monster-quest-row, .skill-source-row, .meal-method');
    if(rowFocusQuery.matches&&visualRow&&!visualRow.classList.contains('result-empty')&&!visualRow.closest('#skillTable tr.skill-db-row'))selectUiRow(visualRow);
    const plannerFavorite=e.target.closest?.('[data-planner-favorite-kind]');
    if(plannerFavorite){e.preventDefault();e.stopPropagation();togglePlannerFavorite(plannerFavorite.dataset.plannerFavoriteKind,plannerFavorite.dataset.plannerFavoriteId);return;}
    const plannerCraft=e.target.closest?.('[data-planner-craft-kind]');
    if(plannerCraft){e.preventDefault();e.stopPropagation();addPlannerCraft(plannerCraft.dataset.plannerCraftKind,plannerCraft.dataset.plannerCraftId);return;}
    const plannerRecommend=e.target.closest?.('[data-planner-open-recommend]');
    if(plannerRecommend){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();void openPlannerRecommendation(plannerRecommend.dataset.plannerOpenRecommend).then(pushCurrentHistoryState);return;}
    const plannerRemove=e.target.closest?.('[data-planner-craft-remove]');
    if(plannerRemove){e.preventDefault();e.stopPropagation();delete plannerState.craft[plannerRemove.dataset.plannerCraftRemove];savePlannerState();renderPlanner();return;}
    const plannerDelta=e.target.closest?.('[data-planner-craft-delta]');
    if(plannerDelta){e.preventDefault();e.stopPropagation();const row=plannerDelta.closest('[data-planner-craft-key]'),key=row?.dataset.plannerCraftKey,entry=plannerState.craft[key];if(entry){entry.qty=Math.max(1,Math.min(99,(Number(entry.qty)||1)+Number(plannerDelta.dataset.plannerCraftDelta||0)));savePlannerState();renderPlanner();}return;}
    const weaponNav=e.target.closest?.('[data-open-weapon]');
    if(weaponNav){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();void navigateWeapon(weaponNav.dataset.openWeapon).then(pushCurrentHistoryState);return;}
    const weaponRow=e.target.closest?.('#weaponTrees tr.weapon-db-row[data-weapon-row]');
    if(weaponRow&&!e.target.closest('button,a,input,select,summary')){e.preventDefault();void openWeaponDetail(weaponRow);return;}
    const skillItem=e.target.closest?.('#skillTable .inline-item-link[data-open-item]');
    if(skillItem){e.preventDefault();e.stopPropagation();void openItemByName(skillItem.dataset.openItem);return;}
    const ownedSave=e.target.closest?.('[data-save-owned-charm]');if(ownedSave){saveCurrentCharmToOwned();return}
    const ownedApply=e.target.closest?.('[data-owned-charm-apply]');
    if(ownedApply){e.preventDefault();e.stopPropagation();applyOwnedCharm(ownedApply.dataset.ownedCharmApply);return;}
    const ownedRemove=e.target.closest?.('[data-owned-charm-remove]');
    if(ownedRemove){e.preventDefault();e.stopPropagation();removeOwnedCharm(ownedRemove.dataset.ownedCharmRemove);return;}
    const autoBuild=e.target.closest?.('[data-auto-build]');
    if(autoBuild&&!e.target.closest('button,a,input,select,summary')){e.preventDefault();e.stopPropagation();applyAutoBuildToSimulator(autoBuild.dataset.autoBuild);return;}
    const autoNear=e.target.closest?.('[data-auto-near]');
    if(autoNear&&!e.target.closest('button,a,input,select,summary')){e.preventDefault();e.stopPropagation();applyAutoNearMissToSimulator(autoNear.dataset.autoNear);return;}
    const recSim=e.target.closest?.('[data-recommend-sim]');
    if(recSim){e.preventDefault();e.stopPropagation();void openRecommendationInSimulator(recSim.dataset.recommendSim);return;}
    const skillBtn=e.target.closest?.('[data-open-skill]');
    if(skillBtn){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();openPage("skill").then(()=>{$("#skillSearch").value=skillName(skillBtn.dataset.openSkill)||"";$("#skillCategoryFilter").value="all";$("#skillTypeFilter").value="all";renderSkillTable();pushCurrentHistoryState();});return;}
    const decoBtn=e.target.closest?.('[data-open-deco]');
    if(decoBtn){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();void openPage("decoration").then(()=>{$("#decoRankFilter").value="all";$("#decoSlotFilter").value="all";$("#decoCategoryFilter").value="all";$("#decoSearch").value=decoBtn.dataset.openDeco||"";renderDecoTable();pushCurrentHistoryState();});return;}
    const plannerNav=e.target.closest?.('#page-planner [data-item-nav]');
    if(plannerNav){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();followItemReference(plannerNav).then(pushCurrentHistoryState);return;}
    const skillNav=e.target.closest?.('#skillTable .skill-source-body [data-item-nav]');
    if(skillNav){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();followItemReference(skillNav).then(pushCurrentHistoryState);return;}
    const skillRow=e.target.closest?.('#skillTable tr.skill-db-row[data-skill-row]');
    if(skillRow){
      if(e.target.closest('button,a,input,select,details,summary'))return;
      e.preventDefault();void openSkillDetail(skillRow.dataset.skillRow,skillRow);return;
    }
    const monsterCard=e.target.closest?.('[data-monster-card]');
    if(monsterCard){e.preventDefault();replaceCurrentHistoryState();$("#monsterSelect").value=monsterCard.dataset.monsterCard;$("#monsterSearch").value="";monsterView="basic";renderMonster();pushCurrentHistoryState();return;}
    const monsterTab=e.target.closest?.('[data-monster-tab]');
    if(monsterTab){e.preventDefault();replaceCurrentHistoryState();setMonsterView(monsterTab.dataset.monsterTab).then(pushCurrentHistoryState);return;}
    const hitzonePart=e.target.closest?.('[data-hitzone-part]');
    if(hitzonePart){
      e.preventDefault();
      const root=hitzonePart.closest('.monster-hitzone-browser');
      if(!root)return;
      const key=hitzonePart.dataset.hitzonePart;
      const panel=root.querySelector(`[data-hitzone-panel="${key}"]`);
      const wasOpen=hitzonePart.getAttribute('aria-expanded')==='true';
      root.querySelectorAll('[data-hitzone-part]').forEach(b=>{b.setAttribute('aria-expanded','false');b.classList.remove('active')});
      root.querySelectorAll('[data-hitzone-panel]').forEach(p=>p.hidden=true);
      if(!wasOpen&&panel){hitzonePart.setAttribute('aria-expanded','true');hitzonePart.classList.add('active');panel.hidden=false;}
      return;
    }
    const monsterList=e.target.closest?.('[data-monster-list]');
    if(monsterList){e.preventDefault();replaceCurrentHistoryState();$("#monsterSelect").value="all";$("#monsterSearch").value="";monsterView="basic";renderMonster();pushCurrentHistoryState();return;}
    const monsterNav=e.target.closest?.('#monsterContent [data-item-nav]');
    if(monsterNav){e.preventDefault();replaceCurrentHistoryState();followItemReference(monsterNav).then(pushCurrentHistoryState);return;}
    const questNav=e.target.closest?.('#questTable [data-item-nav]');
    if(questNav){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();followItemReference(questNav).then(pushCurrentHistoryState);return;}
    const armorProgressNav=e.target.closest?.('#armorTable .armor-detail-row [data-item-nav]');
    if(armorProgressNav){e.preventDefault();e.stopPropagation();replaceCurrentHistoryState();followItemReference(armorProgressNav).then(pushCurrentHistoryState);return;}
    const inline=e.target.closest?.('[data-open-item]');
    if(inline){e.preventDefault();e.stopPropagation();openItemByName(inline.dataset.openItem);return;}
    const armorRow=e.target.closest?.('#armorTable tr.armor-db-row[data-armor-id]');
    if(armorRow){e.preventDefault();void toggleArmorProgressRow(armorRow);return;}
    const itemRow=e.target.closest?.('#itemTable [data-item-id]');
    if(itemRow){e.preventDefault();replaceCurrentHistoryState();renderItemDetail(itemRow.dataset.itemId).then(pushCurrentHistoryState);return;}
    const nav=e.target.closest?.('#itemTable .item-detail-inline [data-item-nav]');
    if(nav){e.preventDefault();replaceCurrentHistoryState();followItemReference(nav).then(pushCurrentHistoryState);return;}
    const close=e.target.closest?.('#itemTable .item-detail-close');
    if(close){e.preventDefault();removeItemDetailRow();selectedItemId="";replaceCurrentHistoryState();return;}
  }));
  document.addEventListener("change",safeUiHandler("document.change",e=>{
    const qty=e.target.closest?.('[data-planner-craft-qty]');
    if(qty){const entry=plannerState.craft[qty.dataset.plannerCraftQty];if(entry){entry.qty=Math.max(1,Math.min(99,Number(qty.value)||1));savePlannerState();renderPlanner();}return;}
    const inv=e.target.closest?.('[data-planner-inventory]');
    if(inv){plannerState.inventory[inv.dataset.plannerInventory]=Math.max(0,Math.min(9999,Number(inv.value)||0));savePlannerState();renderPlanner();return;}
  }));
  document.addEventListener("keydown",safeUiHandler("document.keydown",e=>{const armorRow=e.target.closest?.('#armorTable tr.armor-db-row[data-armor-id]');if(armorRow&&(e.key==="Enter"||e.key===" ")){e.preventDefault();void toggleArmorProgressRow(armorRow);return;}const bcard=e.target.closest?.('[data-auto-build]');if(bcard&&(e.key==="Enter"||e.key===" ")){e.preventDefault();applyAutoBuildToSimulator(bcard.dataset.autoBuild);return;}const ncard=e.target.closest?.('[data-auto-near]');if(ncard&&(e.key==="Enter"||e.key===" ")){e.preventDefault();applyAutoNearMissToSimulator(ncard.dataset.autoNear);return;}const wrow=e.target.closest?.('#weaponTrees tr.weapon-db-row[data-weapon-row]');if(wrow&&(e.key==="Enter"||e.key===" ")){e.preventDefault();void openWeaponDetail(wrow);return;}const row=e.target.closest?.('#skillTable tr.skill-db-row[data-skill-row]');if(row&&(e.key==="Enter"||e.key===" ")){e.preventDefault();void openSkillDetail(row.dataset.skillRow,row);}}));
  document.addEventListener("toggle",safeUiHandler("document.toggle",e=>{
    const d=e.target;
    if(d?.matches?.("#itemTable details.xref-lazy"))void hydrateXrefGroup(d);
    if(d?.open&&d.matches?.("#skillTable details.skill-source-group")){
      const host=d.parentElement;
      host?.querySelectorAll(":scope > details.skill-source-group[open]").forEach(other=>{if(other!==d)other.open=false});
    }
    if(d?.open&&d.matches?.("#skillTable details.skill-armor-set")){
      const host=d.parentElement;
      host?.querySelectorAll(":scope > details.skill-armor-set[open]").forEach(other=>{if(other!==d)other.open=false});
    }
  }),true);
  }));
  results.push(bindEventGroup("navigation",()=>{
  $("#sidebarToggle").onclick=()=>{$(".app-shell").classList.toggle("sidebar-collapsed");const collapsed=$(".app-shell").classList.contains("sidebar-collapsed");$("#sidebarToggle").title=collapsed?"좌측 메뉴 펼치기":"좌측 메뉴 접기";};

  $$('.nav-group-toggle').forEach(b=>b.onclick=e=>{
    e.stopPropagation();
    const menu=$(`#${b.dataset.submenu}`);
    if(menu)menu.classList.toggle("open");
  });
  $$('.nav-main[data-page]').forEach(b=>b.onclick=e=>{
    e.stopPropagation();
    const targetPage=b.dataset.page;
    const targetSource=b.dataset.sourceView||sourceView;
    if(targetPage===currentPage&&targetSource===sourceView){void openPage(targetPage);return;}
    void navigatePage(targetPage,{source:b.dataset.sourceView||null});
  });
  $$('[data-route]').forEach(b=>b.onclick=e=>{
    e.stopPropagation();
    replaceCurrentHistoryState();
    void handleRoute(b).then(pushCurrentHistoryState);
  });
  }));
  results.push(bindEventGroup("simulator-controls",()=>{
  $("#addTargetSkill").onclick=()=>{const v=uiState.targetActivation;if(v&&!targets.includes(v)){targets.push(v);renderTargets()}};
  $("#clearTargets").onclick=()=>{targets=[];renderTargets()};$("#calculateManual").onclick=renderManualResult;$("#runSearch").onclick=runSearch;renderOwnedCharms();
  $("#saveBuild").onclick=saveCurrentBuild;$("#deleteBuild").onclick=deleteSelectedBuild;$("#savedBuildSelect").onchange=loadSelectedBuild;

  $("#hunterType").onchange=()=>{
    if(currentPage==="armor")renderArmorTable();
    if(currentPage==="armor-set"){renderArmorSetTable();const t=pageTitleForState("armor-set");$("#pageTitle").textContent=t[0]}
    if(currentPage==="weapon"){renderWeaponTreeFilter();renderWeaponTrees()}
  };
  $("#rankFilter").onchange=()=>{
    if(currentPage==="armor")renderArmorTable();
    if(currentPage==="armor-set")renderArmorSetTable();
    if(currentPage==="weapon"){renderWeaponTreeFilter();renderWeaponTrees()}
  };
  $("#includeTorsoUp").onchange=()=>{renderManualResult()};
  }));
  results.push(bindEventGroup("database-filters",()=>{
  let armorSearchTimer=null;
  $("#armorSearch").oninput=()=>{if(armorSearchTimer)clearTimeout(armorSearchTimer);armorSearchTimer=setTimeout(renderArmorTable,110)};$("#armorPartFilter").onchange=renderArmorTable;
  $("#armorSetSearch").oninput=renderArmorSetTable;
  $("#weaponSearch").oninput=renderWeaponTrees;$("#weaponTypeFilter").onchange=()=>{renderWeaponTreeFilter();renderWeaponTrees()};$("#weaponTreeFilter").onchange=renderWeaponTrees;$("#weaponElementFilter").onchange=renderWeaponTrees;$("#weaponSort").onchange=renderWeaponTrees;
  $("#weaponSummarySearch").oninput=renderWeaponSummary;$("#weaponSummaryType").onchange=renderWeaponSummary;
  $("#melodySearch").oninput=renderMelodyTable;
  $("#decoSearch").oninput=renderDecoTable;$("#decoRankFilter").onchange=renderDecoTable;$("#decoSlotFilter").onchange=renderDecoTable;$("#decoCategoryFilter").onchange=renderDecoTable;$("#skillSearch").oninput=renderSkillTable;$("#skillCategoryFilter").onchange=renderSkillTable;$("#skillTypeFilter").onchange=renderSkillTable;
  $("#mealSearch").oninput=renderMealGrid;$("#mealIngredientFilter").onchange=renderMealGrid;
  $("#monsterSearch").oninput=()=>{if($("#monsterSelect").value!=="all")$("#monsterSelect").value="all";renderMonster()};$("#monsterSelect").onchange=()=>{monsterView="basic";$("#monsterSearch").value="";renderMonster()};$("#monsterRankFilter").onchange=renderMonster;
  $("#dragonSearch").oninput=renderDragon;
  $("#itemSearch").oninput=renderItemTable;
  $("#composeSearch").oninput=renderCompose;
  $("#questSearch").oninput=renderQuest;$("#questLevelFilter").onchange=renderQuest;$("#questKeyOnly").onchange=renderQuest;$("#questTypeFilter").onchange=renderQuest;$("#questLocationFilter").onchange=renderQuest;$("#questMonsterFilter").onchange=renderQuest;$("#questRewardFilter").oninput=renderQuest;
  }));
  results.push(bindEventGroup("recommendation",()=>{
  $("#recommendWeaponType").onchange=e=>{recommendWeaponType=e.target.value;renderRecommendedLoadouts()};$("#recommendRank").onchange=e=>{recommendRank=e.target.value;renderRecommendedLoadouts()};
  }));
  results.push(bindEventGroup("planner-controls",()=>{
    const clearFav=$("#plannerClearFavorites"),clearCraft=$("#plannerClearCraft"),resetInventory=$("#plannerResetInventory");
    if(clearFav)clearFav.onclick=()=>{plannerState.favorites={weapon:[],armor:[],recommend:[],quest:[]};savePlannerState();renderPlanner();};
    if(clearCraft)clearCraft.onclick=()=>{plannerState.craft={};savePlannerState();renderPlanner();};
    if(resetInventory)resetInventory.onclick=()=>{plannerState.inventory={};savePlannerState();renderPlanner();};
  }));
  results.push(bindEventGroup("json-import",()=>{
  $("#jsonImport").onchange=async e=>{const lines=[];for(const f of e.target.files){try{const json=JSON.parse(await f.text()),type=classifyImported(f.name,json);if(type){data[type]=json;lines.push(`${f.name} → ${type} ${Array.isArray(json)?json.length:"객체"}건`)}else lines.push(`${f.name} → 유형 판별 실패`)}catch{lines.push(`${f.name} → JSON 오류`)}}data.meta={...data.meta,demo:false,version:"browser-import"};rebuildIndexes();$("#importStatus").innerHTML=lines.map(esc).join("<br>");renderAll()};
  }));
  results.push(bindEventGroup("history-lifecycle",()=>{
    window.addEventListener("popstate",safeUiHandler("history.popstate",e=>{
      if(!e.state?.mh4g)return;
      return restoreAppHistoryState(e.state);
    }));
    window.addEventListener("pageshow",safeUiHandler("history.pageshow",e=>{
      if(e.persisted)updateHeaderFilterVisibility();
    }));
  }));
  appEventsBound=results.every(Boolean);
  if(!appEventsBound)showRuntimeStatus("일부 화면 이벤트 연결에 실패했습니다. 실패한 기능만 재시도할 수 있으며 메뉴 이동은 유지됩니다.","warn");
  return appEventsBound;
}

async function bootstrapApp(){
  // 데이터 다운로드가 느리거나 실패해도 메뉴/기본 이벤트는 먼저 살아 있어야 한다.
  bind();
  safeInitStep("반응형 메뉴",setupResponsiveNavColumns);
  safeInitStep("모바일 빠른 이동",setupMobilePageJump);
  const initialState=history.state?.mh4g?history.state:null;
  if(!initialState)replaceCurrentHistoryState();
  showRuntimeStatus("기본 데이터를 불러오는 중입니다. 메뉴 이동은 사용할 수 있습니다.","loading");
  try{
    const patch=await loadSimulatorData();
    Object.assign(data,patch);
    const missingCore=["skills","armors","armorSets","decorations","weapons"].filter(k=>!Array.isArray(patch[k])||patch[k].length===0);
    if(!patch.recommendedLoadouts||!Array.isArray(patch.recommendedLoadouts.entries)||patch.recommendedLoadouts.entries.length===0)missingCore.push("recommendedLoadouts");
    safeInitStep("검색 인덱스",rebuildIndexes);
    safeInitStep("초기 화면",renderAll);
    if(currentPage!=="simulator")safeInitStep("현재 화면 갱신",()=>renderPageData(currentPage));
    if(initialState)await restoreAppHistoryState(initialState);
    if(missingCore.length)showRuntimeStatus(`일부 기본 데이터를 불러오지 못했습니다: ${missingCore.join(", ")} · 메뉴와 정상 로드된 기능은 계속 사용할 수 있습니다.`,"warn");
    else if(appEventsBound)clearRuntimeStatus();
  }catch(err){
    reportAppError("기본 데이터 로드",err);
    // 데이터 오류와 관계없이 이미 연결된 메뉴/버튼은 유지한다.
    safeInitStep("최소 화면 복구",()=>{updateHeaderFilterVisibility();renderSummary();});
  }finally{
    // 실패한 이벤트 그룹이 있었다면 성공한 그룹은 건드리지 않고 실패 그룹만 다시 시도한다.
    bind();
  }
}

window.addEventListener("error",e=>{
  if(e?.error)reportAppError("런타임",e.error);
});
window.addEventListener("unhandledrejection",e=>{
  reportAppError("비동기",e.reason||new Error("처리되지 않은 비동기 오류"));
});
void bootstrapApp();
// 아이템 역참조는 아이템 화면 진입/아이템 링크 첫 사용 시에만 불러온다.
// 대용량 JSON을 백그라운드에서 임의 파싱해 다른 화면의 포인터/스크롤 프레임을 끊지 않도록 prewarm은 사용하지 않는다.
