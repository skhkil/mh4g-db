"use strict";
(function(){
  const $=id=>document.getElementById(id);
  const state={motion:[],cat:[],bows:[],weak:[],excelWeak:[]};
  const dataUrls={
    motion:"./data/workbook_motion_20261116.json?v=1",
    cat:"./data/workbook_meownster_20261116.json?v=1",
    bows:"./data/workbook_relic_bows_20261116.json?v=1",
    excelWeak:"./data/workbook_weakspots_20261116.json?v=1",
    weak:"./data/monster_details.json?v=workbook-reference-20261116"
  };
  function unique(values){return Array.from(new Set(values.filter(Boolean))).sort((a,b)=>a.localeCompare(b,"ko"))}
  function norm(v){return String(v??"").normalize("NFKC").toLowerCase().replace(/\s+/g," ").trim()}
  function setOptions(select,values,defaultLabel){
    select.replaceChildren();
    const empty=document.createElement("option");empty.value="";empty.textContent=defaultLabel;select.append(empty);
    for(const value of unique(values)){const o=document.createElement("option");o.value=value;o.textContent=value;select.append(o)}
  }
  function showRows(body,list,fields){
    const frag=document.createDocumentFragment();
    for(const record of list){
      const tr=document.createElement("tr");
      for(let i=0;i<fields.length;i++){
        const td=document.createElement("td");
        const item=fields[i];
        td.textContent=String(item.get(record)??"");
        if(item.num)td.classList.add("num");
        tr.append(td);
      }
      frag.append(tr);
    }
    body.replaceChildren(frag);
  }
  function count(id,shown,all){$(id).textContent=shown.toLocaleString("ko-KR")+"건 표시 / 총 "+all.toLocaleString("ko-KR")+"건"}
  function renderMotion(){
    const group=$("motionWeapon").value;
    const query=norm($("motionSearch").value);
    const list=state.motion.filter(r=>(!group||r.weapon===group)&&(!query||norm([r.weapon,r.motion,r.ratio,r.detail,r.note].join(" ")).includes(query)));
    showRows($("motionRows"),list,[
      {get:r=>r.weapon},{get:r=>r.motion},{get:r=>r.ratio,num:true},
      {get:r=>[r.detail,r.note].filter(Boolean).join(" · ")},{get:r=>r.sourceRow,num:true}
    ]);
    count("motionCount",list.length,state.motion.length);
  }
  function renderCat(){
    const group=$("catGroup").value;
    const region=$("catRegion").value;
    const query=norm($("catSearch").value);
    const list=state.cat.filter(r=>(!group||r.group===group)&&(!region||r.region===region)&&(!query||norm([r.group,r.region,r.target,r.item,r.sourceValue].join(" ")).includes(query)));
    showRows($("catRows"),list,[
      {get:r=>r.group},{get:r=>r.region},{get:r=>r.target},{get:r=>r.item},
      {get:r=>r.sourceValue,num:true},{get:r=>r.sourceRow,num:true}
    ]);
    count("catCount",list.length,state.cat.length);
  }
  function renderBow(){
    showRows($("bowRows"),state.bows,[
      {get:r=>String(r.id).padStart(2,"0"),num:true},{get:r=>r.charges},
      {get:r=>r.arc},{get:r=>r.coatings},{get:r=>r.sourceRow,num:true}
    ]);
  }
  function addMessage(host,message){const p=document.createElement("p");p.textContent=message;p.className="muted";host.replaceChildren(p)}
  function labeled(host,rows){
    const dl=document.createElement("dl");
    for(const [name,value] of rows){const dt=document.createElement("dt");dt.textContent=name;const dd=document.createElement("dd");dd.textContent=String(value||"—");dl.append(dt,dd)}
    host.append(dl);
  }
  function renderWeak(){
    const monster=$("weakMonster").value;
    const attack=$("weakAttack").value;
    const host=$("weakData"),compare=$("weakExcel");
    host.replaceChildren();compare.replaceChildren();
    if(!monster){addMessage(host,"몬스터를 선택하세요.");addMessage(compare,"몬스터를 선택하세요.");return}
    const data=state.weak.find(x=>x.name===monster);
    if(!data){addMessage(host,"사이트 상세 육질 자료 없음");return}
    const parts=(data.parts||[]).map(x=>{
      const text=String(x[attack]??"").trim();
      return {part:x.part,text,value:/^\d+(?:\.\d+)?$/.test(text)?Number(text):null};
    }).filter(x=>x.value!==null&&x.value>=45).sort((a,b)=>b.value-a.value||a.part.localeCompare(b.part,"ko"));
    if(!parts.length)addMessage(host,"해당 조건의 단일 수치 45 이상 부위가 없거나 별도 상태값으로 기록되어 있습니다.");
    else{
      const ol=document.createElement("ol");
      for(const item of parts){const li=document.createElement("li");li.textContent=item.part+"  —  "+item.text;ol.append(li)}
      host.append(ol);
    }
    const excel=state.excelWeak.find(x=>norm(x.name)===norm(monster));
    if(!excel){addMessage(compare,"엑셀 약점표에 동일한 이름이 없습니다. 이름을 임의로 매칭하지 않았습니다.");return}
    labeled(compare,[
      ["절단",excel.weakspots.cut],["타격",excel.weakspots.impact],["탄",excel.weakspots.shot],
      ["불",excel.elements.fire],["물",excel.elements.water],["번개",excel.elements.thunder],
      ["얼음",excel.elements.ice],["용",excel.elements.dragon],["원본 행",excel.sourceRow]
    ]);
  }
  async function load(key){
    const response=await fetch(dataUrls[key],{cache:"no-cache"});
    if(!response.ok)throw new Error("HTTP "+response.status);
    const result=await response.json();
    return Array.isArray(result)?result:Array.isArray(result.records)?result.records:[];
  }
  function setupTabs(){
    const buttons=Array.from(document.querySelectorAll(".tab"));
    function switchTab(id){
      if(!["motion","meownster","bow","weak"].includes(id))id="motion";
      for(const b of buttons){const on=b.dataset.tab===id;b.classList.toggle("active",on);b.setAttribute("aria-selected",String(on))}
      for(const pane of document.querySelectorAll(".pane")){const on=pane.id==="pane-"+id;pane.classList.toggle("active",on);pane.hidden=!on}
    }
    for(const b of buttons)b.addEventListener("click",()=>{switchTab(b.dataset.tab);history.replaceState(null,"","#"+b.dataset.tab)});
    switchTab(location.hash.slice(1));
  }
  async function main(){
    setupTabs();
    const keys=Object.keys(dataUrls);
    const results=await Promise.allSettled(keys.map(load));
    for(let i=0;i<keys.length;i++){
      if(results[i].status==="fulfilled")state[keys[i]]=results[i].value;
      else console.warn("자료 로딩 실패",keys[i],results[i].reason);
    }
    setOptions($("motionWeapon"),state.motion.map(x=>x.weapon),"모든 무기");
    setOptions($("catGroup"),state.cat.map(x=>x.group),"전체 랭크/식량");
    setOptions($("catRegion"),state.cat.map(x=>x.region),"전체 지역");
    setOptions($("weakMonster"),state.weak.map(x=>x.name),"몬스터 선택");
    for(const id of ["motionWeapon","motionSearch"])$(id).addEventListener("input",renderMotion);
    for(const id of ["catGroup","catRegion","catSearch"])$(id).addEventListener("input",renderCat);
    $("weakMonster").addEventListener("change",renderWeak);
    $("weakAttack").addEventListener("change",renderWeak);
    const preferred=state.weak.find(x=>x.name==="테오·테스카토르");
    if(preferred)$("weakMonster").value=preferred.name;
    renderMotion();renderCat();renderBow();renderWeak();
    if(!state.motion.length)count("motionCount",0,0);
    if(!state.cat.length)count("catCount",0,0);
  }
  document.addEventListener("DOMContentLoaded",()=>{main().catch(error=>console.error("자료실 초기화 실패",error))});
})();
