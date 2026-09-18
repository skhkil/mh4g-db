
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
  for(const [id,need] of Object.entries(req)){
    const v = Number(a.skills?.[id]||0);
    if(v>0) s += Math.min(v,need)*2.2;
    if(v<0) s += v*0.35;
  }
  if(a.torsoUp) s += 4;
  return s;
}

function buildSignature(items){
  return PARTS.map(p=>items.find(a=>a?.part===p)?.id||"-").join("|");
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
  if(already.miss<=0) return {placements:[],points:{...basePoints}};

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
  const maxSteps = Math.min(16, containers.reduce((s,c)=>s+Number(c.capacity||0),0));

  for(let step=0; step<maxSteps; step++){
    const expanded=[...states];
    for(const st of states){
      for(const deco of relevant){
        for(const c of containers){
          if(st.remaining[c.id] >= Number(deco.slots||0)){
            const ns=placeDecorationState(st,deco,c.id,1+torsoUpCount,req);
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
    for(const s of expanded){
      const capped=Object.keys(req).map(k=>`${k}:${Math.min(req[k],s.points[k]||0)}`).join(",");
      const rem=Object.entries(s.remaining).map(([k,v])=>`${k}:${v}`).join(",");
      const key=capped+"|"+rem;
      if(!dedup.has(key) || dedup.get(key).score<s.score) dedup.set(key,s);
    }
    states=[...dedup.values()].sort((a,b)=>b.score-a.score).slice(0,maxStates);
  }
  return best ? {placements:best.placements,points:best.points} : null;
}

export async function searchBuilds(options, data){
  const {
    targetActivationIds=[], hunterType="blade", rank="all",
    charm={skills:{},slots:0}, weaponSlots=0,
    allowDecorations=true, includeTorsoUp=true, limit=20
  } = options;

  const requireTorsoUp=targetActivationIds.includes("__torso_up__");
  const req=requirementMap(targetActivationIds.filter(id=>id!=="__torso_up__"),data.skills);
  if(!Object.keys(req).length && !requireTorsoUp) return {results:[],stats:{message:"목표 스킬 없음"}};

  const eligible = data.armors.filter(a=>{
    const typeOk = hunterType==="both" || a.hunterType==="both" || a.hunterType===hunterType;
    const rankOk = rank==="all" || a.rank===rank;
    return typeOk && rankOk;
  });

  const byPart=Object.fromEntries(PARTS.map(p=>[p, eligible.filter(a=>a.part===p)
    .sort((a,b)=>armorScore(b,req)-armorScore(a,req))
    .slice(0,55)]));

  if(PARTS.some(p=>byPart[p].length===0)){
    return {results:[],stats:{message:"필요한 방어구 부위 데이터가 부족합니다."}};
  }

  let beam=[{armors:[],score:0}];
  const beamWidth=12000;

  for(const part of PARTS){
    const next=[];
    for(const st of beam){
      for(const armor of byPart[part]){
        const arr=[...st.armors,armor];
        let score=arr.reduce((s,a)=>s+armorScore(a,req),0);
        if(requireTorsoUp && arr.some(a=>a?.part!=="body"&&a?.torsoUp)) score+=18;
        // 몸통배가가 있을 때 몸통 스킬 잠재력 반영
        const body=arr.find(a=>a.part==="body");
        const torso=includeTorsoUp ? arr.filter(a=>a.torsoUp).length : 0;
        if(body && torso){
          score += Object.keys(req).reduce((s,id)=>s+Math.max(0,Number(body.skills?.[id]||0))*torso*1.6,0);
        }
        next.push({armors:arr,score});
      }
    }
    next.sort((a,b)=>b.score-a.score);
    const seen=new Set(); beam=[];
    for(const n of next){
      const sig=buildSignature(n.armors);
      if(seen.has(sig)) continue;
      seen.add(sig); beam.push(n);
      if(beam.length>=beamWidth) break;
    }
    await new Promise(r=>setTimeout(r,0));
  }

  const finalists=beam.slice(0,700);
  const results=[];
  for(const candidate of finalists){
    if(requireTorsoUp && !candidate.armors.some(a=>a?.part!=="body"&&a?.torsoUp)) continue;
    const {points,torsoUpCount}=baseBuildPoints(candidate.armors,charm,includeTorsoUp);
    const containers=containersForBuild(candidate.armors,charm.slots,weaponSlots);
    let solved={placements:[],points};
    if(deficitScore(points,req).miss>0){
      if(!allowDecorations) continue;
      solved=solveDecorations(points,containers,data.decorations,req,torsoUpCount,1800);
      if(!solved) continue;
    }
    if(deficitScore(solved.points,req).miss>0) continue;
    const calc=calculateBuild({
      armors:candidate.armors,charm,weaponSlots,decorations:solved.placements
    },data,includeTorsoUp);
    results.push({
      armors:candidate.armors,
      decorations:solved.placements,
      calc,
      score:candidate.score - solved.placements.length*0.15
    });
    if(results.length>=Number(limit)) break;
  }

  return {
    results,
    stats:{
      eligible:eligible.length,
      finalists:finalists.length,
      beam:beam.length,
      approximate:true
    }
  };
}
