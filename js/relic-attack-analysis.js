
let last={attack:"",affinity:"",defense:"",level:"1",kind:"none",activation:"normal",value:"",sharp:"unknown",slots:"0",slotMode:"unknown",fixed:""};
let rulesPromise=null,mountSequence=0;
const create=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n};
const wrap=(name,control)=>{const label=create("label","rp-field");label.append(create("span",null,name),control);return label};
const numberField=(key,hint)=>{const el=create("input");el.type="number";el.inputMode="numeric";el.step="1";el.min=key==="affinity"?"-100":key==="defense"?"0":"0";el.placeholder=hint||"";el.value=last[key]??"";el.oninput=()=>{last[key]=el.value};return el};
const selectField=(key,opts)=>{const el=create("select");for(const [value,label] of opts){const op=create("option",null,label);op.value=String(value);op.selected=String(value)===last[key];el.append(op)}el.onchange=()=>{last[key]=el.value};return el};
const sourceLink=(label,url)=>{const a=create("a",null,label);a.href=url;a.target="_blank";a.rel="noopener noreferrer";return a};
async function loadRules(){
 if(!rulesPromise)rulesPromise=fetch("./data/relic_weapon_traits.json?v=0.7.7-relic-traits3b",{cache:"no-cache"})
  .then(r=>{if(!r.ok)throw Error("HTTP "+r.status);return r.json()})
  .then(d=>{if(!Array.isArray(d.weaponGroups)||!Array.isArray(d.sharpnessTypes))throw Error("검증 DB 형식 오류");return d})
  .catch(err=>{rulesPromise=null;throw err});
 return rulesPromise;
}
export function validateRelicTrait(rules,type,pick){
 const info=rules.weaponGroups.find(g=>g.names.includes(type));
 const result={status:"unknown",messages:[],allowed:[],kind:pick.kind,slotStatus:"unknown"};
 const kind=pick.kind||"none",num=Number(pick.value),activation=pick.activation||"normal";
 const isGunner=rules.gunnerUnverified.includes(type),isStatus=["poison","paralysis","sleep","blast"].includes(kind);
 if(isGunner){result.messages.push("보우건은 탄종·장전·반동 판별이 우선이며, 근접·활 속성치 테이블을 적용하지 않습니다.");}
 else if(kind==="none"){result.messages.push("무속성으로 입력했습니다. 속성·상태이상 수치 검사는 건너뜁니다.");result.status="compatible"}
 else if(!info){result.messages.push("이 무기종의 속성 수치 DB가 없어 판정할 수 없습니다.");}
 else if(!["fire","water","thunder","ice","dragon","poison","paralysis","sleep","blast"].includes(kind)){result.messages.push("지원되지 않는 속성·상태이상 유형입니다.");result.status="mismatch"}
 else if(type==="활"&&isStatus){result.messages.push("활에는 이 상태이상치 표를 적용하지 않습니다. 병 종류는 무기별 특수 성능 판별이 필요합니다.");result.status="mismatch"}
 else{
  const values=info[(activation==="awakened"?"awakened":"normal")+(isStatus?"Status":"Element")]||[];
  result.allowed=values;
  if(pick.value===""||pick.value===null||pick.value===undefined){result.status="unknown";result.messages.push("수치를 입력하면 해당 무기군의 허용 목록과 대조할 수 있습니다.");}
  else if(!Number.isInteger(num)||num<=0){result.status="mismatch";result.messages.push("수치는 0보다 큰 정수여야 합니다.");}
  else if(values.includes(num)){result.status="compatible";result.messages.push("참고 자료의 "+(activation==="awakened"?"각성 필요":"일반 발현")+" "+(isStatus?"상태이상":"속성")+" 수치 목록과 일치합니다.");}
  else{result.status="mismatch";result.messages.push("선택한 무기군·각성 조건의 수치 목록에 없습니다. 무기종과 각성 여부를 다시 확인하세요.");}
 }
 const mode=pick.slotMode||"unknown",slots=Number(pick.slots);
 if(!Number.isInteger(slots)||slots<0||slots>3){result.slotStatus="mismatch";result.messages.push("슬롯은 0~3 범위에서 선택해야 합니다.");}
 else if(mode==="fixed"&&slots===0){result.slotStatus="mismatch";result.messages.push("고정 장식주는 1~3슬롯에서만 선택할 수 있습니다.");}
 else if(mode==="fixed"&&!pick.fixed){result.slotStatus="unknown";result.messages.push("고정 장식주를 선택하세요.");}
 else if(mode==="fixed"){result.slotStatus="compatible";result.messages.push("장식주 후보의 무기군과 슬롯 크기를 대조해야 합니다. 개별 조합 출현 가능성을 확정한 것은 아닙니다.");}
 else if(mode==="empty"){result.slotStatus="compatible";result.messages.push(slots===0?"슬롯 0개(장식주 없음)로 기록했습니다.":"빈 슬롯 "+slots+"개로 기록했습니다. 고정 장식주가 선택된 상태는 아닙니다.");}
 else result.messages.push("슬롯 상태가 미확인이라 슬롯 적합성은 판정하지 않습니다.");
 return result;
}
export function analyzeRelicAttack(d,type,lv,shown,aff=NaN,def=NaN){
 const tbl=d.weaponAttackTables?.find(x=>x.weaponType===type),seqs=d.attackProgression;
 if(!tbl||!seqs||!Number.isFinite(shown)||shown<=0)return {raw:null,candidates:[]};
 const inf=shown/tbl.displayMultiplier,rule=seqs.bonusRules?.[type],matches=[];
 for(const [base,levels] of Object.entries(seqs.stages)){
  const at=lv-1,r=levels.raw[at],a=levels.affinity[at],df=levels.defense[at];
  for(const bonus of rule?.increments||[0]){
   if(r===null||r===undefined)continue;
   const raw=r+(rule?.key==="raw"?bonus:0),affinity=a===null?null:a+(rule?.key==="affinity"?bonus:0),defense=df===null?null:df+(rule?.key==="defense"?bonus:0);
   if(Math.abs(shown-Math.round(raw*tbl.displayMultiplier))>0.001)continue;
   if(Number.isFinite(aff)&&affinity!==null&&aff!==affinity)continue;
   if(Number.isFinite(def)&&defense!==null&&def!==defense)continue;
   matches.push({base,bonus,raw,affinity,defense,uncertain:affinity===null||defense===null});
  }
 }
 return {raw:inf,candidates:matches};
}
function fixedCandidates(decos,rules,type,slot){
 const gunner=["라이트보우건","헤비보우건","활"].includes(type);
 return (decos||[]).filter(x=>x.fixedDecoration&&x.relicOnly&&Number(x.slots)===slot).filter(x=>{
  if(gunner)return !rules.blademasterOnlyPrefixes.some(v=>x.name.startsWith(v));
  return !rules.gunnerOnlyPrefixes.some(v=>x.name.startsWith(v));
 });
}
function build(d,type,decorations,rules,host){
 const previousOpen=Boolean(host.querySelector(".rp-extra")?.open);
 host.querySelector("#relicAttackAdvanced")?.remove();
 const panel=create("section","panel rp-panel");panel.id="relicAttackAdvanced";
 const heading=create("div","rr-heading");heading.append(create("span","rr-step","성능 판별 · STEP 1~3"),create("h2",null,"공격력·강화·발굴 옵션 검증"),create("p","rr-note","공격력·회심·방어로 계열을 찾은 다음, 예리도·속성·슬롯·장식주를 원문 허용 목록과 비교합니다."));panel.append(heading);
 const fields=create("div","rp-fields"),lv=selectField("level",[["1","Lv1 미강화"],["2","Lv2"],["3","Lv3"],["4","Lv4 최종"]]),attack=numberField("attack","예: 대검 1728"),aff=numberField("affinity","선택"),def=numberField("defense","선택");
 fields.append(wrap("강화 단계",lv),wrap("표시 공격력",attack),wrap("회심률 (%)",aff),wrap("방어 보너스",def));panel.append(fields);
 const attackRun=create("button","rp-run","공격력 계열 판별"),attackOut=create("div","rp-results");
 panel.append(attackRun,attackOut);
 const more=create("details","rp-extra");more.open=previousOpen;
 more.append(create("summary",null,"STEP 3 · 예리도·속성·슬롯·고정 장식주 판별"));
 const sf=create("div","rp-fields");
 const blademaster= !["라이트보우건","헤비보우건","활"].includes(type);
 const sharp=selectField("sharp",rules.sharpnessTypes.map(x=>[x.id,x.label]));
 const kind=selectField("kind",rules.attributeKinds.filter(x=>type!=="활"||!["poison","paralysis","sleep","blast"].includes(x[0])));
 const awaken=selectField("activation",[["normal","일반 발현"],["awakened","각성 필요"]]);
 const value=numberField("value","속성·상태이상 수치"),slots=selectField("slots",[["0","0"],["1","1"],["2","2"],["3","3"]]);
 const mode=selectField("slotMode",rules.slotModes);
 const deco=create("select");deco.setAttribute("aria-label","발굴무기 고정 장식주");
 sf.append(wrap("예리도 패턴",sharp),wrap("속성·상태이상 종류",kind),wrap("발현 유형",awaken),wrap("속성·상태이상 수치",value),wrap("슬롯 수",slots),wrap("슬롯 상태",mode));
 more.append(sf);
 const decoField=wrap("고정 장식주 · 보유 슬롯 조건의 DB 후보",deco);decoField.classList.add("rp-deco");
 more.append(decoField);
 const optionInfo=create("p","rr-note");
 const detailOut=create("div","rp-results"),detailRun=create("button","rp-run","부가 옵션 검증");
 more.append(optionInfo,detailRun,detailOut);panel.append(more);
 const reference=create("details","rp-reference");reference.append(create("summary",null,"기존 공격력·강화 상세표 펼쳐보기"));
 for(const tbl of host.querySelectorAll(".table-panel")){tbl.classList.add("rp-reference-table");reference.append(tbl)}
 panel.append(reference);
 const old=host.querySelector(".relic-attack-check");if(old)old.hidden=true;
 host.insertBefore(panel,old??host.querySelector(".relic-attack-summary")?.nextSibling??null);
 const gunner=["라이트보우건","헤비보우건"].includes(type);
 function updateControls(){
  if(type==="활"&&["poison","paralysis","sleep","blast"].includes(kind.value)){kind.value="none";last.kind="none"}
  if(!blademaster){sharp.value="unknown";last.sharp="unknown"}
  sharp.disabled=!blademaster;
  kind.disabled=gunner;awaken.disabled=gunner||kind.value==="none";value.disabled=gunner||kind.value==="none";
  const usesFixed=mode.value==="fixed",n=Number(slots.value);
  deco.disabled=!usesFixed||n===0;
  const items=usesFixed?fixedCandidates(decorations,rules,type,n):[];
  const current=last.fixed;
  deco.replaceChildren();
  const empty=create("option",null,usesFixed?"선택 안 함":"고정 장식주 없음");empty.value="";deco.append(empty);
  for(const x of items){const op=create("option",null,x.name);op.value=x.id;deco.append(op)}
  deco.value=items.some(x=>x.id===current)?current:"";last.fixed=deco.value;
  optionInfo.textContent=gunner?"보우건의 탄·반동·장전과 속성탄 조합은 STEP 4 무기종 전용 판별에서 다룹니다."
   :type==="활"?"활은 일반/각성 속성치만 수치 검사합니다. 병·곡사·강사는 STEP 4에서 다룹니다."
   :kind.value==="none"?"속성 없음으로 선택했습니다. 유형을 바꾸면 무기종별 출현 수치 목록을 표시합니다."
   :"선택한 무기군의 출현 수치 목록과 각성 필요 여부를 각각 대조합니다.";
 }
 kind.addEventListener("change",updateControls);mode.addEventListener("change",()=>{last.fixed="";updateControls()});slots.addEventListener("change",()=>{last.fixed="";updateControls()});
 deco.onchange=()=>{last.fixed=deco.value};
 updateControls();
 function attackResult(){
  attackOut.replaceChildren();
  if(attack.value===""||Number(attack.value)<=0||!Number.isInteger(Number(attack.value))){attackOut.append(create("p","rp-caution","게임 내 무기 자체의 표시 공격력을 정수로 입력하세요."));return}
  const a=aff.value===""?NaN:Number(aff.value),f=def.value===""?NaN:Number(def.value);
  const result=analyzeRelicAttack(d,type,Number(lv.value),Number(attack.value),a,f);
  attackOut.append(create("p","rr-note","역산 무기배율 "+(result.raw?.toFixed(2)??"미확인")+" · Lv"+lv.value+" · 후보 "+result.candidates.length+"건"));
  if(!result.candidates.length){attackOut.append(create("p","rp-caution","현재 DB에서 일치하는 공격력 계열이 없습니다. 강화 단계·무기 자체 공격력을 확인하세요. 일부 중간 강화 수치는 미확인이며 '불가능한 무기'라고 단정하지 않습니다."));return}
  for(const x of result.candidates){
   const card=create("div","rp-candidate");
   card.append(create("strong",null,"초기 기본배율 "+x.base+" 계열"+(x.bonus?" · 추가 보정 +"+x.bonus:"")),create("span",null,"현재 배율 "+x.raw+" · 회심 "+(x.affinity===null?"미확인":x.affinity+"%")+" · 방어 "+(x.defense===null?"미확인":"+"+x.defense)));
   if(x.uncertain)card.append(create("small",null,"현재 강화 단계 수치 일부가 미확인입니다."));
   attackOut.append(card);
  }
  if(result.candidates.length>1)attackOut.append(create("p","rr-note","회심률·방어력까지 입력하면 중복 후보를 좁힐 수 있습니다."));
 }
 function traitResult(){
  detailOut.replaceChildren();
  const pick={kind:kind.value,activation:awaken.value,value:value.value,slots:slots.value,slotMode:mode.value,fixed:deco.value};
  const v=validateRelicTrait(rules,type,pick);
  const head=create("div","rp-verdict");
  head.append(create("strong",null,"속성 수치: "+(v.status==="compatible"?"자료 목록과 일치":v.status==="mismatch"?"입력값 불일치":"판정 보류")),create("span",null,"슬롯·장식주: "+(v.slotStatus==="compatible"?"입력 조건 일치":v.slotStatus==="mismatch"?"입력 오류":"추가 확인 필요")));
  detailOut.append(head);
  const selectedSharp=rules.sharpnessTypes.find(x=>x.id===sharp.value);
  if(blademaster&&selectedSharp&&selectedSharp.id!=="unknown")detailOut.append(create("p","rr-note","예리도 "+selectedSharp.label+" · "+selectedSharp.note+" · 실제 공격 계열별 결합은 전수 확인되지 않았습니다."));
  if(!blademaster)detailOut.append(create("p","rr-note","이 무기종에는 근접 예리도 선택을 적용하지 않습니다."));
  if(v.allowed.length)detailOut.append(create("p","rr-note","허용 수치: "+v.allowed.join(" · ")));
  for(const msg of v.messages)detailOut.append(create("p",v.status==="mismatch"||v.slotStatus==="mismatch"?"rp-caution":"rr-note",msg));
  if(mode.value==="fixed"&&deco.value){
   const chosen=(decorations||[]).find(x=>x.id===deco.value);
   const okay=fixedCandidates(decorations,rules,type,Number(slots.value)).some(x=>x.id===deco.value);
   detailOut.append(create("p",okay?"rr-note":"rp-caution",chosen?(chosen.name+" · "+(okay?"현재 무기군·슬롯 크기의 등록 후보":"슬롯 크기·무기군 조건에 불일치")):"장식주 정보를 확인할 수 없습니다."));
  }
  detailOut.append(create("p","rr-note","이 검증은 각 항목의 원문 등재 여부 확인이며, 공격 계열·예리도·속성·장식주가 모두 동시에 나올 수 있음을 보장하지 않습니다."));
 }
 attackRun.onclick=attackResult;detailRun.onclick=traitResult;
 if(last.attack)attackResult();
}
export async function mountRelicAttack(d,type,decorations){
 const id=++mountSequence;
 const host=document.querySelector("#relicPanel-attack > .panel");
 if(!host)return;
 try{
  const rules=await loadRules();
  if(id!==mountSequence||!host.isConnected)return;
  build(d,type,decorations,rules,host);
 }catch(e){
  if(id!==mountSequence||!host.isConnected)return;
  let p=host.querySelector(".rp-error");if(!p){p=create("p","rp-caution rp-error");host.append(p)}
  p.textContent="성능 옵션 DB 로드 실패: "+e.message;
 }
}
