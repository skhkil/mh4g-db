const FILES = {
  skills:"./data/skills.json",
  armors:"./data/armors.json",
  armorSets:"./data/armor_sets.json",
  decorations:"./data/decorations.json",
  weapons:"./data/weapons.json",
  weaponSummary:"./data/weapon_summary.json",
  melodies:"./data/melodies.json",
  items:"./data/items.json",
  meals:"./data/meals.json",
  monsterSummary:"./data/monster_summary.json",
  monsterDetails:"./data/monster_details.json",
  monsterRewards:"./data/monster_rewards.json",
  dragonExchange:"./data/dragon_exchange.json",
  dragonSell:"./data/dragon_sell.json",
  dragonIncrease:"./data/dragon_increase.json",
  compositions:"./data/compositions.json",
  quests:"./data/quests.json",
  siteInfo:"./data/site_info.json",
  meta:"./data/meta.json"
};

export async function loadData(){
  const out={};
  for(const [k,url] of Object.entries(FILES)){
    try{
      const r=await fetch(url,{cache:"no-store"});
      if(!r.ok) throw new Error(`${r.status}`);
      out[k]=await r.json();
    }catch(e){
      console.error("load failed",url,e);
      out[k]=(k==="meta"||k==="siteInfo")?{}:[];
    }
  }
  return out;
}

export function classifyImported(name,json){
  const lower=name.toLowerCase();
  const rules=[
    ["armor_sets","armorSets"],["armor","armors"],["decor","decorations"],["weapon_summary","weaponSummary"],
    ["weapon","weapons"],["skill","skills"],["item","items"],["meal","meals"],
    ["monster_summary","monsterSummary"],["monster_details","monsterDetails"],["monster_rewards","monsterRewards"],
    ["dragon_exchange","dragonExchange"],["dragon_sell","dragonSell"],["dragon_increase","dragonIncrease"],
    ["composition","compositions"],["quest","quests"],["melod","melodies"],["site_info","siteInfo"]
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
