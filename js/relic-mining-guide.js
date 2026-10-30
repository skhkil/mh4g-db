
let miningData=null, miningPromise=null;
const n=(tag,cls,value)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=value;return e};
function miningLink(label,url){const a=n("a",null,label);a.href=url;a.target="_blank";a.rel="noopener noreferrer";return a}
async function getMining(){
 if(miningData)return miningData;
 if(!miningPromise)miningPromise=(async()=>{
  const res=await fetch("./data/relic_mining_guide.json?v=0.7.7-relic-mining-4",{cache:"no-cache"});
  if(!res.ok)throw new Error("HTTP "+res.status);
  const json=await res.json();
  if(!Array.isArray(json.miningNodes)||!Array.isArray(json.treasurePatterns))throw new Error("채굴 데이터 형식 오류");
  return miningData=json;
 })().catch(e=>{miningPromise=null;throw e});
 return miningPromise;
}
export async function mountRelicMining(root,level=136){
 if(!root?.isConnected)return;
 root.replaceChildren();
 const intro=n("div","rr-heading");intro.append(n("span","rr-step","04 · 보물구역·채굴"),n("h2",null,"채굴로 발굴장비 얻기"),n("p","rr-note","보물구역과 일반 구역의 파란 광석을 비교합니다. 퀘스트 클리어 보상과는 다른 획득 경로입니다."));root.append(intro);
 let data;
 try{data=await getMining()}catch(e){root.append(n("p","rr-note","채굴 데이터를 불러오지 못했습니다. "+e.message));return}
 if(!root.isConnected)return;
 if(Number(level)<126)root.append(n("p","rr-note rr-caution","현재 Lv"+level+"은 봉인된 발굴무기 출현이 확인되는 Lv126보다 낮습니다. 아래 추첨 비율을 현재 레벨에 적용할 수 없습니다."));
 const cards=n("div","rr-mining-grid");
 for(const entry of data.miningNodes){
  const card=n("article","rr-mining-card");card.append(n("h3",null,entry.name),n("p","rr-note",entry.location));
  const rates=n("div","rr-mining-rates");
  for(const [title,value] of [["봉인된 무기",entry.sealedWeaponPercent],["봉인된 방어구",entry.sealedArmorPercent]]){
   const stat=n("div","rr-mining-rate");stat.append(n("small",null,title),n("strong",null,value+"%"));rates.append(stat)
  }
  card.append(rates,n("p","rr-note","광석 채굴 1회 추첨 기준 · 일본 플레이어 분석 자료"));cards.append(card);
 }
 root.append(cards);
 const caveat=n("p","rr-note rr-caution",data.note+" 보물구역 출현률·채굴 횟수·클리어 보상과 합산하지 않습니다.");root.append(caveat);
 const layout=n("details","rr-more");layout.append(n("summary",null,"보물구역 구조·파란 광석 지점 보기"));
 const patterns=n("div","rr-mining-patterns");
 for(const pat of data.treasurePatterns){const row=n("div","rr-mining-pattern");row.append(n("strong",null,pat.id),n("span",null,pat.areas),n("small",null,"파란 광석 지점 "+pat.fixedBlueNodes+"곳"));patterns.append(row)}
 layout.append(patterns);
 for(const rule of data.treasureRules)layout.append(n("p","rr-note",rule));
 root.append(layout);
 const details=n("details","rr-more");details.append(n("summary",null,"채굴 확률 해석과 원자료"));
 for(const restriction of data.restrictions)details.append(n("p","rr-note",restriction));
 const links=n("div","rr-mining-links");
 links.append(miningLink("보물구역 등장·위치 (MH4G@wiki)",data.sources.wikiGuildQuest),
  miningLink("보물구역 구조 (MH4G@wiki)",data.sources.wikiExploration),
  miningLink("파란 광석 확률 분석",data.sources.miningAnalysis));
 details.append(links);root.append(details);
}
