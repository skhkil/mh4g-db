
export const PARTS = ["head","body","arms","waist","legs"];
export const PART_NAMES = {head:"머리",body:"몸통",arms:"팔",waist:"허리",legs:"다리"};

export function slotsText(n=0){
  n = Math.max(0, Math.min(3, Number(n)||0));
  return "O".repeat(n) + "-".repeat(3-n);
}

export function skillMapAdd(target, source, mul=1){
  if(!source) return target;
  for(const [k,v] of Object.entries(source)){
    target[k] = (target[k] || 0) + Number(v || 0) * mul;
  }
  return target;
}

export function getSkillDefinition(skills, id){
  return skills.find(s => s.id === id) || null;
}

export function getActivatedSkills(points, skills){
  const result = [];
  for(const [skillId, value] of Object.entries(points)){
    const def = getSkillDefinition(skills, skillId);
    if(!def) continue;
    const activations = [...(def.activations || [])].sort((a,b)=>Number(a.points)-Number(b.points));
    let active = null;
    if(value >= 0){
      for(const a of activations){
        if(Number(a.points) > 0 && value >= Number(a.points)) active = a;
      }
    } else {
      const negatives = activations.filter(a=>Number(a.points)<0).sort((a,b)=>Number(b.points)-Number(a.points));
      for(const a of negatives){
        if(value <= Number(a.points)) active = a;
      }
    }
    if(active) result.push({skillId, points:value, name:active.name, threshold:Number(active.points)});
  }
  return result.sort((a,b)=>b.threshold-a.threshold);
}

export function baseBuildPoints(armors, charm, includeTorsoUp=true){
  const points = {};
  const body = armors.find(a=>a?.part==="body");
  const other = armors.filter(a=>a && a.part!=="body");
  const torsoUpCount = includeTorsoUp ? other.filter(a=>a.torsoUp).length : 0;

  for(const armor of other){
    if(!armor.torsoUp) skillMapAdd(points, armor.skills);
    else if(armor.skills) skillMapAdd(points, armor.skills);
  }
  if(body) skillMapAdd(points, body.skills, 1 + torsoUpCount);
  skillMapAdd(points, charm?.skills);
  return {points, torsoUpCount};
}

export function containersForBuild(armors, charmSlots=0, weaponSlots=0){
  const containers = [{id:"weapon",label:"무기",capacity:Number(weaponSlots)||0}];
  for(const p of PARTS){
    const a = armors.find(x=>x?.part===p);
    containers.push({id:p,label:PART_NAMES[p],capacity:Number(a?.slots)||0});
  }
  containers.push({id:"charm",label:"호석",capacity:Number(charmSlots)||0});
  return containers;
}

export function applyDecoration(points, deco, multiplier=1){
  return skillMapAdd(points, deco.skills, multiplier);
}

export function calculateBuild({armors=[], charm={skills:{},slots:0}, weaponSlots=0, decorations=[]}, data, includeTorsoUp=true){
  const {points, torsoUpCount} = baseBuildPoints(armors, charm, includeTorsoUp);
  for(const placed of decorations){
    const deco = typeof placed.deco === "string"
      ? data.decorations.find(d=>d.id===placed.deco)
      : placed.deco;
    if(!deco) continue;
    const mult = placed.container==="body" ? (1 + torsoUpCount) : 1;
    applyDecoration(points, deco, mult);
  }
  const defense = armors.reduce((s,a)=>s+Number(a?.defense||0),0);
  const resist = {fire:0,water:0,thunder:0,ice:0,dragon:0};
  for(const a of armors){
    for(const k of Object.keys(resist)) resist[k]+=Number(a?.resistances?.[k]||0);
  }
  return {points, activated:getActivatedSkills(points,data.skills), defense, resist, torsoUpCount};
}

function requirementMap(targetActivationIds, skills){
  const req = {};
  for(const activationId of targetActivationIds){
    for(const s of skills){
      const a = (s.activations||[]).find(x=>x.id===activationId);
      if(a && Number(a.points)>0){
        req[s.id] = Math.max(req[s.id]||0, Number(a.points));
      }
    }
  }
  return req;
}


const RANK_ORDER={low:0,high:1,g:2};
function progressionRankAllows(armorRank, progression){
  if(progression==="all"||!progression) return true;
  const armor=RANK_ORDER[armorRank];
  const max=RANK_ORDER[progression];
  return Number.isFinite(armor)&&Number.isFinite(max)&&armor<=max;
}

function compareArmorGenerationTie(a,b,progression){
  const max=RANK_ORDER[progression];
  if(!Number.isFinite(max))return 0;
  const ad=max-(RANK_ORDER[a?.rank]??0),bd=max-(RANK_ORDER[b?.rank]??0);
  return ad-bd||Number(b?.defense||0)-Number(a?.defense||0)||String(a?.id||"").localeCompare(String(b?.id||""));
}

function targetRequirementsSatisfied(points, req){
  return Object.entries(req).every(([id,need])=>Number(points?.[id]||0)>=Number(need||0));
}

function deficitScore(points, req){
  let miss=0, hit=0;
  for(const [id,need] of Object.entries(req)){
    const have=Number(points[id]||0);
    miss += Math.max(0, need-have);
    hit += Math.min(need, Math.max(0,have));
  }
  return {miss,hit};
}

function armorScore(a, req){
  let s = Number(a.slots||0)*0.65;
  const entries=Object.entries(req||{}).filter(([,need])=>Number(need)>0);
  for(const [id,need] of entries){
    const v = Number(a.skills?.[id]||0);
    if(v>0) s += Math.min(v,need)*2.2;
    if(v<0) s += v*0.35;
  }
  // 몸통배가는 아직 채워야 할 목표 스킬이 있을 때만 후보 생성에 가점을 준다.
  // 호석/발굴무기만으로 목표가 완성된 경우 불필요한 몸통배가 세트가 빔을 점유하는 것을 막는다.
  if(a.torsoUp && entries.length) s += 4;
  return s;
}

function buildSignature(items){
  return PARTS.map(p=>items.find(a=>a?.part===p)?.id||"-").join("|");
}

function decorationBurden(placements=[]){
  let usedSlots=0;
  const types=new Set();
  for(const placed of placements){
    const deco=placed?.deco;
    usedSlots+=Number((typeof deco==="object"?deco?.slots:0)||0);
    const id=typeof deco==="string"?deco:deco?.id;
    if(id)types.add(id);
  }
  return {decorationCount:placements.length,usedDecorationSlots:usedSlots,distinctDecorationTypes:types.size};
}

function negativeSkillBurden(calc){
  const negative=(calc?.activated||[]).filter(a=>Number(a.threshold)<0);
  return {
    negativeSkillCount:negative.length,
    negativeSkillSeverity:negative.reduce((sum,a)=>sum+Math.abs(Number(a.threshold)||0),0)
  };
}

function targetPointEfficiency(calc,req,skills){
  let targetWastePoints=0,targetUpgradeSteps=0;
  for(const [skillId,needRaw] of Object.entries(req)){
    const need=Number(needRaw)||0;
    const have=Number(calc?.points?.[skillId]||0);
    const def=getSkillDefinition(skills,skillId);
    const thresholds=(def?.activations||[]).map(a=>Number(a.points)).filter(v=>v>0).sort((a,b)=>a-b);
    const reached=thresholds.filter(v=>v<=have).at(-1)??need;
    targetWastePoints+=Math.max(0,have-reached);
    targetUpgradeSteps+=thresholds.filter(v=>v>need&&v<=have).length;
  }
  const targetIds=new Set(Object.keys(req));
  const extraPositiveSkillCount=(calc?.activated||[]).filter(a=>Number(a.threshold)>0&&!targetIds.has(a.skillId)).length;
  return {targetWastePoints,targetUpgradeSteps,extraPositiveSkillCount};
}

function preferredSkillMetrics(calc,preferredSkillWeights={}){
  const active=new Set((calc?.activated||[]).filter(a=>Number(a.threshold)>0).map(a=>a.skillId));
  let preferredSkillScore=0,preferredSkillCount=0;
  for(const [id,w] of Object.entries(preferredSkillWeights||{}))if(active.has(id)){preferredSkillScore+=Number(w)||0;preferredSkillCount+=1}
  return {preferredSkillScore,preferredSkillCount};
}

function residualCompletionPotential(calc,req,skills,decorations,freeSlots=0){
  const slots=Math.max(0,Number(freeSlots||0));
  if(slots<=0)return {count:0,score:0};
  const targetIds=new Set(Object.keys(req||{}));
  let count=0,score=0;
  for(const skill of skills||[]){
    if(targetIds.has(skill.id))continue;
    const have=Number(calc?.points?.[skill.id]||0);
    const next=(skill.activations||[]).map(a=>Number(a.points)).filter(v=>v>0&&v>have).sort((a,b)=>a-b)[0];
    if(!Number.isFinite(next))continue;
    const need=next-have;
    let minSlots=Infinity;
    for(const d of decorations||[]){
      const gain=Math.max(0,Number(d?.skills?.[skill.id]||0));
      const ds=Math.max(1,Number(d?.slots||0));
      if(!gain)continue;
      minSlots=Math.min(minSlots,Math.ceil(need/gain)*ds);
    }
    if(minSlots<=slots){count+=1;score+=Math.max(1,slots-minSlots+1);}
  }
  return {count,score};
}

function practicalBuildMetrics(armors,progression,calc,containers,usedDecorationSlots){
  const max=Number.isFinite(RANK_ORDER[progression])?RANK_ORDER[progression]:RANK_ORDER.g;
  const downgrades=armors.map(a=>Math.max(0,max-(RANK_ORDER[a?.rank]??0)));
  const totalCapacity=(containers||[]).reduce((sum,c)=>sum+Number(c?.capacity||0),0);
  const resistValues=["fire","water","thunder","ice","dragon"].map(k=>Number(calc?.resist?.[k]||0));
  return {
    rankMaxDowngrade:downgrades.length?Math.max(...downgrades):0,
    rankTotalDowngrade:downgrades.reduce((a,b)=>a+b,0),
    currentRankPieces:downgrades.filter(x=>x===0).length,
    defense:Number(calc?.defense||0),
    resistanceTotal:resistValues.reduce((sum,v)=>sum+v,0),
    resistanceMinimum:resistValues.length?Math.min(...resistValues):0,
    remainingSlots:Math.max(0,totalCapacity-Number(usedDecorationSlots||0))
  };
}

function compareRankedMetrics(a,b){
  const am=a.metrics||{},bm=b.metrics||{};
  return (bm.preferredSkillScore||0)-(am.preferredSkillScore||0)
    ||(bm.preferredSkillCount||0)-(am.preferredSkillCount||0)
    ||(bm.extraPositiveSkillCount||0)-(am.extraPositiveSkillCount||0)
    ||(bm.targetUpgradeSteps||0)-(am.targetUpgradeSteps||0)
    ||(am.negativeSkillCount||0)-(bm.negativeSkillCount||0)
    ||(am.negativeSkillSeverity||0)-(bm.negativeSkillSeverity||0)
    ||(bm.remainingSlots||0)-(am.remainingSlots||0)
    ||(am.targetWastePoints||0)-(bm.targetWastePoints||0)
    ||(am.usedDecorationSlots||0)-(bm.usedDecorationSlots||0)
    ||(am.decorationCount||0)-(bm.decorationCount||0)
    ||(am.distinctDecorationTypes||0)-(bm.distinctDecorationTypes||0)
    ||(am.rankMaxDowngrade||0)-(bm.rankMaxDowngrade||0)
    ||(am.rankTotalDowngrade||0)-(bm.rankTotalDowngrade||0)
    ||(bm.defense||0)-(am.defense||0)
    ||(bm.resistanceTotal||0)-(am.resistanceTotal||0)
    ||(bm.resistanceMinimum||0)-(am.resistanceMinimum||0);
}

function compareRankedBuilds(a,b){
  return compareRankedMetrics(a,b)||buildSignature(a.armors).localeCompare(buildSignature(b.armors));
}

function diversifyExactTieGroups(sorted){
  const out=[];
  for(let i=0;i<sorted.length;){
    let j=i+1;
    while(j<sorted.length&&compareRankedMetrics(sorted[i],sorted[j])===0)j++;
    const group=sorted.slice(i,j);
    if(group.length<=2){out.push(...group);i=j;continue;}
    const chosen=[group.shift()];
    while(group.length){
      let bestIndex=0,bestDistance=-1;
      for(let k=0;k<group.length;k++){
        const sig=group[k].armors.map(a=>a?.id||"");
        const minDistance=Math.min(...chosen.map(c=>c.armors.reduce((n,a,idx)=>n+(a?.id!==sig[idx]?1:0),0)));
        if(minDistance>bestDistance){bestDistance=minDistance;bestIndex=k;}
      }
      chosen.push(group.splice(bestIndex,1)[0]);
    }
    out.push(...chosen);i=j;
  }
  return out;
}


function placeDecorationState(state, deco, containerId, bodyMultiplier, req){
  const next = {
    remaining:{...state.remaining},
    points:{...state.points},
    placements:[...state.placements,{deco,container:containerId}]
  };
  next.remaining[containerId] -= Number(deco.slots||0);
  skillMapAdd(next.points, deco.skills, containerId==="body" ? bodyMultiplier : 1);
  const ds=deficitScore(next.points,req);
  next.score = ds.hit*3 - ds.miss*8 + Object.values(next.remaining).reduce((a,b)=>a+b,0)*0.05;
  return next;
}

function solveDecorations(basePoints, containers, decorations, req, torsoUpCount, maxStates=2500){
  const already=deficitScore(basePoints,req);
  if(already.miss<=0) return {placements:[],points:{...basePoints},complete:true};

  const relevant = decorations
    .filter(d=>Number(d.slots)>=1 && Number(d.slots)<=3)
    .filter(d=>Object.keys(req).some(id=>Number(d.skills?.[id]||0)>0))
    .sort((a,b)=>{
      const av=Object.keys(req).reduce((s,id)=>s+Math.max(0,Number(a.skills?.[id]||0)),0)/Number(a.slots||1);
      const bv=Object.keys(req).reduce((s,id)=>s+Math.max(0,Number(b.skills?.[id]||0)),0)/Number(b.slots||1);
      return bv-av;
    })
    .slice(0,24);

  let states=[{
    remaining:Object.fromEntries(containers.map(c=>[c.id,Number(c.capacity||0)])),
    points:{...basePoints}, placements:[], score:-already.miss*8
  }];
  let best=null;
  let bestPartial=states[0];
  const maxSteps = Math.min(16, containers.reduce((s,c)=>s+Number(c.capacity||0),0));

  const betterPartial=(a,b)=>{
    if(!b)return true;
    const ad=deficitScore(a.points,req),bd=deficitScore(b.points,req);
    if(ad.miss!==bd.miss)return ad.miss<bd.miss;
    if(ad.hit!==bd.hit)return ad.hit>bd.hit;
    if(a.placements.length!==b.placements.length)return a.placements.length<b.placements.length;
    const ar=Object.values(a.remaining).reduce((x,y)=>x+Number(y||0),0);
    const br=Object.values(b.remaining).reduce((x,y)=>x+Number(y||0),0);
    return ar>br;
  };

  for(let step=0; step<maxSteps; step++){
    const expanded=[...states];
    for(const st of states){
      for(const deco of relevant){
        for(const c of containers){
          if(st.remaining[c.id] >= Number(deco.slots||0)){
            const ns=placeDecorationState(st,deco,c.id,1+torsoUpCount,req);
            if(betterPartial(ns,bestPartial))bestPartial=ns;
            if(deficitScore(ns.points,req).miss<=0){
              best=ns; break;
            }
            expanded.push(ns);
          }
        }
        if(best) break;
      }
      if(best) break;
    }
    if(best) break;

    const dedup=new Map();
    for(const st of expanded){
      const capped=Object.keys(req).map(k=>`${k}:${Math.min(req[k],st.points[k]||0)}`).join(",");
      const rem=Object.entries(st.remaining).map(([k,v])=>`${k}:${v}`).join(",");
      const key=capped+"|"+rem;
      if(!dedup.has(key) || dedup.get(key).score<st.score) dedup.set(key,st);
    }
    states=[...dedup.values()].sort((a,b)=>b.score-a.score).slice(0,maxStates);
    for(const st of states)if(betterPartial(st,bestPartial))bestPartial=st;
  }
  if(best)return {placements:best.placements,points:best.points,complete:true};
  return {placements:bestPartial?.placements||[],points:bestPartial?.points||{...basePoints},complete:false};
}


function requirementDeficits(points,req){
  return Object.entries(req).map(([skillId,needRaw])=>{
    const need=Number(needRaw)||0,have=Number(points?.[skillId]||0);
    return {skillId,need,have,missing:Math.max(0,need-have)};
  }).filter(x=>x.missing>0).sort((a,b)=>b.missing-a.missing||a.skillId.localeCompare(b.skillId));
}

function remainingContainersAfterPlacements(containers,placements=[]){
  const used={};
  for(const placed of placements){
    const id=placed?.container;if(!id)continue;
    const deco=placed?.deco;
    used[id]=(used[id]||0)+Number((typeof deco==="object"?deco?.slots:0)||0);
  }
  return (containers||[]).map(c=>({
    ...c,
    capacity:Math.max(0,Number(c?.capacity||0)-Number(used[c?.id]||0))
  }));
}

function virtualExtraSlotContainers(extraSlots){
  const out=[];
  let left=Math.max(0,Number(extraSlots)||0),i=0;
  while(left>0){
    const capacity=Math.min(3,left);
    out.push({id:`__extra_${i++}`,label:"추가 슬롯",capacity});
    left-=capacity;
  }
  return out;
}

function estimateSlotCompletion(points,containers,placements,decorations,req,torsoUpCount,maxExtraSlots=9,maxStates=900){
  const remaining=remainingContainersAfterPlacements(containers,placements);
  const currentFreeSlots=remaining.reduce((sum,c)=>sum+Number(c?.capacity||0),0);
  const already=deficitScore(points,req);
  if(already.miss<=0)return {slotOnlyCompletable:true,minAdditionalSlots:0,currentFreeSlots,extraPlacements:[]};
  const test=extra=>{
    const testContainers=[...remaining,...virtualExtraSlotContainers(extra)];
    const solved=solveDecorations(points,testContainers,decorations,req,torsoUpCount,maxStates);
    return solved.complete&&targetRequirementsSatisfied(solved.points,req)?solved:null;
  };
  const maxSolved=test(maxExtraSlots);
  if(!maxSolved)return {slotOnlyCompletable:false,minAdditionalSlots:null,currentFreeSlots,extraPlacements:[]};
  let lo=0,hi=maxExtraSlots,best=maxSolved;
  while(lo<hi){
    const mid=Math.floor((lo+hi)/2);
    const solved=test(mid);
    if(solved){hi=mid;best=solved;}else lo=mid+1;
  }
  if(lo!==maxExtraSlots){const exact=test(lo);if(exact)best=exact;}
  const extraPlacements=(best.placements||[]).filter(x=>String(x?.container||"").startsWith("__extra_"));
  return {slotOnlyCompletable:true,minAdditionalSlots:lo,currentFreeSlots,extraPlacements};
}

function buildTargetGenerationMeta(req, skills){
  const thresholds={};
  for(const [skillId,needRaw] of Object.entries(req)){
    const need=Number(needRaw)||0;
    const def=getSkillDefinition(skills,skillId);
    thresholds[skillId]=(def?.activations||[]).map(a=>Number(a.points)).filter(v=>v>0&&v>=need).sort((a,b)=>a-b);
  }
  return {thresholds};
}

function targetWasteForGeneration(points,req,targetMeta){
  let waste=0,upgradeSteps=0;
  for(const [skillId,needRaw] of Object.entries(req)){
    const need=Number(needRaw)||0,have=Number(points?.[skillId]||0);
    const thresholds=targetMeta.thresholds?.[skillId]||[];
    const reached=thresholds.filter(v=>v<=have).at(-1)??need;
    waste+=Math.max(0,have-reached);
    upgradeSteps+=thresholds.filter(v=>v>need&&v<=have).length;
  }
  return {waste,upgradeSteps};
}

function extendTargetGenerationState(st,armor,req,includeTorsoUp){
  const targetPoints={...st.targetPoints};
  const add=(skills,mul=1)=>{for(const id of Object.keys(req)){const v=Number(skills?.[id]||0);if(v)targetPoints[id]=Number(targetPoints[id]||0)+v*mul;}};
  let torsoUpCount=Number(st.targetTorsoUpCount||0),bodyTargetSkills=st.bodyTargetSkills;
  if(armor?.part==="body"){
    bodyTargetSkills=Object.fromEntries(Object.keys(req).map(id=>[id,Number(armor.skills?.[id]||0)]));
    add(armor.skills,1+torsoUpCount);
  }else{
    add(armor?.skills,1);
    if(includeTorsoUp&&armor?.torsoUp){torsoUpCount+=1;if(bodyTargetSkills)add(bodyTargetSkills,1);}
  }
  return {targetPoints,targetTorsoUpCount:torsoUpCount,bodyTargetSkills};
}


function buildDecorationEfficiency(req, decorations){
  const best={};
  for(const skillId of Object.keys(req||{})){
    const options=(decorations||[]).filter(d=>Number(d?.slots)>=1&&Number(d?.skills?.[skillId]||0)>0);
    best[skillId]=options.reduce((m,d)=>Math.max(m,Number(d.skills?.[skillId]||0)/Math.max(1,Number(d.slots||1))),0);
  }
  return best;
}

function generationFeasibility(state,req,decoEfficiency,availableSlots){
  let missingSkillCount=0,missingTotal=0,estimatedSlots=0,hit=0;
  for(const [id,needRaw] of Object.entries(req||{})){
    const need=Number(needRaw)||0,have=Number(state?.targetPoints?.[id]||0);
    const missing=Math.max(0,need-have);
    if(missing>0){
      missingSkillCount+=1;missingTotal+=missing;
      const eff=Number(decoEfficiency?.[id]||0);
      estimatedSlots+=eff>0?missing/eff:99;
    }
    hit+=Math.min(need,Math.max(0,have));
  }
  const slack=Number(availableSlots||0)-estimatedSlots;
  return {missingSkillCount,missingTotal,estimatedSlots,completionSlack:slack,targetHit:hit};
}

function compareGenerationFeasibility(a,b){
  const af=a.feasibility||{},bf=b.feasibility||{};
  return (af.missingSkillCount||0)-(bf.missingSkillCount||0)
    ||(bf.completionSlack??-999)-(af.completionSlack??-999)
    ||(af.missingTotal||0)-(bf.missingTotal||0)
    ||(bf.targetHit||0)-(af.targetHit||0)
    ||b.efficientScore-a.efficientScore
    ||b.score-a.score;
}

function selectGenerationBeam(next,width,useFeasibility=false){
  const original=[...next].sort((a,b)=>b.score-a.score);
  const efficient=[...next].sort((a,b)=>b.efficientScore-a.efficientScore||b.score-a.score);
  if(!useFeasibility){
    const out=[],seen=new Set();let oi=0,ei=0;
    const pushFrom=list=>{while(list===original?oi<list.length:ei<list.length){const idx=list===original?oi++:ei++;const n=list[idx],sig=buildSignature(n.armors);if(seen.has(sig))continue;seen.add(sig);out.push(n);return true;}return false;};
    while(out.length<width&&(oi<original.length||ei<efficient.length)){
      for(let k=0;k<3&&out.length<width;k++)if(!pushFrom(original))break;
      if(out.length<width)pushFrom(efficient);
    }
    return out;
  }
  const feasible=[...next].sort(compareGenerationFeasibility);
  const out=[],seen=new Set();let oi=0,ei=0,fi=0;
  const pushFrom=(list,key)=>{
    let i=key==='o'?oi:key==='e'?ei:fi;
    while(i<list.length){const n=list[i++],sig=buildSignature(n.armors);if(seen.has(sig))continue;seen.add(sig);out.push(n);if(key==='o')oi=i;else if(key==='e')ei=i;else fi=i;return true;}
    if(key==='o')oi=i;else if(key==='e')ei=i;else fi=i;return false;
  };
  while(out.length<width&&(oi<original.length||ei<efficient.length||fi<feasible.length)){
    if(out.length<width)pushFrom(feasible,'f');
    if(out.length<width)pushFrom(efficient,'e');
    for(let k=0;k<2&&out.length<width;k++)if(!pushFrom(original,'o'))break;
  }
  return out;
}

function selectFinalistsWithTargetEfficiency(beam,limit,useFeasibility=false){
  const original=[...beam].sort((a,b)=>b.score-a.score);
  const efficient=[...beam].sort((a,b)=>b.efficientScore-a.efficientScore||b.score-a.score);
  const out=[],seen=new Set();let oi=0,ei=0,fi=0;
  const feasible=useFeasibility?[...beam].sort(compareGenerationFeasibility):[];
  const push=(list,key)=>{
    let i=key==='o'?oi:key==='e'?ei:fi;
    while(i<list.length){const n=list[i++],sig=buildSignature(n.armors);if(seen.has(sig))continue;seen.add(sig);out.push(n);if(key==='o')oi=i;else if(key==='e')ei=i;else fi=i;return true;}
    if(key==='o')oi=i;else if(key==='e')ei=i;else fi=i;return false;
  };
  while(out.length<limit&&(oi<original.length||ei<efficient.length||(useFeasibility&&fi<feasible.length))){
    if(useFeasibility){for(let k=0;k<2&&out.length<limit;k++)if(!push(feasible,'f'))break;}
    if(out.length<limit)push(efficient,'e');
    if(out.length<limit)push(original,'o');
  }
  return out;
}


function compactDecorationPlacements(basePoints,placements,decorations,req,torsoUpCount){
  let current=[...(placements||[])];
  const calcPoints=list=>{
    const points={...basePoints};
    for(const placed of list)skillMapAdd(points,placed.deco?.skills,placed.container==='body'?1+torsoUpCount:1);
    return points;
  };
  const used=list=>list.reduce((sum,p)=>sum+Number(p?.deco?.slots||0),0);
  const overage=points=>Object.entries(req||{}).reduce((sum,[id,need])=>sum+Math.max(0,Number(points?.[id]||0)-Number(need||0)),0);
  let changed=true,guard=0;
  while(changed&&guard++<12){
    changed=false;
    outer:
    for(let i=0;i<current.length;i++){
      const old=current[i],oldSlots=Number(old?.deco?.slots||0);
      const alternatives=[null,...(decorations||[]).filter(d=>Number(d?.slots||0)<oldSlots&&Number(d?.slots||0)>=1&&Object.keys(req||{}).some(id=>Number(d?.skills?.[id]||0)>0))];
      let bestList=current,bestPoints=calcPoints(current),bestUsed=used(current),bestOver=overage(bestPoints);
      for(const deco of alternatives){
        const trial=current.slice();
        if(deco)trial[i]={deco,container:old.container};else trial.splice(i,1);
        const pts=calcPoints(trial);
        if(!targetRequirementsSatisfied(pts,req))continue;
        const u=used(trial),o=overage(pts);
        if(u<bestUsed||(u===bestUsed&&o<bestOver)){bestList=trial;bestPoints=pts;bestUsed=u;bestOver=o;}
      }
      if(bestList!==current){current=bestList;changed=true;break outer;}
    }
  }
  return {placements:current,points:calcPoints(current)};
}

function remainingContainerCapacities(containers,placements=[]){
  const remaining=Object.fromEntries((containers||[]).map(c=>[c.id,Number(c.capacity||0)]));
  for(const placed of placements||[]){
    const id=placed?.container,slots=Number(placed?.deco?.slots||0);
    if(id in remaining)remaining[id]=Math.max(0,Number(remaining[id]||0)-slots);
  }
  return remaining;
}

function residualStateMetrics(points,req,skills,preferredSkillWeights,remaining){
  const calc={points,activated:getActivatedSkills(points,skills)};
  const targetIds=new Set(Object.keys(req||{}));
  const positive=calc.activated.filter(a=>Number(a.threshold)>0);
  const extraPositiveSkillCount=positive.filter(a=>!targetIds.has(a.skillId)).length;
  const targetEff=targetPointEfficiency(calc,req,skills);
  const neg=negativeSkillBurden(calc);
  const pref=preferredSkillMetrics(calc,preferredSkillWeights);
  const remainingSlots=Object.values(remaining||{}).reduce((s,v)=>s+Number(v||0),0);
  return {extraPositiveSkillCount,targetUpgradeSteps:targetEff.targetUpgradeSteps,...neg,...pref,remainingSlots};
}

function compareResidualStates(a,b){
  const am=a.metrics||{},bm=b.metrics||{};
  return (bm.preferredSkillScore||0)-(am.preferredSkillScore||0)
    ||(bm.preferredSkillCount||0)-(am.preferredSkillCount||0)
    ||(bm.extraPositiveSkillCount||0)-(am.extraPositiveSkillCount||0)
    ||(bm.targetUpgradeSteps||0)-(am.targetUpgradeSteps||0)
    ||(am.negativeSkillCount||0)-(bm.negativeSkillCount||0)
    ||(am.negativeSkillSeverity||0)-(bm.negativeSkillSeverity||0)
    ||(bm.remainingSlots||0)-(am.remainingSlots||0)
    ||a.addedCount-b.addedCount;
}

function repackDecorationPlacements(containers,placements,torsoUpCount=0){
  const caps=Object.fromEntries((containers||[]).map(c=>[c.id,Number(c.capacity||0)]));
  const fixed=[];const movable=[];
  for(const p of placements||[]){
    if(torsoUpCount>0&&p?.container==='body')fixed.push(p);else movable.push(p);
  }
  for(const p of fixed)caps[p.container]=Math.max(0,Number(caps[p.container]||0)-Number(p?.deco?.slots||0));
  const order=Object.fromEntries((containers||[]).map((c,i)=>[c.id,i]));
  const eligibleIds=(containers||[]).map(c=>c.id).filter(id=>!(torsoUpCount>0&&id==='body'));
  const sorted=[...movable].sort((a,b)=>Number(b?.deco?.slots||0)-Number(a?.deco?.slots||0));
  const out=[...fixed];
  for(const p of sorted){
    const slots=Math.max(1,Number(p?.deco?.slots||0));
    const fit=eligibleIds.filter(id=>Number(caps[id]||0)>=slots).sort((a,b)=>Number(caps[a])-Number(caps[b])||(order[a]??99)-(order[b]??99));
    if(!fit.length)return placements;
    const id=fit[0];caps[id]-=slots;out.push({...p,container:id});
  }
  return out;
}

function optimizePartialSkillCompletions(basePoints,containers,placements,decorations,req,torsoUpCount,skills,preferredSkillWeights={},maxStates=180){
  const remainingContainers=remainingContainersAfterPlacements(containers,placements);
  const free=remainingContainers.reduce((sum,c)=>sum+Number(c?.capacity||0),0);
  if(free<=0)return {placements,points:basePoints};
  const targetIds=new Set(Object.keys(req||{}));
  const partials=[];
  for(const skill of skills||[]){
    if(targetIds.has(skill.id))continue;
    const have=Number(basePoints?.[skill.id]||0);
    if(have<=0)continue;
    const next=(skill.activations||[]).map(a=>Number(a.points)).filter(v=>v>0&&v>have).sort((a,b)=>a-b)[0];
    if(!Number.isFinite(next))continue;
    const gap=next-have;
    let minSlots=Infinity;
    for(const d of decorations||[]){
      const gain=Math.max(0,Number(d?.skills?.[skill.id]||0));
      const ds=Math.max(1,Number(d?.slots||0));
      if(!gain)continue;
      minSlots=Math.min(minSlots,Math.ceil(gap/gain)*ds);
    }
    if(minSlots<=free)partials.push({id:skill.id,next,gap,minSlots,preferred:Number(preferredSkillWeights?.[skill.id]||0)});
  }
  partials.sort((a,b)=>b.preferred-a.preferred||a.minSlots-b.minSlots||a.gap-b.gap).splice(6);
  if(!partials.length)return {placements,points:basePoints};
  const combos=[];
  const build=(start,left,arr)=>{
    if(arr.length)combos.push([...arr]);
    if(left<=0)return;
    for(let i=start;i<partials.length;i++){arr.push(partials[i]);build(i+1,left-1,arr);arr.pop();}
  };
  build(0,Math.min(3,partials.length),[]);
  combos.sort((a,b)=>b.length-a.length||b.reduce((s,x)=>s+x.preferred,0)-a.reduce((s,x)=>s+x.preferred,0)||a.reduce((s,x)=>s+x.minSlots,0)-b.reduce((s,x)=>s+x.minSlots,0));
  let best={placements,points:basePoints};
  let bestState={points:basePoints,remaining:Object.fromEntries(remainingContainers.map(c=>[c.id,Number(c.capacity||0)])),addedCount:0};
  bestState.metrics=residualStateMetrics(bestState.points,req,skills,preferredSkillWeights,bestState.remaining);
  for(const combo of combos.slice(0,28)){
    if(combo.reduce((sum,x)=>sum+x.minSlots,0)>free)continue;
    const extReq={...req};for(const x of combo)extReq[x.id]=x.next;
    const solved=solveDecorations(basePoints,remainingContainers,decorations,extReq,torsoUpCount,maxStates);
    if(!solved.complete||!targetRequirementsSatisfied(solved.points,extReq))continue;
    const rem=remainingContainerCapacities(remainingContainers,solved.placements||[]);
    const state={points:solved.points,remaining:rem,addedCount:(solved.placements||[]).length};
    state.metrics=residualStateMetrics(state.points,req,skills,preferredSkillWeights,state.remaining);
    if(compareResidualStates(state,bestState)<0){bestState=state;best={placements:[...(placements||[]),...(solved.placements||[])],points:solved.points};}
  }
  return best;
}

function optimizeResidualDecorations(basePoints,containers,placements,decorations,req,torsoUpCount,skills,preferredSkillWeights={},maxStates=260){
  const remaining=remainingContainerCapacities(containers,placements);
  const totalFree=Object.values(remaining).reduce((s,v)=>s+Number(v||0),0);
  if(totalFree<=0)return {placements,points:basePoints};
  const baseActivated=getActivatedSkills(basePoints,skills);
  const negativeIds=new Set(baseActivated.filter(a=>Number(a.threshold)<0).map(a=>a.skillId));
  const targetIds=new Set(Object.keys(req||{}));
  const completion=[];
  for(const s of skills||[]){
    const have=Number(basePoints?.[s.id]||0);
    const next=(s.activations||[]).map(a=>Number(a.points)).filter(v=>v>0&&v>have).sort((a,b)=>a-b)[0];
    if(!Number.isFinite(next))continue;
    const gap=next-have;
    let minSlots=Infinity;
    for(const d of decorations||[]){
      const gain=Math.max(0,Number(d?.skills?.[s.id]||0));
      const ds=Math.max(1,Number(d?.slots||0));
      if(!gain)continue;
      minSlots=Math.min(minSlots,Math.ceil(gap/gain)*ds);
    }
    if(minSlots<=totalFree)completion.push({id:s.id,next,gap,minSlots,partial:have>0,preferred:Number(preferredSkillWeights?.[s.id]||0),target:targetIds.has(s.id)});
  }
  completion.sort((a,b)=>Number(b.partial)-Number(a.partial)||b.preferred-a.preferred||a.minSlots-b.minSlots||a.gap-b.gap||Number(a.target)-Number(b.target));
  const partialCompletion=completion.filter(x=>x.partial);
  const completionSkillIds=new Set([...partialCompletion.map(x=>x.id),...completion.filter(x=>!x.partial).slice(0,12).map(x=>x.id)]);
  const usefulSkillIds=new Set([...negativeIds,...completionSkillIds]);
  const completionMeta=Object.fromEntries(completion.map(x=>[x.id,x]));
  const candidates=(decorations||[])
    .filter(d=>Number(d.slots)>=1&&Number(d.slots)<=3)
    .filter(d=>Object.entries(d.skills||{}).some(([id,v])=>Number(v)>0&&usefulSkillIds.has(id)))
    .sort((a,b)=>{
      const score=d=>{
        const ds=Math.max(1,Number(d.slots||1));
        let best=0;
        for(const [id,vRaw] of Object.entries(d.skills||{})){
          const v=Math.max(0,Number(vRaw)||0);if(!v||!usefulSkillIds.has(id))continue;
          const meta=completionMeta[id];
          if(meta){
            const completionBoost=v>=meta.gap?6:0;
            const partialBoost=meta.partial?10:0;
            const preferredBoost=Math.max(0,meta.preferred)*2;
            best=Math.max(best,partialBoost+completionBoost+preferredBoost+(v/ds)*3+1/Math.max(1,meta.minSlots));
          }else if(negativeIds.has(id))best=Math.max(best,(v/ds)*2);
        }
        return best;
      };
      return score(b)-score(a)||Number(a.slots||0)-Number(b.slots||0);
    }).slice(0,36);
  if(!candidates.length)return {placements,points:basePoints};
  const seed={points:{...basePoints},remaining:{...remaining},added:[],addedCount:0};
  seed.metrics=residualStateMetrics(seed.points,req,skills,preferredSkillWeights,seed.remaining);
  let states=[seed],best=seed;
  const maxSteps=Math.min(8,totalFree);
  const relevantIds=[...usefulSkillIds];
  for(let step=0;step<maxSteps;step++){
    const expanded=[...states];
    for(const st of states){
      for(const deco of candidates){
        const slots=Number(deco.slots||0);
        for(const [container,freeRaw] of Object.entries(st.remaining)){
          if(Number(freeRaw)<slots)continue;
          const ns={points:{...st.points},remaining:{...st.remaining},added:[...st.added,{deco,container}],addedCount:st.addedCount+1};
          ns.remaining[container]-=slots;
          skillMapAdd(ns.points,deco.skills,container==='body'?1+torsoUpCount:1);
          if(!targetRequirementsSatisfied(ns.points,req))continue;
          ns.metrics=residualStateMetrics(ns.points,req,skills,preferredSkillWeights,ns.remaining);
          expanded.push(ns);
          if(compareResidualStates(ns,best)<0)best=ns;
        }
      }
    }
    const dedup=new Map();
    for(const st of expanded){
      const pts=relevantIds.map(id=>`${id}:${Math.max(-20,Math.min(30,Number(st.points?.[id]||0)))}`).join(',');
      const rem=Object.entries(st.remaining).map(([k,v])=>`${k}:${v}`).join(',');
      const key=pts+'|'+rem;
      const old=dedup.get(key);if(!old||compareResidualStates(st,old)<0)dedup.set(key,st);
    }
    states=[...dedup.values()].sort(compareResidualStates).slice(0,maxStates);
    if(states[0]&&compareResidualStates(states[0],best)<0)best=states[0];
  }
  return {placements:[...(placements||[]),...best.added],points:best.points,residualMetrics:best.metrics};
}

function autoSearchProfile(targetCount){
  if(targetCount>=5)return {name:"complex5",partLimit:36,beamWidth:3000,finalists:100,decoStates:220,timeBudgetMs:10000};
  if(targetCount>=4)return {name:"complex4",partLimit:36,beamWidth:3000,finalists:80,decoStates:220,timeBudgetMs:6000};
  if(targetCount===3)return {name:"balanced3",partLimit:46,beamWidth:6500,finalists:260,decoStates:900,timeBudgetMs:8000};
  return {name:"deep",partLimit:55,beamWidth:12000,finalists:700,decoStates:1800,timeBudgetMs:12000};
}

export async function searchBuilds(options, data){
  const {
    targetActivationIds=[], hunterType="blade", rank="all",
    charm={skills:{},slots:0}, weaponSlots=0,
    allowDecorations=true, includeTorsoUp=true, limit=20,
    preferredSkillWeights={}, onProgress=null, timeBudgetMs=null
  } = options;

  const requireTorsoUp=targetActivationIds.includes("__torso_up__");
  const req=requirementMap(targetActivationIds.filter(id=>id!=="__torso_up__"),data.skills);
  if(!Object.keys(req).length && !requireTorsoUp) return {results:[],nearMisses:[],stats:{message:"목표 스킬 없음"}};

  const targetCount=Object.keys(req).length+(requireTorsoUp?1:0);
  // 후보 생성 단계에서는 현재 호석(보유 발굴무기 고정 스킬을 합산한 값 포함)으로
  // 이미 충족한 포인트를 다시 방어구에서 쫓지 않는다. 최종 검증은 여전히 전체 req로 수행한다.
  const generationReq=Object.fromEntries(Object.entries(req).map(([id,need])=>[id,Math.max(0,Number(need||0)-Math.max(0,Number(charm?.skills?.[id]||0))) ]).filter(([,need])=>need>0));
  const profile=autoSearchProfile(targetCount);
  const budget=Math.max(1000,Number(timeBudgetMs||profile.timeBudgetMs));
  const startedAt=Date.now();
  const progress=payload=>{try{if(typeof onProgress==="function")onProgress(payload)}catch{}};
  const yieldUi=()=>new Promise(r=>setTimeout(r,0));

  const eligible = data.armors.filter(a=>{
    const typeOk = hunterType==="both" || a.hunterType==="both" || a.hunterType===hunterType;
    const rankOk = progressionRankAllows(a.rank,rank);
    return typeOk && rankOk;
  });

  const byPart=Object.fromEntries(PARTS.map(p=>[p, eligible.filter(a=>a.part===p)
    .sort((a,b)=>armorScore(b,generationReq)-armorScore(a,generationReq)||compareArmorGenerationTie(a,b,rank))
    .slice(0,profile.partLimit)]));

  if(PARTS.some(p=>byPart[p].length===0)){
    return {results:[],nearMisses:[],stats:{message:"필요한 방어구 부위 데이터가 부족합니다."}};
  }

  const targetMeta=buildTargetGenerationMeta(req,data.skills);
  const useFeasibility=targetCount>=4;
  const decorationEfficiency=useFeasibility?buildDecorationEfficiency(req,data.decorations):null;
  const fixedGenerationSlots=useFeasibility?Math.max(0,Number(charm?.slots||0))+Math.max(0,Number(weaponSlots||0)):0;
  const futureMaxSlots=useFeasibility?Object.fromEntries(PARTS.map((p,i)=>[i,PARTS.slice(i+1).reduce((sum,rp)=>sum+Math.max(...byPart[rp].map(a=>Number(a?.slots||0))),0)])):{};
  const initialTargetPoints=Object.fromEntries(Object.keys(req).map(id=>[id,Number(charm?.skills?.[id]||0)]));
  let beam=[{armors:[],score:0,efficientScore:0,targetPoints:initialTargetPoints,targetTorsoUpCount:0,bodyTargetSkills:null}];
  for(let partIndex=0;partIndex<PARTS.length;partIndex++){
    const part=PARTS[partIndex];
    const next=[];
    for(const st of beam){
      for(const armor of byPart[part]){
        const arr=[...st.armors,armor];
        let score=arr.reduce((sum,a)=>sum+armorScore(a,generationReq),0);
        if(requireTorsoUp && arr.some(a=>a?.part!=="body"&&a?.torsoUp)) score+=18;
        const body=arr.find(a=>a.part==="body");
        const torso=includeTorsoUp ? arr.filter(a=>a.torsoUp).length : 0;
        if(body && torso){
          score += Object.keys(req).reduce((sum,id)=>sum+Math.max(0,Number(body.skills?.[id]||0))*torso*1.6,0);
        }
        const targetState=extendTargetGenerationState(st,armor,req,includeTorsoUp);
        const efficiency=targetWasteForGeneration(targetState.targetPoints,req,targetMeta);
        const feasibility=useFeasibility?generationFeasibility(targetState,req,decorationEfficiency,fixedGenerationSlots+arr.reduce((sum,a)=>sum+Number(a?.slots||0),0)+Number(futureMaxSlots[partIndex]||0)):null;
        next.push({armors:arr,score,efficientScore:score+efficiency.upgradeSteps*1.5,feasibility,targetWaste:efficiency.waste,...targetState});
      }
    }
    beam=selectGenerationBeam(next,profile.beamWidth,useFeasibility);
    progress({phase:"armor",current:partIndex+1,total:PARTS.length,beam:beam.length});
    await yieldUi();
  }

  const finalists=selectFinalistsWithTargetEfficiency(beam,profile.finalists,useFeasibility);
  const rankedPool=[];
  const nearMissPool=[];
  const poolTarget=Math.min(profile.finalists,Math.max(60,Number(limit||20)*5));
  let timedOut=false;
  let checkedFinalists=0;
  for(let candidateIndex=0;candidateIndex<finalists.length;candidateIndex++){
    if(Date.now()-startedAt>=budget){timedOut=true;break;}
    const candidate=finalists[candidateIndex];
    checkedFinalists=candidateIndex+1;
    if(requireTorsoUp && !candidate.armors.some(a=>a?.part!=="body"&&a?.torsoUp)) continue;
    const {points,torsoUpCount}=baseBuildPoints(candidate.armors,charm,includeTorsoUp);
    const containers=containersForBuild(candidate.armors,charm.slots,weaponSlots);
    let solved={placements:[],points,complete:deficitScore(points,req).miss<=0};
    if(!solved.complete){
      if(allowDecorations)solved=solveDecorations(points,containers,data.decorations,req,torsoUpCount,profile.decoStates);
    }
    if(!solved.complete){
      const missing=requirementDeficits(solved.points,req);
      nearMissPool.push({
        armors:candidate.armors,
        decorations:solved.placements||[],
        points:solved.points||points,
        missing,
        missingSkillCount:missing.length,
        missingTotal:missing.reduce((sum,x)=>sum+x.missing,0),
        score:candidate.score
      });
    }else if(targetRequirementsSatisfied(solved.points,req)){
      const calc=calculateBuild({
        armors:candidate.armors,charm,weaponSlots,decorations:solved.placements
      },data,includeTorsoUp);
      if(targetRequirementsSatisfied(calc.points,req)){
        const decoMetrics=decorationBurden(solved.placements);
        const metrics={
          ...negativeSkillBurden(calc),
          ...decoMetrics,
          ...targetPointEfficiency(calc,req,data.skills),
          ...preferredSkillMetrics(calc,preferredSkillWeights),
          ...practicalBuildMetrics(candidate.armors,rank,calc,containers,decoMetrics.usedDecorationSlots)
        };
        rankedPool.push({
          armors:candidate.armors,
          decorations:solved.placements,
          calc,
          metrics,
          score:candidate.score - solved.placements.length*0.15
        });
      }
    }
    if((candidateIndex+1)%5===0){
      progress({phase:"decorate",current:candidateIndex+1,total:finalists.length,exact:rankedPool.length,near:nearMissPool.length});
      await yieldUi();
    }
    if(rankedPool.length>=poolTarget)break;
  }

  // 요청 스킬을 완성한 후보 가운데 실제로 여유 슬롯이 있는 일부만 2차 최적화한다.
  // 1차 전수 탐색에서 매 후보마다 후처리를 돌리면 단순 1~2스킬 검색도 지나치게 느려지므로,
  // 기본 완성도가 높은 후보 + 잔여 슬롯이 많은 후보의 합집합에만 적용한다.
  if(allowDecorations&&rankedPool.length){
    const provisional=[...rankedPool].sort(compareRankedBuilds);
    const byFree=[...rankedPool].sort((a,b)=>(b.metrics?.remainingSlots||0)-(a.metrics?.remainingSlots||0)||compareRankedBuilds(a,b));
    const byPotential=[...rankedPool].sort((a,b)=>{
      const ap=residualCompletionPotential(a.calc,req,data.skills,data.decorations,a.metrics?.remainingSlots);
      const bp=residualCompletionPotential(b.calc,req,data.skills,data.decorations,b.metrics?.remainingSlots);
      return bp.count-ap.count||bp.score-ap.score||compareRankedBuilds(a,b);
    });
    const selected=new Set();
    const optimizeCap=Math.min(rankedPool.length,targetCount>=4?Math.max(8,Math.min(14,Number(limit||20)+4)):Math.max(3,Math.min(5,Number(limit||20)+1)));
    const laneCap=targetCount>=4?Math.max(4,Math.ceil(optimizeCap/2)):Math.max(2,Math.ceil(optimizeCap/2));
    const addLane=(list,predicate=()=>true)=>{for(const item of list.slice(0,laneCap)){if(selected.size>=optimizeCap)break;if(predicate(item))selected.add(item);}};
    addLane(provisional);
    addLane(byPotential,item=>Number(item.metrics?.remainingSlots||0)>0);
    addLane(byFree,item=>Number(item.metrics?.remainingSlots||0)>0);
    for(const item of selected){
      if(targetCount<4&&Number(item.metrics?.remainingSlots||0)<=0)continue;
      const {points,torsoUpCount}=baseBuildPoints(item.armors,charm,includeTorsoUp);
      const containers=containersForBuild(item.armors,charm.slots,weaponSlots);
      const compact=compactDecorationPlacements(points,item.decorations||[],data.decorations,req,torsoUpCount);
      const repackedPlacements=repackDecorationPlacements(containers,compact.placements,torsoUpCount);
      const partial=optimizePartialSkillCompletions(compact.points,containers,repackedPlacements,data.decorations,req,torsoUpCount,data.skills,preferredSkillWeights,targetCount>=4?180:80);
      const optimized=optimizeResidualDecorations(partial.points,containers,partial.placements,data.decorations,req,torsoUpCount,data.skills,preferredSkillWeights,targetCount>=4?60:20);
      const calc=calculateBuild({armors:item.armors,charm,weaponSlots,decorations:optimized.placements},data,includeTorsoUp);
      if(!targetRequirementsSatisfied(calc.points,req))continue;
      const decoMetrics=decorationBurden(optimized.placements);
      item.decorations=optimized.placements;
      item.calc=calc;
      item.metrics={
        ...negativeSkillBurden(calc),
        ...decoMetrics,
        ...targetPointEfficiency(calc,req,data.skills),
        ...preferredSkillMetrics(calc,preferredSkillWeights),
        ...practicalBuildMetrics(item.armors,rank,calc,containers,decoMetrics.usedDecorationSlots)
      };
    }
  }

  rankedPool.sort(compareRankedBuilds);
  const diversified=diversifyExactTieGroups(rankedPool);
  const results=diversified.slice(0,Number(limit));

  nearMissPool.sort((a,b)=>a.missingSkillCount-b.missingSkillCount||a.missingTotal-b.missingTotal||(a.decorations?.length||0)-(b.decorations?.length||0)||b.score-a.score||buildSignature(a.armors).localeCompare(buildSignature(b.armors)));
  const nearAnalysisPool=nearMissPool.slice(0,Math.min(16,nearMissPool.length)).map(n=>{
    const {torsoUpCount}=baseBuildPoints(n.armors,charm,includeTorsoUp);
    const containers=containersForBuild(n.armors,charm.slots,weaponSlots);
    const slotCompletion=estimateSlotCompletion(n.points,containers,n.decorations||[],data.decorations,req,torsoUpCount,9,Math.min(1200,profile.decoStates));
    return {...n,slotCompletion};
  });
  nearAnalysisPool.sort((a,b)=>
    Number(!a.slotCompletion?.slotOnlyCompletable)-Number(!b.slotCompletion?.slotOnlyCompletable)
    ||Number(a.slotCompletion?.minAdditionalSlots??99)-Number(b.slotCompletion?.minAdditionalSlots??99)
    ||a.missingSkillCount-b.missingSkillCount
    ||a.missingTotal-b.missingTotal
    ||Number(b.slotCompletion?.currentFreeSlots||0)-Number(a.slotCompletion?.currentFreeSlots||0)
    ||(a.decorations?.length||0)-(b.decorations?.length||0)
    ||b.score-a.score
    ||buildSignature(a.armors).localeCompare(buildSignature(b.armors))
  );
  const nearMisses=nearAnalysisPool.slice(0,3).map(n=>({
    ...n,
    calc:calculateBuild({armors:n.armors,charm,weaponSlots,decorations:n.decorations||[]},data,includeTorsoUp)
  }));
  const elapsedMs=Date.now()-startedAt;
  return {
    results,
    nearMisses,
    stats:{
      eligible:eligible.length,
      finalists:finalists.length,
      checkedFinalists,
      rankedPool:rankedPool.length,
      beam:beam.length,
      approximate:true,
      targetCount,
      profile:profile.name,
      timedOut,
      elapsedMs
    }
  };
}

