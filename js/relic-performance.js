
let state={level:"1",attack:"",affinity:"",defense:"",sharp:"unknown",slots:"unknown",element:"",fixedDecorationId:"",editingId:"",special:{}},loaded=null,loading=null,sequence=0;
const node=(t,c,v)=>{const x=document.createElement(t);if(c)x.className=c;if(v!==undefined)x.textContent=v;return x};
const select=(options,value,onChange)=>{const s=node("select");for(const [v,label] of options){const o=node("option",null,label);o.value=v;s.append(o)}s.value=value;s.onchange=()=>onChange(s.value);return s};
const field=(label,control)=>{const l=node("label","rp-field");l.append(node("span",null,label),control);return l};
const num=(value,ph,onChange)=>{const x=node("input");x.type="number";x.inputMode="numeric";x.step="1";x.placeholder=ph;x.value=value;x.oninput=()=>onChange(x.value);return x};
const text=(host,value,cls="rr-note")=>host.append(node("p",cls,value));
export function predictRelic(d,type,level,shown,affinity,defense){
 const table=d.weaponAttackTables?.find(x=>x.weaponType===type),p=d.attackProgression;
 if(!table||!p||!Number.isInteger(level)||level<1||level>4||!Number.isInteger(shown)||shown<=0)return [];
 const rule=p.bonusRules?.[type],result=[];
 for(const [base,seq] of Object.entries(p.stages)){
  const i=level-1;
  for(const bonus of rule?.increments||[0]){
   if(!Number.isFinite(seq.raw[i]))continue;
   const raw=seq.raw[i]+(rule?.key==="raw"?bonus:0);
   const a=seq.affinity[i]===null?null:seq.affinity[i]+(rule?.key==="affinity"?bonus:0);
   const df=seq.defense[i]===null?null:seq.defense[i]+(rule?.key==="defense"?bonus:0);
   if(Math.round(raw*table.displayMultiplier)!==shown)continue;
   if(Number.isFinite(affinity)&&a!==null&&a!==affinity)continue;
   if(Number.isFinite(defense)&&df!==null&&df!==defense)continue;
   const next=p.stages[base],last=3;
   const finalRaw=next.raw[last]===null?null:next.raw[last]+(rule?.key==="raw"?bonus:0);
   const finalAffinity=next.affinity[last]===null?null:next.affinity[last]+(rule?.key==="affinity"?bonus:0);
   const finalDefense=next.defense[last]===null?null:next.defense[last]+(rule?.key==="defense"?bonus:0);
   result.push({base,bonus,raw,affinity:a,defense:df,finalRaw,finalAffinity,finalDefense,finalDisplay:finalRaw===null?null:Math.round(finalRaw*table.displayMultiplier),uncertain:a===null||df===null});
  }
 }
 return result;
}
export function physicalIndex(raw,aff,sharpness=1){
 if(!Number.isFinite(raw)||!Number.isFinite(aff)||!Number.isFinite(sharpness))return null;
 const affinityFactor=1+(aff/100)*0.25;
 return raw*affinityFactor*sharpness;
}
function render(d,type,guide,host,decorations=[]){
 const retainedTables=[...host.querySelectorAll(".table-panel")];
 host.replaceChildren();
 const sharpnessApplicable=!["라이트보우건","헤비보우건","활"].includes(type);
 const form=node("section","panel rp-panel"),head=node("div","rr-heading");
 head.append(node("span","rr-step","무기 성능 분석 · STEP 4~5"),node("h2",null,"발굴무기 성능·강화 가치 분석"));
 text(head,"공격력과 회심을 입력하면 기대 물리 성능을 계산합니다. 예리도·슬롯·무기별 특수옵션은 선택 입력이며, 확인되지 않은 값은 추정하지 않습니다.");
 form.append(head);
 const inputs=node("div","rp-fields");
 inputs.append(field("강화 단계",select([["1","Lv1 미강화"],["2","Lv2"],["3","Lv3"],["4","Lv4 최종"]],state.level,x=>{state.level=x;render(d,type,guide,host)})));
 inputs.append(field("무기 표시 공격력",num(state.attack,"예: 대검 1728",x=>{state.attack=x})));
 inputs.append(field("무기 자체 회심률 (%)",num(state.affinity,"예: -25",x=>{state.affinity=x})));
 inputs.append(field("무기 자체 방어력 (+)",num(state.defense,"선택",x=>{state.defense=x})));
 form.append(inputs);
 const optional=node("details","rp-extra");optional.append(node("summary",null,"예리도·속성·슬롯 추가 입력 (선택)"));
 const extra=node("div","rp-fields");
 if(sharpnessApplicable)extra.append(field("실전 유지 예리도",select(Object.entries(guide.sharpness).map(([id,x])=>[id,x.label]),state.sharp,x=>{state.sharp=x})));
 extra.append(field("슬롯 구성",select(guide.slots,state.slots,x=>{state.slots=x})));
 extra.append(field("속성/상태이상 메모",num(state.element,"해당 수치 · 선택",x=>{state.element=x})));
 optional.append(extra);
 const fixedList=(decorations||[]).filter(x=>x.relicOnly&&x.fixedDecoration);
 const fixedPicker=select([["","고정 장식주 선택"],...fixedList.map(x=>[x.id,x.name])],state.fixedDecorationId,x=>{state.fixedDecorationId=x});
 optional.append(field("고정 장식주 (고정 장식 선택 시)",fixedPicker));
 const profile=guide.weaponSpecial[type],specialControls=node("div","rp-fields");
 for(const spec of profile.fields||[])specialControls.append(field(spec.label,select(spec.options,state.special[type+"-"+spec.id]||"unknown",v=>{state.special[type+"-"+spec.id]=v})));
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
 const run=node("button","rp-run","성능 분석하기"),result=node("div","rp-results");run.type="button";form.append(run,result);
 const refs=node("details","rp-reference");refs.append(node("summary",null,"기존 무기별 기본배율·강화 표 참고"));
 for(const t of retainedTables){t.classList.add("rp-reference-table");refs.append(t)}
 form.append(refs);
 const legacy=host.querySelector(".relic-attack-check");if(legacy)legacy.hidden=true;
 host.insertBefore(form,host.firstChild);
 function calculate(){
  result.replaceChildren();
  const shown=Number(state.attack),lv=Number(state.level);
  if(!state.attack||!Number.isInteger(shown)||shown<=0){text(result,"무기 표시 공격력을 입력해 주세요.","rp-caution");return}
  const af=state.affinity.trim()===""?NaN:Number(state.affinity),def=state.defense.trim()===""?NaN:Number(state.defense);
  if(state.affinity.trim()!==""&&(!Number.isInteger(af)||af< -100||af>100)){text(result,"회심률은 -100~100의 정수로 입력해 주세요.","rp-caution");return}
  if(state.defense.trim()!==""&&(!Number.isInteger(def)||def<0)){text(result,"무기 방어 보너스는 0 이상의 정수로 입력해 주세요.","rp-caution");return}
  const candidates=predictRelic(d,type,lv,shown,af,def);
  const table=d.weaponAttackTables.find(t=>t.weaponType===type),raw=shown/table.displayMultiplier;
  const sharp=sharpnessApplicable?guide.sharpness[state.sharp]:null;
  const chosenFactor=sharpnessApplicable?(sharp?.factor??null):1;
  const actualAff=Number.isFinite(af)?af:(candidates.length===1?candidates[0].affinity:null);
  const metrics=node("div","rp-metrics");
  const metric=(label,value,detail)=>{const x=node("div","rp-metric");x.append(node("small",null,label),node("strong",null,value));if(detail)x.append(node("span",null,detail));metrics.append(x)};
  metric("현재 환산 공격배율",raw.toFixed(2),"무기 자체 공격력 ÷ 표시배율");
  metric("회심 기대 물리배율",actualAff===null?"회심 입력 필요":physicalIndex(raw,actualAff).toFixed(2),"예리도 보정 전 · 모션/육질 제외");
  metric("예리도까지 반영",chosenFactor===null?"예리도 미선택":actualAff===null?"회심 입력 필요":physicalIndex(raw,actualAff,chosenFactor).toFixed(2),!sharpnessApplicable?"거너: 예리도 미적용":"선택한 예리도를 계속 유지한다고 가정");
  metric("공격 계열 후보",String(candidates.length)+"건",candidates.length>1?"회심·방어 입력 시 후보 축소 가능":"확인된 데이터 기준");
  result.append(metrics);
  if(!candidates.length){text(result,"초기 계열을 확정할 근거가 없습니다. 수치·강화 단계·스킬/도핑 보정 여부를 확인해 주세요. 일부 중간 강화 데이터는 미확인입니다.","rp-caution")}
  else{
   const cards=node("div","rp-candidate-list");
   for(const c of candidates){
    const card=node("article","rp-candidate");
    card.append(node("strong",null,"초기 "+c.base+" 계열"+(c.bonus?" · 추가 보정 +"+c.bonus:"")));
    const current=node("p",null,"현재 공격배율 "+c.raw+" · 회심 "+(c.affinity??"미확인")+"% · 방어 "+(c.defense??"미확인"));card.append(current);
    const lastLine=node("p",null,"Lv4 예상 표시 공격력 "+(c.finalDisplay??"미확인")+" · 회심 "+(c.finalAffinity===null?"미확인":c.finalAffinity+"%")+" · 방어 "+(c.finalDefense===null?"미확인":c.finalDefense));
    card.append(lastLine);
    if(c.finalRaw!==null&&c.finalAffinity!==null){
     const fin=physicalIndex(c.finalRaw,c.finalAffinity,chosenFactor??1);
     const start=Number.isFinite(actualAff)?physicalIndex(raw,actualAff,chosenFactor??1):null;
     card.append(node("p","rp-gain","Lv4 회심 반영 지표 "+fin.toFixed(2)+(start!==null?" · 현재 대비 "+(fin-start>=0?"+":"")+(fin-start).toFixed(2):"")));
    }
    if(c.uncertain)text(card,"강화 단계의 회심·방어 수치 일부 미검증","rr-note");
    cards.append(card)
   }
   result.append(cards);
  }
  const tips=node("div","rp-tips"),heading=node("h3",null,"이 무기에서 중요한 점");tips.append(heading);
  text(tips,profile.focus);
  if(sharpnessApplicable&&sharp?.needsHandicraft)text(tips,"선택한 보라 예리도는 장인 적용을 가정했어. 장인 없이 사용할 때는 이 예리도 지표가 적용되지 않아.");
  if(sharpnessApplicable&&sharp?.color==="purple")text(tips,"보라 유지 중에만 해당 배율을 적용. 실제 예리도 소모를 고려하지 않아.");
  if(state.slots==="empty3")text(tips,"빈 슬롯 3개는 스킬 구성의 유연성이 큰 장점이야. 공격 지표에는 더하지 않았어.");
  else if(state.slots==="fixed")text(tips,"고정 장식주는 슬롯의 스킬 효과를 확인해야 해. 빈 슬롯 3개와 동일하게 평가할 수 없어.");
  for(const f of profile.fields||[]){const value=state.special[type+"-"+f.id];if(value&&value!=="unknown"&&profile.interpretations?.[value])text(tips,profile.interpretations[value]);}
  if(state.element)text(tips,"속성·상태이상 "+state.element+"은 입력 메모로만 사용해. 속성 육질·무기 모션·각성 여부가 없으므로 물리 지표에 더하지 않았어.");
  result.append(tips);
  text(result,"계산은 무기 자체 진공격력·회심·지정 예리도만 사용하며, 스킬/부적/도핑·속성육질·포격·병·탄·사격보정·모션값은 제외. 서로 다른 무기종 지표를 직접 비교하지 마세요.");
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
  state.sharp=p.sharp||"unknown";state.element=p.element||"";state.slots=item.slotMode==="empty"?({0:"none",1:"empty1",2:"empty2",3:"empty3"}[item.slots]||"unknown"):item.slotMode==="fixed"?"fixed":"unknown";
  state.fixedDecorationId=item.decorationId||"";state[nameKey]=p.name||"";
  state.special={...state.special,...(p.special||{})};
  render(d,type,guide,host,decorations);
 };
 discard.onclick=()=>{state.editingId="";state.attack="";state.affinity="";state.defense="";state.level="1";state.sharp="unknown";state.slots="unknown";state.element="";state.fixedDecorationId="";state[nameKey]="";render(d,type,guide,host,decorations)};
 save.onclick=()=>{
  const shown=Number(state.attack),lv=Number(state.level);
  const affinity=state.affinity.trim()===""?null:Number(state.affinity),defense=state.defense.trim()===""?null:Number(state.defense);
  if(!Number.isInteger(shown)||shown<=0||!Number.isInteger(lv)||lv<1||lv>4){status.textContent="공격력과 강화 단계를 먼저 입력하세요.";return}
  if(affinity!==null&&(!Number.isInteger(affinity)||affinity< -100||affinity>100)){status.textContent="회심률 입력을 확인하세요.";return}
  if(defense!==null&&(!Number.isInteger(defense)||defense<0)){status.textContent="방어력 입력을 확인하세요.";return}
  const slot=state.slots,mode=slot==="fixed"?"fixed":slot==="unknown"?"unknown":"empty",slots=slot==="fixed"?Number(fixedList.find(x=>x.id===state.fixedDecorationId)?.slots||0):slot==="unknown"?0:slot==="none"?0:Number(slot.replace("empty",""));
  if(mode==="fixed"&&!fixedList.some(x=>x.id===state.fixedDecorationId)){status.textContent="고정 장식주가 있는 무기는 실제 장식주 종류를 선택해야 시뮬레이터에 적용할 수 있습니다. 선택하지 않아도 미확인으로 저장됩니다.";}
  const deco=fixedList.find(x=>x.id===state.fixedDecorationId),confirmed=mode!=="fixed"||!!deco;
  const p={weaponType:type,name:state[nameKey]||"",level:lv,attack:shown,affinity,defense,sharp:state.sharp,element:state.element,special:{...state.special}};
  const record={id:state.editingId||"relic_perf_"+Date.now()+"_"+Math.random().toString(36).slice(2,8),slotMode:!confirmed?"unknown":mode,slots:!confirmed?0:slots,decorationId:confirmed&&mode==="fixed"?deco.id:"",skills:confirmed&&mode==="fixed"?{...deco.skills}:{},performance:p};
  const all=records(),idx=all.findIndex(x=>x.id===record.id),dup=idx<0?all.findIndex(x=>x.performance&&signature(x)===signature(record)):-1;
  if(idx>=0)all[idx]=record;else if(dup>=0){record.id=all[dup].id;all[dup]=record}else all.push(record);
  try{localStorage.setItem(STORE,JSON.stringify(all))}catch(e){status.textContent="로컬 저장 실패: "+e.message;return}
  state.editingId=record.id;status.textContent="보유 발굴무기 목록에 저장됨"+(record.slotMode==="unknown"?" · 슬롯 정보 미확인으로 스킬조합 제외":"");
  document.dispatchEvent(new CustomEvent("mh4g-owned-relic-weapons-changed"));
  refreshOwned();
 };
 refreshOwned();
 run.onclick=calculate;if(state.attack)calculate();
}
export async function mountRelicPerformance(d,type,decorations=[]){
 const id=++sequence;const host=document.querySelector("#relicPanel-attack > .panel");if(!host)return;
 try{
  if(!loading)loading=fetch("./data/relic_performance_guide.json?v=0.7.7-relic-performance45",{cache:"no-cache"}).then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()}).then(v=>{loaded=v;return v}).catch(e=>{loading=null;throw e});
  const guide=loaded||await loading;
  if(id!==sequence||!host.isConnected)return;
  render(d,type,guide,host,decorations);
 }catch(e){if(id!==sequence||!host.isConnected)return;host.append(node("p","rp-caution","성능 분석 자료를 불러오지 못했습니다: "+e.message))}
}
