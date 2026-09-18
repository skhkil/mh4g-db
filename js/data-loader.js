const DATA_VERSION = "0.7.7-chat4-recommend-weapon-research";

const FULL_FILES = {
  skills:"./data/skills.json",
  armors:"./data/armors.json",
  armorSets:"./data/armor_sets.json",
  decorations:"./data/decorations.json",
  weapons:"./data/weapons.json",
  weaponSummary:"./data/weapon_summary.json",
  melodies:"./data/melodies.json",
  items:"./data/items.json",
  itemReferenceIndex:"./data/item_reference_index.json",
  skillReferenceIndex:"./data/skill_reference_index.json",
  meals:"./data/meals.json",
  monsterSummary:"./data/monster_summary.json",
  monsterDetails:"./data/monster_details.json",
  monsterRewards:"./data/monster_rewards.json",
  monsterReferenceIndex:"./data/monster_reference_index.json",
  dragonExchange:"./data/dragon_exchange.json",
  dragonSell:"./data/dragon_sell.json",
  dragonIncrease:"./data/dragon_increase.json",
  compositions:"./data/compositions.json",
  quests:"./data/quests.json",
  questReferenceIndex:"./data/quest_reference_index.json",
  siteInfo:"./data/site_info.json",
  meta:"./data/meta.json",
  recommendedLoadouts:"./data/recommended_loadouts.json"
};

// 시뮬레이터 첫 화면에 필요한 필드만 담은 경량 데이터.
// 전체 DB 화면을 열 때는 FULL_FILES의 원본 JSON을 지연 로딩한다.
const SIMULATOR_FILES = {
  skills:"./data/skills.json",
  armors:"./data/sim_armors.json",
  armorSets:"./data/sim_armor_sets.json",
  decorations:"./data/decorations.json",
  weapons:"./data/sim_weapons.json",
  meta:"./data/meta.json",
  recommendedLoadouts:"./data/recommended_loadouts.json"
};

export const FULL_DATA_KEYS = Object.freeze(Object.keys(FULL_FILES));
const requestCache = new Map();

function emptyValue(key){
  return (key==="meta"||key==="siteInfo"||key.endsWith("Index"))?{}:[];
}
function versioned(url){
  return `${url}?v=${DATA_VERSION}`;
}
async function fetchJson(key,url){
  const cacheKey=`${key}:${url}`;
  if(requestCache.has(cacheKey)) return requestCache.get(cacheKey);
  const promise=(async()=>{
    try{
      // 버전 쿼리로 새 배포는 갱신하고, 같은 버전은 브라우저 캐시를 적극 사용한다.
      const r=await fetch(versioned(url),{cache:"force-cache"});
      if(!r.ok) throw new Error(`${r.status}`);
      return await r.json();
    }catch(e){
      console.error("load failed",url,e);
      return emptyValue(key);
    }
  })();
  requestCache.set(cacheKey,promise);
  return promise;
}
async function loadMap(fileMap,keys=Object.keys(fileMap)){
  const selected=keys.filter(k=>fileMap[k]);
  const rows=await Promise.all(selected.map(async k=>[k,await fetchJson(k,fileMap[k])]));
  return Object.fromEntries(rows);
}

export function loadSimulatorData(){
  return loadMap(SIMULATOR_FILES);
}

export function loadFullData(keys=FULL_DATA_KEYS){
  return loadMap(FULL_FILES,keys);
}

export async function loadItemReference(itemId){
  const key=String(itemId||"").trim();
  if(!key) return {id:key,acquire:[],uses:[]};
  return fetchJson(`itemRef:${key}`,`./data/item_refs/${encodeURIComponent(key)}.json`);
}

export async function loadSkillReference(file){
  const key=String(file||"").trim();
  if(!key) return {decorations:[],armors:[]};
  const x=await fetchJson(`skillRef:${key}`,`./data/skill_refs/${encodeURIComponent(key)}`);
  return (x&&typeof x==="object"&&!Array.isArray(x))?x:{decorations:[],armors:[]};
}

export async function loadMonsterReference(file){
  const key=String(file||"").trim();
  if(!key) return {monster:"",items:[],quests:[],uses:[]};
  const x=await fetchJson(`monsterRef:${key}`,`./data/monster_refs/${encodeURIComponent(key)}.json`);
  return (x&&typeof x==="object"&&!Array.isArray(x))?x:null;
}

export async function loadMonsterReferencesFallback(){
  const x=await fetchJson("monsterReferencesFallback","./data/monster_references.json");
  return (x&&typeof x==="object"&&!Array.isArray(x))?x:{};
}

// 이전 코드 호환용: 인자가 없으면 전체 데이터를 병렬 로딩한다.
export function loadData(){
  return loadFullData();
}

export function classifyImported(name,json){
  const lower=name.toLowerCase();
  const rules=[
    ["armor_sets","armorSets"],["armor","armors"],["decor","decorations"],["weapon_summary","weaponSummary"],
    ["weapon","weapons"],["skill_reference_index","skillReferenceIndex"],["skill","skills"],["item_reference_index","itemReferenceIndex"],["item","items"],["meal","meals"],
    ["monster_summary","monsterSummary"],["monster_details","monsterDetails"],["monster_rewards","monsterRewards"],["monster_reference_index","monsterReferenceIndex"],
    ["dragon_exchange","dragonExchange"],["dragon_sell","dragonSell"],["dragon_increase","dragonIncrease"],
    ["composition","compositions"],["quest_reference_index","questReferenceIndex"],["quest","quests"],["melod","melodies"],["site_info","siteInfo"]
  ];
  for(const [needle,key] of rules) if(lower.includes(needle)) return key;
  if(Array.isArray(json)&&json.length){
    const x=json[0];
    if("pieces" in x&&"hunterType" in x) return "armorSets";
    if("part" in x&&"defense" in x) return "armors";
    if("activations" in x) return "skills";
    if("slots" in x&&"skills" in x&&!("part" in x)) return "decorations";
    if("attack" in x||"weaponType" in x) return "weapons";
    if("rare" in x&&("acquire" in x||"maxStack" in x)) return "items";
    if("questType" in x) return "quests";
    if("ingredient1" in x) return "meals";
    if("species" in x&&"weakspots" in x) return "monsterSummary";
    if("parts" in x&&"statuses" in x) return "monsterDetails";
    if("probability" in x&&"monster" in x) return "monsterRewards";
  }
  return null;
}
