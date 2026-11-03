
let state={level:"1",attack:"",affinity:"",defense:"",sharp:"unknown",slots:"unknown",element:"",attributeKind:"none",attributeActivation:"normal",fixedDecorationId:"",editingId:"",special:{}},loaded=null,loading=null,sequence=0;
const node=(t,c,v)=>{const x=document.createElement(t);if(c)x.className=c;if(v!==undefined)x.textContent=v;return x};
const select=(options,value,onChange)=>{const s=node("select");for(const [v,label] of options){const o=node("option",null,label);o.value=v;s.append(o)}s.value=value;s.onchange=()=>onChange(s.value);return s};
const field=(label,control)=>{const l=node("label","rp-field");l.append(node("span",null,label),control);return l};
const num=(value,ph,onChange)=>{const x=node("input");x.type="number";x.inputMode="numeric";x.step="1";x.placeholder=ph;x.value=value;x.oninput=()=>onChange(x.value);return x};
const text=(host,value,cls="rr-note")=>host.append(node("p",cls,value));
export function predictRelic(d,type,level,shown,affinity,defense,sharpness="unknown"){
 const table=d.weaponAttackTables?.find(x=>x.weaponType===type),p=d.attackProgression;
 if(!table||!p||!Number.isInteger(level)||level<1||level>4||!Number.isInteger(shown)||shown<=0)return [];
 const rule=p.bonusRules?.[type],result=[];
 const variants=sharpness==="naturalPurple"?["natural"]:sharpness==="unknown"?["natural","handicraft"]:["handicraft"];
 const fixedBonuses={대검:{natural:20,handicraft:10},해머:{natural:20,handicraft:10},태도:{natural:20,handicraft:10},쌍검:{natural:20,handicraft:10},한손검:{natural:35,handicraft:20},랜스:{natural:35,handicraft:20}};
 for(const [base,seq] of Object.entries(p.stages)){
  const i=level-1;
  for(const variant of (fixedBonuses[type]?variants:["handicraft"])){
   const bonus=fixedBonuses[type]?.[variant]??0, naturalBonus=0;
   if(!Number.isFinite(seq.raw[i]))continue;
   const stageBonus=rule?.key==="raw"&&base==="250"&&i===0?Math.max(0,bonus-10):bonus;
   const raw=seq.raw[i]+(rule?.key==="raw"?stageBonus:0);
   const a=seq.affinity[i]===null?null:seq.affinity[i]+(rule?.key==="affinity"?bonus:0)+naturalBonus;
   const df=seq.defense[i]===null?null:seq.defense[i]+(rule?.key==="defense"?bonus:0);
   if(Math.round(raw*table.displayMultiplier)!==shown)continue;
   if(Number.isFinite(affinity)&&a!==null&&a!==affinity)continue;
   if(Number.isFinite(defense)&&df!==null&&df!==defense)continue;
   const next=p.stages[base],last=3;
   const finalRaw=next.raw[last]===null?null:next.raw[last]+(rule?.key==="raw"?bonus:0);
   const finalAffinity=next.affinity[last]===null?null:next.affinity[last]+(rule?.key==="affinity"?bonus:0)+naturalBonus;
   const finalDefense=next.defense[last]===null?null:next.defense[last]+(rule?.key==="defense"?bonus:0);
   result.push({base,bonus,naturalBonus,variant,raw,affinity:a,defense:df,finalRaw,finalAffinity,finalDefense,finalDisplay:finalRaw===null?null:Math.round(finalRaw*table.displayMultiplier),uncertain:a===null||df===null});
  }
 }
 return result;
}
export function physicalIndex(raw,aff,sharpness=1){
 if(!Number.isFinite(raw)||!Number.isFinite(aff)||!Number.isFinite(sharpness))return null;
 const affinityFactor=1+(aff/100)*0.25;
 return raw*affinityFactor*sharpness;
}
function render(d,type,guide,host,decorations=[],traits=null){
 const retainedTables=[...host.querySelectorAll(":scope > .table-panel, :scope > .rp-reference .rp-reference-table, :scope > .panel > .table-panel")];
 host.replaceChildren();
 const sharpnessApplicable=!["라이트보우건","헤비보우건","활"].includes(type);
 const form=node("section","panel rp-panel"),head=node("div","rr-heading");
 head.append(node("span","rr-step","무기 성능 판별 · 강화 테이블"),node("h2",null,"발굴무기 강화 수치 조회"));
 text(head,"공격력·회심률·방어력·속성을 목록에서 선택하면 아래 강화표가 자동으로 갱신됩니다. 직접 숫자를 입력할 필요가 없습니다.");
 form.append(head);
 const inputs=node("div","rp-fields");
 const refresh=()=>render(d,type,guide,host,decorations,traits);
 const change=(key,value,resets=[])=>{state[key]=value;for(const k of resets)state[k]="";refresh()};
 const stage=Number(state.level),p=d.attackProgression,table=d.weaponAttackTables.find(t=>t.weaponType===type),rule=p.bonusRules?.[type];
 const isGunner=["라이트보우건","헤비보우건","활"].includes(type);
 const bonusVariants={대검:[0,10,20],해머:[0,10,20],태도:[0,10,20],쌍검:[0,10,20],한손검:[0,20,35],랜스:[0,20,35]};
 const attackValues=new Set();
 for(const [base,seq] of Object.entries(p.stages)){
   const raw=seq.raw[stage-1];if(raw===null||!Number.isFinite(raw))continue;
   for(const b of bonusVariants[type]||[0]){
     const adj=rule?.key==="raw"&&base==="250"?Math.max(0,b-10):b;
     attackValues.add(Math.round((raw+(rule?.key==="raw"?adj:0))*table.displayMultiplier));
   }
 }
 const attacks=[...attackValues].sort((a,b)=>a-b);
 if(state.attack&&!attacks.includes(Number(state.attack))){state.attack="";state.affinity="";state.defense=""}
 const candidatesFor=(shown,af=NaN,def=NaN)=>state.attack?predictRelic(d,type,stage,shown,af,def,sharpnessApplicable?state.sharp:"unknown"):[];
 const all=state.attack?candidatesFor(Number(state.attack)):[];
 const affinityValues=[...new Set(all.map(x=>x.affinity).filter(Number.isFinite))].sort((a,b)=>a-b);
 if(state.affinity&&!affinityValues.includes(Number(state.affinity))){state.affinity="";state.defense=""}
 const aff=state.affinity===""?NaN:Number(state.affinity);
 const afterAff=state.affinity===""?all:candidatesFor(Number(state.attack),aff);
 const defenses=[...new Set(afterAff.map(x=>x.defense).filter(Number.isFinite))].sort((a,b)=>a-b);
 if(state.defense&&!defenses.includes(Number(state.defense)))state.defense="";
 inputs.append(field("강화 단계",select([["1","Lv1 미강화"],["2","Lv2"],["3","Lv3"],["4","Lv4 최종"]],state.level,x=>change("level",x,["attack","affinity","defense"]))));
 inputs.append(field("표시 공격력",select([["","공격력 선택"],...attacks.map(v=>[String(v),String(v)])],state.attack,x=>change("attack",x,["affinity","defense"]))));
 inputs.append(field("회심률",select([["","회심률 선택"],...affinityValues.map(v=>[String(v),(v>0?"+":"")+v+"%"])],state.affinity,x=>change("affinity",x,["defense"]))));
 inputs.append(field("방어력 보너스",select([["","선택 안 함"],...defenses.map(v=>[String(v),"+"+v])],state.defense,x=>change("defense",x))));
 form.append(inputs);
 const optional=node("details","rp-extra");optional.open=true;optional.append(node("summary",null,"예리도 · 속성 · 슬롯"));
 const extra=node("div","rp-fields");
 if(sharpnessApplicable)extra.append(field("예리도 유형",select(Object.entries(guide.sharpness).map(([id,x])=>[id,x.label]),state.sharp,x=>change("sharp",x,["attack","affinity","defense"]))));
 const group=traits?.weaponGroups?.find(g=>g.names.includes(type));
 const kinds=traits?.attributeKinds||[["none","무속성"],["fire","불"],["water","물"],["thunder","번개"],["ice","얼음"],["dragon","용"],["poison","독"],["paralysis","마비"],["sleep","수면"],["blast","폭파"]];
 const allowedKinds=(!group||isGunner)?[["none","무속성/미확인"]]:kinds.filter(([k])=>!group.statusExceptions?.includes(type)||!["poison","paralysis","sleep","blast"].includes(k));
 if(!allowedKinds.some(([k])=>k===state.attributeKind))state.attributeKind="none";
 const valueKey=(["poison","paralysis","sleep","blast"].includes(state.attributeKind)?"Status":"Element");
 const values=state.attributeKind==="none"?[]:group?.[(state.attributeActivation==="awakened"?"awakened":"normal")+valueKey]||[];
 if(state.element&&!values.includes(Number(state.element)))state.element="";
 extra.append(field("속성·상태이상",select(allowedKinds,state.attributeKind,x=>{state.attributeKind=x;state.element="";refresh()})));
 if(state.attributeKind!=="none"&&group)extra.append(field("발동 조건",select([["normal","일반"],["awakened","각성 필요"]],state.attributeActivation,x=>{state.attributeActivation=x;state.element="";refresh()})));
 if(state.attributeKind!=="none"&&group)extra.append(field("속성치",select([["","수치 선택"],...values.map(v=>[String(v),String(v)])],state.element,x=>change("element",x))));
 if(!group)text(optional,"이 무기종의 속성 수치 선택 테이블은 아직 검증되지 않았습니다.","rr-note");
 else if(group.statusExceptions?.includes(type))text(optional,"활의 상태이상 수치는 이 자료에서 별도 검증 대상이므로 제외했습니다.","rr-note");
 extra.append(field("슬롯 구성",select(guide.slots,state.slots,x=>change("slots",x))));
 optional.append(extra);
 const fixedList=(decorations||[]).filter(x=>x.relicOnly&&x.fixedDecoration);
 const fixedPicker=select([["","고정 장식주 선택"],...fixedList.map(x=>[x.id,x.name])],state.fixedDecorationId,x=>{state.fixedDecorationId=x;refresh()});
 optional.append(field("고정 장식주 (고정 장식 선택 시)",fixedPicker));
 const profile=guide.weaponSpecial[type],specialControls=node("div","rp-fields");
 for(const spec of profile.fields||[])specialControls.append(field(spec.label,select(spec.options,state.special[type+"-"+spec.id]||"unknown",v=>{state.special[type+"-"+spec.id]=v;refresh()})));
 if(profile.fields?.length)optional.append(node("h3",null,type+" 전용 옵션"),specialControls);
 form.append(optional);
 const owner=node("section","rp-owned");owner.append(node("h3",null,"STEP 6 · 보유 발굴무기 저장 및 연동"));
 text(owner,"이름·성능·슬롯을 기존 보유 발굴무기 저장소에 보관합니다. 슬롯 미확인이나 고정 장식주 미선택 무기는 자동조합에 투입하지 않습니다.");
 const ownedList=node("div","rp-owned-fields");
 const nickname=node("input");nickname.type="text";nickname.maxLength=55;nickname.placeholder="구분용 이름 (선택)";
 const nameKey="mh4g-relic-performance-name";nickname.value=state[nameKey]||"";nickname.oninput=()=>{state[nameKey]=nickname.value};
 const existing=node("select");existing.setAttribute("aria-label","저장된 발굴무기 불러오기");
 ownedList.append(field("무기 구분 이름",nickname),field("저장한 무기 불러오기",existing));
 owner.append(ownedList);
 const ownerActions=node("div","rp-owned-actions"),save=node("button","rp-run","현재 무기 저장"),discard=node("button","ghost","새 무기로 입력");
 ownerActions.append(save,discard);owner.append(ownerActions);
 const status=node("p","rr-note");owner.append(status);form.append(owner);
 const result=node("div","rp-results");form.append(result);
 const refs=node("details","rp-reference");refs.append(node("summary",null,"기존 무기별 기본배율·강화 표 참고"));
 for(const t of retainedTables){t.classList.add("rp-reference-table");refs.append(t)}
 form.append(refs);
 const legacy=host.querySelector(".relic-attack-check");if(legacy)legacy.hidden=true;
 host.insertBefore(form,host.firstChild);
 function calculate(){
  result.replaceChildren();
  const shown=Number(state.attack),lv=Number(state.level);
  if(!state.attack||!Number.isInteger(shown)||shown<=0){text(result,"위에서 공격력을 선택하면 강화표가 자동으로 표시됩니다.","rr-note");return}
  const af=state.affinity.trim()===""?NaN:Number(state.affinity),def=state.defense.trim()===""?NaN:Number(state.defense);
  if(state.affinity.trim()!==""&&(!Number.isInteger(af)||af< -100||af>100)){text(result,"회심률은 -100~100의 정수로 입력해 주세요.","rp-caution");return}
  if(state.defense.trim()!==""&&(!Number.isInteger(def)||def<0)){text(result,"방어력 보너스는 0 이상의 정수로 입력해 주세요.","rp-caution");return}
  const candidates=predictRelic(d,type,lv,shown,af,def,sharpnessApplicable?state.sharp:"unknown");
  if(!candidates.length){
    text(result,"일치하는 고정 성능 유형이 없습니다. 무기 자체 수치인지, 선택한 강화 단계와 예리도가 맞는지 확인해 주세요. 자료가 미확인인 유형은 조회되지 않을 수 있습니다.","rp-caution");
    return;
  }
  const unique=[...new Map(candidates.map(c=>[[c.base,c.bonus,c.variant].join("|"),c])).values()];
  const summary=node("p","rr-note",unique.length===1?"고정 테이블 일치 · 강화 단계별 수치":"일치하는 유형 "+unique.length+"개 · 회심/방어/예리도 선택으로 후보를 좁힐 수 있습니다.");
  result.append(summary);
  const table=d.weaponAttackTables.find(t=>t.weaponType===type);
  for(const c of unique){
    const card=node("article","rp-candidate");
    card.append(node("h3",null,"공격 계열 "+c.base+(c.variant==="natural"?" · 기본 보라 20":c.variant==="handicraft"?" · 예리도+1 보라 유형":"")));
    const grid=node("div","rp-candidate-table");
    const tab=node("table");tab.className="table-panel";
    const thead=node("thead"),tr=node("tr");
    for(const title of ["강화","공격력","회심률","방어 보너스"])tr.append(node("th",null,title));
    thead.append(tr);tab.append(thead);
    const tbody=node("tbody"),p=d.attackProgression,seq=p.stages[c.base],rule=p.bonusRules?.[type];
    for(let i=0;i<4;i++){
      const stageBonus=rule?.key==="raw"&&c.base==="250"&&i===0?Math.max(0,c.bonus-10):c.bonus;
      const raw=seq.raw[i]===null?null:seq.raw[i]+(rule?.key==="raw"?stageBonus:0);
      const a=seq.affinity[i]===null?null:seq.affinity[i]+(rule?.key==="affinity"?c.bonus:0)+c.naturalBonus;
      const df=seq.defense[i]===null?null:seq.defense[i]+(rule?.key==="defense"?c.bonus:0);
      const row=node("tr");
      for(const v of ["Lv"+(i+1)+(i===lv-1?" (현재)":""),raw===null?"미확인":String(Math.round(raw*table.displayMultiplier)),a===null?"미확인":(a>0?"+":"")+a+"%",df===null?"미확인":"+"+df])row.append(node("td",null,v));
      tbody.append(row);
    }
    tab.append(tbody);grid.append(tab);card.append(grid);
    if(seq.raw.some(x=>x===null)||seq.affinity.some(x=>x===null)||seq.defense.some(x=>x===null))text(card,"일부 중간 단계는 검증된 수치가 없어 미확인으로 표시합니다.","rr-note");
    result.append(card);
  }
  if(state.attributeKind!=="none")text(result,"선택 속성: "+(kinds.find(([k])=>k===state.attributeKind)?.[1]||state.attributeKind)+" "+(state.element||"미선택")+(state.attributeActivation==="awakened"?" (각성 필요)":"")+" · Lv2~Lv4 동일","rr-note");
  text(result,"강화표는 확인된 공격 계열만 표시합니다. 일부 중간 수치와 속성·공격 유형의 조합 가능성은 미검증입니다. 자료: MH4G@wiki / otameshine.","rr-note");
 }
 const STORE="mh4g-owned-relic-weapons-v1";
 const records=()=>{try{const a=JSON.parse(localStorage.getItem(STORE)||"[]");return Array.isArray(a)?a:[]}catch{return []}};
 const signature=x=>JSON.stringify([x.performance?.weaponType,x.performance?.attack,x.performance?.level,x.performance?.affinity,x.performance?.defense,x.slotMode,x.slots,x.decorationId,x.performance?.sharp,x.performance?.element]);
 function refreshOwned(){
  const items=records().filter(x=>x.performance?.weaponType===type);
  existing.replaceChildren();const def=node("option",null,"새 무기 등록");def.value="";existing.append(def);
  for(const item of items){const o=node("option",null,item.performance?.name||type+" "+item.performance?.attack||item.id);o.value=item.id;existing.append(o)}
  existing.value=state.editingId;if(existing.value!==state.editingId){state.editingId="";existing.value=""}
  save.textContent=state.editingId?"선택한 무기 갱신":"현재 무기 저장";
 }
 existing.onchange=()=>{
  state.editingId=existing.value;const item=records().find(x=>x.id===existing.value);if(!item){refreshOwned();return}
  const p=item.performance||{};state.attack=String(p.attack||"");state.level=String(p.level||"1");state.affinity=p.affinity===null?"":String(p.affinity??"");state.defense=p.defense===null?"":String(p.defense??"");
  state.sharp=p.sharp||"unknown";state.element=String(p.element||"");state.attributeKind=p.attributeKind||"none";state.attributeActivation=p.attributeActivation||"normal";state.slots=item.slotMode==="empty"?({0:"none",1:"empty1",2:"empty2",3:"empty3"}[item.slots]||"unknown"):item.slotMode==="fixed"?"fixed":"unknown";
  state.fixedDecorationId=item.decorationId||"";state[nameKey]=p.name||"";
  state.special={...state.special,...(p.special||{})};
  render(d,type,guide,host,decorations,traits);
 };
 discard.onclick=()=>{state.editingId="";state.attack="";state.affinity="";state.defense="";state.level="1";state.sharp="unknown";state.slots="unknown";state.element="";state.attributeKind="none";state.attributeActivation="normal";state.fixedDecorationId="";state[nameKey]="";render(d,type,guide,host,decorations,traits)};
 save.onclick=()=>{
  const shown=Number(state.attack),lv=Number(state.level);
  const affinity=state.affinity.trim()===""?null:Number(state.affinity),defense=state.defense.trim()===""?null:Number(state.defense);
  if(!Number.isInteger(shown)||shown<=0||!Number.isInteger(lv)||lv<1||lv>4){status.textContent="공격력과 강화 단계를 먼저 입력하세요.";return}
  if(affinity!==null&&(!Number.isInteger(affinity)||affinity< -100||affinity>100)){status.textContent="회심률 입력을 확인하세요.";return}
  if(defense!==null&&(!Number.isInteger(defense)||defense<0)){status.textContent="방어력 입력을 확인하세요.";return}
  const slot=state.slots,mode=slot==="fixed"?"fixed":slot==="unknown"?"unknown":"empty",slots=slot==="fixed"?Number(fixedList.find(x=>x.id===state.fixedDecorationId)?.slots||0):slot==="unknown"?0:slot==="none"?0:Number(slot.replace("empty",""));
  if(mode==="fixed"&&!fixedList.some(x=>x.id===state.fixedDecorationId)){status.textContent="고정 장식주가 있는 무기는 실제 장식주 종류를 선택해야 시뮬레이터에 적용할 수 있습니다. 선택하지 않아도 미확인으로 저장됩니다.";}
  const deco=fixedList.find(x=>x.id===state.fixedDecorationId),confirmed=mode!=="fixed"||!!deco;
  const p={weaponType:type,name:state[nameKey]||"",level:lv,attack:shown,affinity,defense,sharp:state.sharp,element:state.element,attributeKind:state.attributeKind,attributeActivation:state.attributeActivation,special:{...state.special}};
  const record={id:state.editingId||"relic_perf_"+Date.now()+"_"+Math.random().toString(36).slice(2,8),slotMode:!confirmed?"unknown":mode,slots:!confirmed?0:slots,decorationId:confirmed&&mode==="fixed"?deco.id:"",skills:confirmed&&mode==="fixed"?{...deco.skills}:{},performance:p};
  const all=records(),idx=all.findIndex(x=>x.id===record.id),dup=idx<0?all.findIndex(x=>x.performance&&signature(x)===signature(record)):-1;
  if(idx>=0)all[idx]=record;else if(dup>=0){record.id=all[dup].id;all[dup]=record}else all.push(record);
  try{localStorage.setItem(STORE,JSON.stringify(all))}catch(e){status.textContent="로컬 저장 실패: "+e.message;return}
  state.editingId=record.id;status.textContent="보유 발굴무기 목록에 저장됨"+(record.slotMode==="unknown"?" · 슬롯 정보 미확인으로 스킬조합 제외":"");
  document.dispatchEvent(new CustomEvent("mh4g-owned-relic-weapons-changed"));
  refreshOwned();
 };
 refreshOwned();
 calculate();
}
export async function mountRelicPerformance(d,type,decorations=[]){
 const id=++sequence;const host=document.querySelector("#relicPanel-attack > .panel");if(!host)return;
 try{
  if(!loading)loading=fetch("./data/relic_performance_guide.json?v=0.7.9-relic-select-stats",{cache:"no-cache"}).then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()}).then(v=>{loaded=v;return v}).catch(e=>{loading=null;throw e});
  const guide=loaded||await loading;
  const traits=await fetch("./data/relic_weapon_traits.json?v=0.7.9-relic-select-stats",{cache:"no-cache"}).then(r=>{if(!r.ok)throw Error("traits HTTP "+r.status);return r.json()});
  if(id!==sequence||!host.isConnected)return;
  render(d,type,guide,host,decorations,traits);
 }catch(e){if(id!==sequence||!host.isConnected)return;host.append(node("p","rp-caution","성능 분석 자료를 불러오지 못했습니다: "+e.message))}
}
