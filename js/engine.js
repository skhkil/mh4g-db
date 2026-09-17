
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
      if(a && Number(a.points)>0) req[s.id] = Math.max(req[s.id]||0, Number(a.points));
    }
  }
  return req;
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
  let s = Number(a.slots||0)*0.65 + Number(a.defense||0)*0.004;
  for(const [id,need] of Object.entries(req)){
    const v = Number(a.skills?.[id]||0);
    if(v>0) s += Math.min(v,need)*2.2;
    if(v<0) s += v*0.35;
  }
  if(a.torsoUp) s += 4;
  return s;
}

function rankAllowed(itemRank, progress){
  if(progress==="all") return true;
  const order={low:1,high:2,g:3};
  return (order[itemRank]||99) <= (order[progress]||0);
}

function dominatesArmor(a,b,req){
  if(a===b || a.part!==b.part || Boolean(a.torsoUp)!==Boolean(b.torsoUp)) return false;
  if(Number(a.slots||0)<Number(b.slots||0) || Number(a.defense||0)<Number(b.defense||0)) return false;
  let strictly = Number(a.slots||0)>Number(b.slots||0) || Number(a.defense||0)>Number(b.defense||0);
  for(const id of Object.keys(req)){
    const av=Number(a.skills?.[id]||0), bv=Number(b.skills?.[id]||0);
    if(av<bv) return false;
    if(av>bv) strictly=true;
  }
  return strictly;
}

function pruneDominatedArmors(items,req){
  const sorted=[...items].sort((a,b)=>armorScore(b,req)-armorScore(a,req));
  const kept=[];
  outer: for(const item of sorted){
    for(const k of kept) if(dominatesArmor(k,item,req)) continue outer;
    kept.push(item);
  }
  return kept;
}

function heapSwap(h,a,b){const t=h[a];h[a]=h[b];h[b]=t}
function heapUp(h,i){while(i>0){const p=(i-1)>>1;if(h[p].score<=h[i].score)break;heapSwap(h,p,i);i=p}}
function heapDown(h,i){for(;;){let m=i,l=i*2+1,r=l+1;if(l<h.length&&h[l].score<h[m].score)m=l;if(r<h.length&&h[r].score<h[m].score)m=r;if(m===i)break;heapSwap(h,i,m);i=m}}
function pushTopK(heap,node,k){
  if(heap.length<k){heap.push(node);heapUp(heap,heap.length-1);return}
  if(node.score<=heap[0].score)return;
  heap[0]=node;heapDown(heap,0);
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

function relevantDecorationsFor(req,decorations){
  return decorations
    .filter(d=>Number(d.slots)>=1 && Number(d.slots)<=3)
    .filter(d=>Object.keys(req).some(id=>Number(d.skills?.[id]||0)>0))
    .sort((a,b)=>{
      const av=Object.keys(req).reduce((s,id)=>s+Math.max(0,Number(a.skills?.[id]||0)),0)/Number(a.slots||1);
      const bv=Object.keys(req).reduce((s,id)=>s+Math.max(0,Number(b.skills?.[id]||0)),0)/Number(b.slots||1);
      return bv-av || Number(a.slots||0)-Number(b.slots||0);
    })
    .slice(0,24);
}

function solveDecorations(basePoints, containers, relevant, req, torsoUpCount, maxStates=1400){
  const already=deficitScore(basePoints,req);
  if(already.miss<=0) return {placements:[],points:{...basePoints}};
  if(!relevant.length) return null;

  let states=[{
    remaining:Object.fromEntries(containers.map(c=>[c.id,Number(c.capacity||0)])),
    points:{...basePoints}, placements:[], score:-already.miss*8
  }];
  let best=null;
  const maxSteps = Math.min(16, containers.reduce((s,c)=>s+Number(c.capacity||0),0));

  for(let step=0; step<maxSteps; step++){
    const dedup=new Map();
    for(const st of states){
      const baseKey=Object.keys(req).map(k=>`${k}:${Math.min(req[k],st.points[k]||0)}`).join(",")+"|"+Object.entries(st.remaining).map(([k,v])=>`${k}:${v}`).join(",");
      dedup.set(baseKey,st);
      for(const deco of relevant){
        const cost=Number(deco.slots||0);
        for(const c of containers){
          if(st.remaining[c.id] < cost) continue;
          const ns=placeDecorationState(st,deco,c.id,1+torsoUpCount,req);
          if(deficitScore(ns.points,req).miss<=0){best=ns;break}
          const capped=Object.keys(req).map(k=>`${k}:${Math.min(req[k],ns.points[k]||0)}`).join(",");
          const rem=Object.entries(ns.remaining).map(([k,v])=>`${k}:${v}`).join(",");
          const key=capped+"|"+rem;
          if(!dedup.has(key)||dedup.get(key).score<ns.score)dedup.set(key,ns);
        }
        if(best)break;
      }
      if(best)break;
    }
    if(best)break;
    states=[...dedup.values()].sort((a,b)=>b.score-a.score).slice(0,maxStates);
  }
  return best ? {placements:best.placements,points:best.points} : null;
}

function validatePlacements(placements,containers){
  const cap=Object.fromEntries(containers.map(c=>[c.id,Number(c.capacity||0)]));
  for(const p of placements||[]){
    const cost=Number(p.deco?.slots||0);
    if(!(p.container in cap)||cost<1||cap[p.container]<cost)return false;
    cap[p.container]-=cost;
  }
  return true;
}

export async function searchBuilds(options, data){
  const {
    targetActivationIds=[], hunterType="blade", rank="all",
    charm={skills:{},slots:0}, weaponSlots=0,
    allowDecorations=true, includeTorsoUp=true, limit=20
  } = options;
  const t0=performance.now();
  const req=requirementMap(targetActivationIds,data.skills);
  if(!Object.keys(req).length) return {results:[],stats:{message:"목표 스킬 없음"}};

  const eligible = data.armors.filter(a=>{
    const typeOk = hunterType==="both" || a.hunterType==="both" || a.hunterType===hunterType;
    return typeOk && rankAllowed(a.rank,rank);
  });

  const rawByPart=Object.fromEntries(PARTS.map(p=>[p,eligible.filter(a=>a.part===p)]));
  const byPart={};
  for(const p of PARTS){
    const pruned=pruneDominatedArmors(rawByPart[p],req)
      .sort((a,b)=>armorScore(b,req)-armorScore(a,req));
    byPart[p]=pruned.slice(0,48);
  }
  if(PARTS.some(p=>byPart[p].length===0)) return {results:[],stats:{message:"필요한 방어구 부위 데이터가 부족합니다."}};

  let beam=[{armors:[],score:0,baseScore:0}];
  const beamWidth=7000;
  for(const part of PARTS){
    const heap=[];
    for(const st of beam){
      for(const armor of byPart[part]){
        const arr=[...st.armors,armor];
        const baseScore=st.baseScore+armorScore(armor,req);
        const body=arr.find(a=>a.part==="body");
        const torso=includeTorsoUp ? arr.filter(a=>a.torsoUp).length : 0;
        const torsoBonus=body&&torso?Object.keys(req).reduce((s,id)=>s+Math.max(0,Number(body.skills?.[id]||0))*torso*1.6,0):0;
        pushTopK(heap,{armors:arr,baseScore,score:baseScore+torsoBonus},beamWidth);
      }
    }
    beam=heap.sort((a,b)=>b.score-a.score);
    await new Promise(r=>setTimeout(r,0));
  }
  const tBeam=performance.now();

  const finalists=beam.slice(0,700);
  const relevantDecorations=allowDecorations?relevantDecorationsFor(req,data.decorations):[];
  const decoMemo=new Map();
  const results=[];
  let checked=0,invalid=0;
  for(const candidate of finalists){
    const {points,torsoUpCount}=baseBuildPoints(candidate.armors,charm,includeTorsoUp);
    const containers=containersForBuild(candidate.armors,charm.slots,weaponSlots);
    let solved={placements:[],points};
    if(deficitScore(points,req).miss>0){
      if(!allowDecorations)continue;
      const pointKey=Object.keys(req).map(k=>`${k}:${Math.min(req[k],points[k]||0)}`).join(",");
      const capKey=containers.map(c=>`${c.id}:${c.capacity}`).join(",");
      const memoKey=`${pointKey}|${capKey}|t${torsoUpCount}`;
      if(decoMemo.has(memoKey)) solved=decoMemo.get(memoKey);
      else{
        solved=solveDecorations(points,containers,relevantDecorations,req,torsoUpCount,1400);
        decoMemo.set(memoKey,solved);
      }
      if(!solved)continue;
    }
    checked++;
    if(!validatePlacements(solved.placements,containers)){invalid++;continue}
    if(deficitScore(solved.points,req).miss>0)continue;
    const calc=calculateBuild({armors:candidate.armors,charm,weaponSlots,decorations:solved.placements},data,includeTorsoUp);
    if(deficitScore(calc.points,req).miss>0){invalid++;continue}
    results.push({armors:candidate.armors,decorations:solved.placements,calc,score:candidate.score-solved.placements.length*0.15});
    if(results.length>=Number(limit))break;
    if(checked%24===0)await new Promise(r=>setTimeout(r,0));
  }
  const tEnd=performance.now();
  return {
    results,
    stats:{
      eligible:eligible.length,
      rawCandidates:Object.fromEntries(PARTS.map(p=>[p,rawByPart[p].length])),
      candidates:Object.fromEntries(PARTS.map(p=>[p,byPart[p].length])),
      finalists:finalists.length,beam:beam.length,approximate:true,
      relevantDecorations:relevantDecorations.length,decorationMemo:decoMemo.size,invalid,
      beamMs:Math.round(tBeam-t0),solveMs:Math.round(tEnd-tBeam),totalMs:Math.round(tEnd-t0)
    }
  };
}
