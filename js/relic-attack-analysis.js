
let lastValues={attack:"",affinity:"",defense:"",level:"1",element:"",status:"",sharp:"unknown",slots:"0",fixed:""};
const el=(tag,cls,text)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x};
const field=(title,x)=>{const l=el("label","rp-field");l.append(el("span",null,title),x);return l};
const input=(key,type="number")=>{const x=el("input");x.type=type;x.value=lastValues[key]??"";x.oninput=()=>{lastValues[key]=x.value};return x};
const sel=(key,options)=>{const x=el("select");for(const [v,t] of options){const o=el("option",null,t);o.value=v;o.selected=v===String(lastValues[key]);x.append(o)}x.onchange=()=>{lastValues[key]=x.value};return x};
function getCandidates(d,type,level,shown,aff,def){
 const table=d.weaponAttackTables.find(x=>x.weaponType===type);const meta=d.attackProgression;
 const raw=shown/table.displayMultiplier,rule=meta.bonusRules[type];
 const candidates=[];
 for(const [base,seq] of Object.entries(meta.stages)){
  const index=level-1,r=seq.raw[index],a=seq.affinity[index],f=seq.defense[index];
  const bonuses=rule?.increments??[0];
  for(const bonus of bonuses){
   const expectedRaw=r===null?null:r+(rule?.key==="raw"?bonus:0);
   const expectedA=a===null?null:a+(rule?.key==="affinity"?bonus:0);
   const expectedD=f===null?null:f+(rule?.key==="defense"?bonus:0);
   if(expectedRaw===null)continue;
   const attackDelta=Math.abs(shown-Math.round(expectedRaw*table.displayMultiplier));
   if(attackDelta>0.001)continue;
   if(Number.isFinite(aff)&&expectedA!==null&&aff!==expectedA)continue;
   if(Number.isFinite(def)&&expectedD!==null&&def!==expectedD)continue;
   candidates.push({base,bonus,raw:expectedRaw,aff:expectedA,def:expectedD,uncertain:expectedA===null||expectedD===null,display:Math.round(expectedRaw*table.displayMultiplier)});
  }
 }
 return {raw,candidates};
}
function mountPanel(d,type,host,decors){
 if(!host)return;
 const old=host.querySelector("#relicAttackAdvanced");
 if(old)old.remove();
 const panel=el("section","panel rp-panel");panel.id="relicAttackAdvanced";
 const title=el("div","rr-heading");title.append(el("span","rr-step","01~03 · 발굴무기 판별"),el("h2",null,"공격력·강화·옵션 종합 분석"),el("p","rr-note","표시 공격력과 무기 자체 회심·방어를 입력해 해당 강화 단계의 계열 후보를 좁힙니다. 스킬·부적·도핑이 적용된 상태창 공격력이 아니라 무기 자체 수치로 비교하세요."));panel.append(title);
 const controls=el("div","rp-fields");
 const lv=sel("level",[["1","Lv1 미강화"],["2","Lv2"],["3","Lv3"],["4","Lv4 최종"]]);
 const atk=input("attack"),aff=input("affinity"),def=input("defense");
 atk.min="1";atk.step="1";atk.placeholder="예: 대검 1728";
 aff.min="-100";aff.max="100";aff.step="1";aff.placeholder="무기 자체 수치";
 def.min="0";def.step="1";def.placeholder="무기 자체 수치";
 controls.append(field("강화 단계",lv),field("표시 공격력",atk),field("회심률 (%) · 선택",aff),field("방어 보너스 · 선택",def));panel.append(controls);
 const button=el("button","rp-run","무기 계열 판별");button.type="button";panel.append(button);
 const output=el("div","rp-results");panel.append(output);
 const extra=el("details","rp-extra");extra.append(el("summary",null,"STEP 3 · 예리도·속성·슬롯·고정 장식주 추가 판별"));
 const extraControls=el("div","rp-fields");
 const sharp=sel("sharp",d.attackProgression.sharpening.categories.map(x=>[x.id,x.label]));
 const elem=input("element"),status=input("status");
 const slots=sel("slots",[["0","0"],["1","1"],["2","2"],["3","3"]]);
 extraControls.append(field("예리도 유형",sharp),field("속성치 · 선택",elem),field("상태이상치 · 선택",status),field("슬롯 / 고정 장식 크기",slots));extra.append(extraControls);
 const decoWrap=el("div","rp-deco");const decoSelect=el("select");decoSelect.setAttribute("aria-label","발굴 고정 장식주");
 decoWrap.append(field("고정 장식주 · 해당 슬롯 후보",decoSelect));extra.append(decoWrap);
 const detailResult=el("div","rp-results");extra.append(detailResult);
 const detailBtn=el("button","rp-run","부가 옵션 검토");detailBtn.type="button";extra.append(detailBtn);
 panel.append(extra);
 const oldInput=host.querySelector(".relic-attack-check"),tables=host.querySelectorAll(".table-panel");
 if(oldInput)oldInput.hidden=true;for(const t of tables)t.classList.add("rp-reference-table");
 const reference=el("details","rp-reference");reference.append(el("summary",null,"기존 공격력·강화 표 보기"));for(const t of tables)reference.append(t);panel.append(reference);
 host.insertBefore(panel,oldInput??host.querySelector(".relic-attack-summary")?.nextSibling??null);
 function setDeco(){
  const slot=Number(slots.value),rows=(decors||[]).filter(x=>Number(x.slots)===slot&&x.fixedDecoration);
  decoSelect.replaceChildren();const empty=el("option",null,slot?"고정 장식주 선택 안 함":"슬롯 0 · 해당 없음");empty.value="";decoSelect.append(empty);
  for(const x of rows){const o=el("option",null,x.name);o.value=x.id;o.selected=x.id===lastValues.fixed;decoSelect.append(o)}
  if(!rows.some(x=>x.id===lastValues.fixed))lastValues.fixed="";
  decoSelect.value=lastValues.fixed;
  decoSelect.disabled=!slot||!rows.length;
 }
 slots.addEventListener("change",()=>{lastValues.fixed="";setDeco()});
 decoSelect.onchange=()=>{lastValues.fixed=decoSelect.value};
 setDeco();
 function renderResult(){
  output.replaceChildren();
  if(!atk.value||!Number.isFinite(Number(atk.value))||Number(atk.value)<=0){output.append(el("p","rr-note","표시 공격력을 입력하세요."));return}
  const a=aff.value.trim()===""?NaN:Number(aff.value),f=def.value.trim()===""?NaN:Number(def.value);
  const {raw,candidates}=getCandidates(d,type,Number(lv.value),Number(atk.value),a,f);
  output.append(el("p","rr-note","역산 무기배율 "+raw.toFixed(2)+" · 강화 Lv"+lv.value+" · 일치 후보 "+candidates.length+"건"));
  if(!candidates.length){output.append(el("p","rp-caution","현재 확인된 계열과 일치하지 않습니다. 강화 단계, 무기종, 무기 자체 공격력 및 회심 보정 여부를 확인하세요. Lv2~3 일부 계열의 원자료가 미확인이므로 '불가능한 무기'로 확정하지 않습니다."));return}
  for(const x of candidates){const card=el("div","rp-candidate");card.append(el("strong",null,"초기 "+x.base+" 계열"+(x.bonus?" · 추가 보정 +"+x.bonus:"")),el("span",null,"현재 배율 "+x.raw+" · 회심 "+(x.aff===null?"미확인":x.aff+"%")+" · 방어 "+(x.def===null?"미확인":"+"+x.def)));if(x.uncertain)card.append(el("small",null,"현재 강화 단계의 일부 수치는 원자료 미확인"));output.append(card)}
  if(candidates.length>1)output.append(el("p","rr-note","복수 후보입니다. 회심률·방어 보너스를 입력하면 더 좁힐 수 있습니다."));
 }
 function renderDetails(){
  detailResult.replaceChildren();const cap=d.elementCaps?.[type],value=Number(elem.value),st=Number(status.value);
  const sharpInfo=d.attackProgression.sharpening.categories.find(x=>x.id===sharp.value);
  if(sharpInfo?.id!=="unknown")detailResult.append(el("p","rr-note","예리도: "+sharpInfo.label+" · "+sharpInfo.note));
  if(elem.value)detailResult.append(el("p","rr-note","속성 "+elem.value+" · 기존 DB 참고 상한: "+(cap?.element??"무기종별 상한 자료 없음")+" · 세부 출현 조합 판정 미완료"));
  if(status.value)detailResult.append(el("p","rr-note","상태이상 "+status.value+" · 기존 DB 참고 상한: "+(cap?.status??"무기종별 상한 자료 없음")+" · 세부 출현 조합 판정 미완료"));
  const deco=(decors||[]).find(x=>x.id===decoSelect.value);
  detailResult.append(el("p","rr-note","슬롯 "+slots.value+" · "+(deco?deco.name:"고정 장식주 선택 안 함")+" · 실제 출현 가능한 조합의 전수검증이 완료되지 않아 적합성은 확정하지 않습니다."));
 }
 button.onclick=renderResult;detailBtn.onclick=renderDetails;
 if(lastValues.attack)renderResult();
}
export function mountRelicAttack(d,type,decors){
 const panel=document.getElementById("relicPanel-attack");
 if(!panel)return;
 const host=panel.querySelector(".panel");
 if(!host)return;
 mountPanel(d,type,host,decors);
}
