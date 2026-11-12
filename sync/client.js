/* MH4G optional cross-device sync; does not change existing app save logic. */
(()=>{
"use strict";
const KEYS=["mh4g-builds-v1","mh4g-owned-charms-v1","mh4g-owned-relic-weapons-v1","mh4g-owned-relic-armors-v1","mh4g-planner-v1"];
const WORKER_URL="https://mh4g-sync.skhkil.workers.dev";
const CONF="mh4g-sync-config-v1",BASE="mh4g-sync-baseline-v1",BACKUP="mh4g-sync-backups-v1";
const fallback=()=>({favorites:{weapon:[],armor:[],recommend:[],quest:[]},craft:{},inventory:{}});
const parse=(s,d)=>{try{return JSON.parse(s)}catch{return d}};
const snapshot=()=>Object.fromEntries(KEYS.map((k,i)=>{const v=parse(localStorage.getItem(k),i===4?fallback():[]);return [k,v===null?(i===4?fallback():[]):v]}));
const signature=x=>JSON.stringify(x);
const config=()=>parse(localStorage.getItem(CONF),{})||{};
const saveConfig=x=>localStorage.setItem(CONF,JSON.stringify(x));
const status=(s,error=false)=>{const el=document.getElementById("mhSyncStatus");if(el){el.textContent=s;el.style.color=error?"#eea399":""}};
const btn=(s)=>document.getElementById(s);
let busy=false,paused=false,uploadTimer=null,pendingRefresh=false,lockReason="";
function backup(note){
  const stored=parse(localStorage.getItem(BACKUP),[]);
  const copies=Array.isArray(stored)?stored:[];
  copies.unshift({at:new Date().toISOString(),note,data:snapshot()});
  localStorage.setItem(BACKUP,JSON.stringify(copies.slice(0,3)));
}
function saveLocal(data){
  backup("클라우드 데이터 적용 전");
  for(const k of KEYS)localStorage.setItem(k,JSON.stringify(data[k]));
  localStorage.setItem(BASE,signature(data));
}
function arrayMerge(a,b){
  const result=Array.isArray(a)?structuredClone(a):[];
  const items=Array.isArray(b)?b:[];
  const byId=new Map(result.map((x,i)=>[String(x?.id||""),i]).filter(x=>x[0]));
  const fingerprints=new Set(result.map(signature));
  for(const item of items){
    const fp=signature(item);if(fingerprints.has(fp))continue;
    const id=String(item?.id||"");
    if(id&&byId.has(id)){
      const newItem=structuredClone(item);
      newItem.id="sync_"+crypto.randomUUID();
      if(typeof newItem.name==="string")newItem.name+=" (다른 기기)";
      result.push(newItem);
    }else{result.push(structuredClone(item));if(id)byId.set(id,result.length-1)}
    fingerprints.add(fp);
  }
  return result;
}
function mergeInitial(local,remote){
  const result={};for(const k of KEYS.slice(0,4))result[k]=arrayMerge(local[k],remote[k]);
  const l=local[KEYS[4]]||fallback(),r=remote[KEYS[4]]||fallback();
  result[KEYS[4]]={
    favorites:Object.fromEntries(["weapon","armor","recommend","quest"].map(k=>[k,[...new Set([...(r.favorites?.[k]||[]),...(l.favorites?.[k]||[])])] ])),
    craft:{...(r.craft||{}),...(l.craft||{})},
    inventory:{...(r.inventory||{}),...(l.inventory||{})}
  };
  return result;
}
async function api(method,body,codeOverride=null){
 const c=config(),code=codeOverride??c.code,url=WORKER_URL;
 if(!/^[a-zA-Z0-9_-]{43}$/.test(code||""))throw new Error("연결 코드가 올바르지 않습니다.");
 const res=await fetch(url+"/v1/sync",{method,headers:{"Authorization":"Bearer "+code,...(body?{"Content-Type":"application/json"}:{})},body:body?JSON.stringify(body):undefined,cache:"no-store"});
 let data;try{data=await res.json()}catch{throw new Error("서버 응답을 읽을 수 없습니다.")}
 if(res.status===409)throw Object.assign(new Error("다른 기기에서 먼저 저장했습니다. 동기화가 정지됐습니다. 아래 충돌 해결 버튼을 이용하세요."),{conflict:true});
 if(!res.ok)throw new Error(data.error||"서버 연결 오류 ("+res.status+")");
 return data;
}
function makeCode(){const b=crypto.getRandomValues(new Uint8Array(32));return btoa(String.fromCharCode(...b)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=/g,"")}
function connected(){const c=config();return Boolean(c.code)}
function setRevision(revision,data){const c=config();saveConfig({...c,revision});localStorage.setItem(BASE,signature(data))}
function lock(e){paused=true;lockReason=e.message||String(e);status(lockReason+" · 자동 동기화 중지. 충돌 해결을 눌러주세요.",true);btn("mhSyncResolve").hidden=false}
function editing(){const el=document.activeElement;return document.hasFocus()&&Boolean(el&&(el.matches?.("input,textarea,select,[contenteditable=true]")||el.isContentEditable))}
function tryRefresh(){if(!pendingRefresh||document.hidden||editing()||btn("mhSyncDialog")?.open)return;pendingRefresh=false;location.reload()}
function refreshSoon(){pendingRefresh=true;status("다른 기기의 변경을 받았습니다. 화면을 자동 갱신합니다.");tryRefresh()}
function scheduleSync(){if(!connected()||paused)return;clearTimeout(uploadTimer);uploadTimer=setTimeout(()=>{uploadTimer=null;if(busy){scheduleSync();return}void sync()},400)}
async function connect(newCode,requireExisting=false,requestedCode=""){
 if(busy){status("다른 동기화 작업이 끝난 후 다시 시도하세요.",true);return}
 busy=true;
 const priorConfig=config();
 try{
   const url=WORKER_URL;
   const code=newCode?makeCode():(requireExisting?requestedCode:btn("mhSyncCode").value).trim();
   if(!/^[A-Za-z0-9_-]{43}$/.test(code))throw new Error("연결 코드는 영문·숫자로 된 43자리여야 합니다.");
   if(requireExisting&&code===priorConfig.code)throw new Error("입력한 코드는 현재 모바일 연결 코드와 같습니다. PC의 연결 코드를 다시 확인하세요. 기존 연결은 변경되지 않았습니다.");
   // Check the target with the proposed code; never mutate the active configuration until the entire transfer succeeds.
   const remote=await api("GET",undefined,code);
   if(newCode&&remote.exists)throw new Error("새 연결 코드가 이미 사용 중입니다.");
   if(requireExisting&&!remote.exists)throw new Error("입력한 코드에 해당하는 클라우드 기록이 없습니다. 현재 모바일 연결은 유지됩니다.");
   if(requireExisting){
     const fp=await fingerprintCode(code);
     if(!confirm("전환할 클라우드의 연결 식별자: "+fp+"\n대상 클라우드 버전: "+remote.revision+
       "\n\nPC 연결 진단에 표시된 식별자와 정확히 같은지 확인하세요.\n다르면 취소를 누르세요. 이 연결로 전환하겠습니까?"))
       throw new Error("연결 전환을 취소했습니다. 기존 연결은 유지됩니다.");
   }
   const local=snapshot();let data=local,revision=remote.revision||0;
   if(remote.exists){
     const hasLocal=KEYS.slice(0,4).some(k=>Array.isArray(local[k])&&local[k].length)||
       Boolean(Object.keys(local[KEYS[4]]?.craft||{}).length||Object.keys(local[KEYS[4]]?.inventory||{}).length);
     if(hasLocal){
       if(!confirm("이 기기의 데이터와 대상 클라우드 데이터를 병합할까요?\n중복 ID의 장비는 복제하여 보존하고, 제작 수량/보유 소재의 충돌은 현재 기기 값을 우선합니다.\n변경 전 로컬 백업도 보존합니다."))
         throw new Error("연결을 취소했습니다. 기존 연결은 유지됩니다.");
       data=mergeInitial(local,remote.data);
     }else data=remote.data;
   }
   if(signature(snapshot())!==signature(local))throw new Error("전환 중 현재 기기 데이터가 변경됐습니다. 안전을 위해 중단했습니다.");
   // Always back up when switching, including when the merged data is identical.
   backup(requireExisting?"다른 클라우드로 연결 전환 전":"클라우드 연결 전");
   const updated=await api("PUT",{revision,data},code);
   if(signature(snapshot())!==signature(data))saveLocal(data);
   // Set the code only after the target GET/PUT and local write all succeeded.
   saveConfig({url,code,revision:updated.revision});
   localStorage.setItem(BASE,signature(data));
   btn("mhSyncCode").value=code;
   btn("mhSyncSwitchInput").value="";
   btn("mhSyncResolve").hidden=true;paused=false;lockReason="";
   status("연결 성공 · 자동 동기화 활성화 (버전 "+updated.revision+")");
   if(remote.exists)refreshSoon();
 }catch(e){status(e.message||String(e),true)}
 finally{busy=false;render()}
}
async function sync(manual=false){
 if(!connected()){if(manual)status("미연결 · 새 연결을 만들거나 기존 코드로 연결하세요.",true);return}
 if(paused){if(manual){status((lockReason||"동기화 충돌 발생")+" · 먼저 충돌 해결을 눌러주세요.",true);btn("mhSyncResolve").hidden=false}return}
 if(busy){if(manual)status("이미 동기화 작업이 진행 중입니다.");return}
 busy=true;
 if(manual)status("서버에 동기화 요청 중...");
 try{
   const current=snapshot(),base=localStorage.getItem(BASE),here=signature(current);
   const remote=await api("GET");
   if(signature(snapshot())!==here){scheduleSync();return}
   const localChanged=base!==here;
   if(!remote.exists){lock(new Error("클라우드 데이터가 사라졌습니다. 자동 덮어쓰기를 중지합니다."));return}
   const c=config(),remoteChanged=remote.revision!==c.revision;
   if(localChanged&&remoteChanged){lock(new Error("두 기기에서 동시에 변경했습니다. 자동 덮어쓰기를 중지합니다."));return}
   if(remoteChanged){
     // Do not overwrite changes made while the remote GET was in flight.
     if(signature(snapshot())!==here){scheduleSync();return}
     saveLocal(remote.data);setRevision(remote.revision,remote.data);
     refreshSoon();
   }else if(localChanged){
     const result=await api("PUT",{revision:c.revision,data:current});
     setRevision(result.revision,current);status("저장됨 · 버전 "+result.revision);
     if(signature(snapshot())!==here)scheduleSync();
   }else status("동기화됨 · 버전 "+c.revision);
 }catch(e){if(e.conflict)lock(e);else status("연결 오류 · 로컬 저장 유지: "+e.message,true)}
 finally{busy=false;render()}
}
async function resolve(){
 const decision=prompt("충돌 해결: 1 = 클라우드 데이터로 복원 (로컬 백업), 2 = 현재 기기 데이터로 클라우드 복구/덮어쓰기\n※ 2번은 클라우드를 덮어쓰므로 최신 데이터가 있는 기기에서만 실행하세요.\n취소하려면 빈칸 또는 취소");
 if(!["1","2"].includes(decision))return;
 if(busy)return;busy=true;
 try{
   const remote=await api("GET");
   if(decision==="1"){
     if(!remote.exists)throw new Error("클라우드에 복원할 데이터가 없습니다. 현재 기기의 데이터로 복구하려면 2를 선택하세요.");
     saveLocal(remote.data);setRevision(remote.revision,remote.data);refreshSoon();
   }else{
     if(!confirm(remote.exists?"현재 기기의 데이터를 클라우드에 덮어쓰시겠습니까? 다른 기기 변경 사항을 잃을 수 있습니다.":"클라우드 기록이 없습니다. 현재 기기의 로컬 데이터를 클라우드에 다시 생성할까요?"))return;
     backup("충돌 덮어쓰기/클라우드 복구 전");const data=snapshot();
     const v=await api("PUT",{revision:remote.exists?remote.revision:0,data});setRevision(v.revision,data);
   }
   paused=false;lockReason="";btn("mhSyncResolve").hidden=true;status("충돌 해결 완료 · 자동 동기화 재개");
 }catch(e){status(e.message,true)}finally{busy=false;render()}
}
async function fingerprintCode(code){
 if(!/^[A-Za-z0-9_-]{43}$/.test(code||""))return "미연결";
 const bytes=new TextEncoder().encode(code);
 const hash=await crypto.subtle.digest("SHA-256",bytes);
 return [...new Uint8Array(hash)].slice(0,6).map(b=>b.toString(16).padStart(2,"0")).join("").toUpperCase();
}
async function connectionFingerprint(){return fingerprintCode(config().code)}
function downloadLocalBackup(){
 try{
   const payload={format:"mh4g-sync-local-backup-v1",createdAt:new Date().toISOString(),data:snapshot()};
   const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json;charset=utf-8"});
   const url=URL.createObjectURL(blob),a=document.createElement("a");
   a.href=url;a.download="mh4g-local-backup-"+new Date().toISOString().slice(0,10)+".json";
   document.body.append(a);a.click();a.remove();
   setTimeout(()=>URL.revokeObjectURL(url),2000);
   status("현재 기기 데이터 JSON 백업 다운로드를 요청했습니다. 파일이 저장됐는지 확인하세요.");
 }catch(e){status("백업 생성 실패: "+(e?.message||String(e)),true)}
}
async function diagnose(){
 const el=btn("mhSyncDiagnostics");if(!el)return;
 if(!connected()){el.textContent="진단: 연결 코드가 없습니다. 기존 코드로 연결하거나 새 연결을 만드세요.";return}
 el.textContent="진단 중 · 서버 연결 확인...";
 let fingerprint="확인 실패";
 try{fingerprint=await connectionFingerprint()}catch{}
 const c=config(),local=snapshot();
 const pending=localStorage.getItem(BASE)!==signature(local);
 const summary="연결 식별자 "+fingerprint+" (PC·모바일에서 일치해야 함) · 이 기기 버전 "+(c.revision??"미설정")+
  " · 로컬 변경 "+(pending?"있음":"없음")+
  " · 자동 동기화 "+(paused?"중지":"활성")+
  " · 저장 세팅 "+(Array.isArray(local["mh4g-builds-v1"])?local["mh4g-builds-v1"].length:0)+"건"+
  " · 보유 호석 "+(Array.isArray(local["mh4g-owned-charms-v1"])?local["mh4g-owned-charms-v1"].length:0)+"개";
 try{
   const remote=await api("GET");
   el.textContent=summary+" · 서버 응답 정상 · 클라우드 "+(remote.exists?"존재 (버전 "+remote.revision+")":"없음")+(paused?" · 충돌 해결 필요":"");
 }catch(e){el.textContent=summary+" · 서버 진단 실패: "+(e?.message||String(e))}
}
function render(){
 const c=config(),active=connected();
 // The active code is read-only; switching uses an independent input that polling never overwrites.
 if(active)btn("mhSyncCode").value=c.code;
 btn("mhSyncCode").readOnly=active;
 btn("mhSyncSwitchArea").hidden=!active;
 btn("mhSyncCreate").hidden=active;btn("mhSyncJoin").hidden=active;
 btn("mhSyncSwitch").hidden=!active;btn("mhSyncDisconnect").hidden=!active;
 btn("mhSyncNow").hidden=!active;btn("mhSyncCheck").hidden=!active;
}

// Import explicitly selected owned charms from a one-time URL fragment.
// Keeps unrelated charms intact, replaces matching old values, and deduplicates repeated imports.
function importOwnedCharmLink(){
 const match=location.hash.match(/^#mh4g-charm-import=([A-Za-z0-9_-]{16,8192})$/);
 if(!match)return;
 const clearLink=()=>history.replaceState(history.state,"",location.pathname+location.search);
 try{
   const decoded=atob(match[1].replace(/-/g,"+").replace(/_/g,"/"));
   const payload=JSON.parse(decoded);
   if(payload?.v!==1||!Array.isArray(payload.p)||payload.p.length<1||payload.p.length>30)throw new Error("호석 데이터 형식이 올바르지 않습니다.");
   const parseSkills=entries=>{
     if(!Array.isArray(entries)||entries.length<1||entries.length>2)throw new Error("스킬 수가 올바르지 않습니다.");
     const result={};
     for(const pair of entries){
       if(!Array.isArray(pair)||pair.length!==2||!/^skill_[a-f0-9]{12}$/.test(pair[0])||!Number.isInteger(pair[1])||pair[1]===0||Math.abs(pair[1])>40||Object.hasOwn(result,pair[0]))throw new Error("스킬 ID 또는 포인트 값이 잘못되었습니다.");
       result[pair[0]]=pair[1];
     }
     return result;
   };
   const key="mh4g-owned-charms-v1",original=parse(localStorage.getItem(key),[]);
   if(!Array.isArray(original))throw new Error("보유 호석 저장소가 손상되었습니다.");
   const list=structuredClone(original);
   const sig=(skills,slots)=>JSON.stringify([Object.entries(skills||{}).filter(([,v])=>Number(v)!==0).map(([k,v])=>[k,Number(v)]).sort((a,b)=>a[0].localeCompare(b[0])),Number(slots)||0]);
   let replaced=0,added=0,already=0,removedOld=0;
   for(let i=0;i<payload.p.length;i++){
     const row=payload.p[i];
     if(!Array.isArray(row)||row.length!==3||!Number.isInteger(row[0])||row[0]<0||row[0]>3)throw new Error("기존 호석 슬롯 형식이 잘못되었습니다.");
     const oldSkills=parseSkills(row[1]),newSkills=parseSkills(row[2]);
     const oldSignature=sig(oldSkills,row[0]),newSignature=sig(newSkills,3);
     const previous=list.findIndex(c=>sig(c?.skills,c?.slots)===oldSignature);
     const hasNew=list.some(c=>sig(c?.skills,c?.slots)===newSignature);
     if(previous!==-1){
       if(hasNew){list.splice(previous,1);removedOld++;}
       else{list[previous]={...list[previous],skills:newSkills,slots:3};replaced++;}
     }else if(hasNew)already++;
     else{list.push({id:"charm_import_"+Date.now()+"_"+i,skills:newSkills,slots:3});added++;}
   }
   if(!confirm("보유 호석 "+payload.p.length+"개를 현재 목록에 반영할까요?\n기존 원본 호석은 교체하고, 등록되지 않은 호석은 추가합니다.\n다른 호석과 저장 세팅은 보존하며 변경 전 백업을 남깁니다.")){clearLink();return;}
   const changed=replaced+added+removedOld;
   if(changed){
     backup("호석 링크 가져오기 전");
     localStorage.setItem(key,JSON.stringify(list));
     window.dispatchEvent(new Event("mh4g:sync-change"));
   }
   clearLink();
   alert("보유 호석 반영 완료\n교체 "+replaced+"개 · 신규 "+added+"개 · 기존 중복 정리 "+removedOld+"개 · 이미 등록 "+already+"개\n총 "+list.length+"개. 변경 내용을 화면에 반영합니다.");
   if(changed)location.reload();
 }catch(e){clearLink();alert("호석 가져오기 실패: "+(e?.message||String(e)));}
}

function init(){
 const button=document.createElement("button");button.type="button";button.textContent="☁ 세팅 동기화";button.id="mhSyncOpen";button.style.cssText="margin-left:auto;cursor:pointer;padding:8px 12px;border-radius:8px;border:1px solid #64748b;background:transparent;color:inherit;white-space:nowrap";
 (document.querySelector(".topbar")||document.body).append(button);
 const panel=document.createElement("dialog");panel.id="mhSyncDialog";panel.style.cssText="box-sizing:border-box;max-width:min(94vw,510px);width:100%;max-height:86dvh;overflow-y:auto;border:1px solid #64748b;border-radius:12px;padding:20px;color:#e5e7eb;background:#1d2530;box-shadow:0 20px 60px #0009";
 panel.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;gap:12px"><h2 style="margin:0;font-size:clamp(18px,5vw,24px);line-height:1.35;min-width:0">☁ 세팅 자동 동기화</h2><button type="button" id="mhSyncClose">닫기 ×</button></div>'+
 '<p style="font-size:13px;line-height:1.55">Google 로그인 없이 회사 PC와 모바일을 연결합니다. 최초 1회 연결 코드 입력 후 자동 동기화됩니다. 연결 코드는 비밀번호와 같으니 타인에게 공개하지 마세요.</p>'+
 '<label style="display:block;margin:12px 0">현재 연결 코드 (연결 중에는 읽기 전용)<input id="mhSyncCode" type="password" placeholder="연결되지 않은 경우 입력할 43자리 코드" autocomplete="off" style="box-sizing:border-box;width:100%;padding:10px;margin-top:5px;font-family:monospace"></label>'+
 '<div id="mhSyncSwitchArea" hidden><label style="display:block;margin:12px 0">전환할 다른 기기의 연결 코드 (43자리)<input id="mhSyncSwitchInput" type="password" placeholder="PC에서 복사한 코드 붙여넣기" autocomplete="off" style="box-sizing:border-box;width:100%;padding:10px;margin-top:5px;font-family:monospace"></label><p style="font-size:12px;margin-top:0">이 칸은 자동 동기화 중에도 지워지지 않습니다. 전환 전에 대상 연결 식별자를 확인합니다.</p></div>'+
 '<div id="mhSyncStatus" role="status" style="font-size:13px;min-height:32px">미연결 · 현재 세팅은 기존처럼 이 브라우저에 저장됩니다.</div>'+
 '<div style="display:flex;gap:8px;flex-wrap:wrap"><button id="mhSyncCreate">새 연결 만들기</button><button id="mhSyncJoin">기존 코드로 연결</button><button id="mhSyncSwitch" hidden>기존 코드로 안전하게 전환</button><button id="mhSyncCopy">코드 복사</button><button id="mhSyncNow" hidden>지금 동기화</button><button id="mhSyncCheck" hidden>연결 진단</button><button id="mhSyncDownload">이 기기 데이터 백업(JSON)</button><button id="mhSyncResolve" hidden>충돌 해결</button><button id="mhSyncDisconnect" hidden>연결 해제</button></div>'+ 
 '<div id="mhSyncDiagnostics" role="status" style="font-size:12px;line-height:1.5;margin-top:10px;overflow-wrap:anywhere"></div>'+
 '<p style="font-size:12px;line-height:1.5;margin-top:13px">동기화: 저장 세팅 · 보유 호석 · 발굴무기 · 발굴방어구 · 즐겨찾기/제작 목록. 로컬 백업은 적용 직전 보관됩니다. 동시 수정 충돌 시 자동 동기화를 중지합니다.</p>';
 document.body.append(panel);
 btn("mhSyncOpen").onclick=()=>{render();if(paused)status((lockReason||"동기화 충돌")+" · 충돌 해결이 필요합니다.",true);panel.showModal()};
 btn("mhSyncClose").onclick=()=>{panel.close();tryRefresh()};
 btn("mhSyncCreate").onclick=()=>connect(true);
 btn("mhSyncJoin").onclick=()=>connect(false);
 btn("mhSyncSwitch").onclick=()=>{
   const candidate=btn("mhSyncSwitchInput").value.trim();
   if(!/^[A-Za-z0-9_-]{43}$/.test(candidate)){status("전환할 PC 연결 코드를 별도 입력칸에 43자리로 붙여넣으세요.",true);return}
   if(candidate===config().code){status("전환할 코드가 현재 연결과 같습니다. PC에서 복사한 코드인지 확인하세요.",true);return}
   void connect(false,true,candidate);
 };
 btn("mhSyncDownload").onclick=downloadLocalBackup;
 btn("mhSyncNow").onclick=()=>{void sync(true)};
 btn("mhSyncCheck").onclick=()=>{void diagnose()};
 btn("mhSyncResolve").onclick=resolve;
 btn("mhSyncDisconnect").onclick=()=>{if(confirm("연결 정보를 이 기기에서 해제할까요? 로컬 세팅은 유지됩니다. 연결 코드를 잃으면 클라우드 복구가 어려울 수 있습니다.")){localStorage.removeItem(CONF);localStorage.removeItem(BASE);paused=false;lockReason="";status("연결 해제됨");render()}};
 btn("mhSyncCopy").onclick=async()=>{const code=config().code;if(!code){status("연결된 코드가 없습니다.",true);return}try{await navigator.clipboard.writeText(code);status("현재 연결 코드 복사됨")}catch{btn("mhSyncCode").select();status("현재 코드가 선택됐습니다. 직접 복사하세요.")}};
 render();
 // Save/delete actions push after a short debounce; polling pulls changes from other devices.
 window.addEventListener("mh4g:sync-change",scheduleSync);
 window.addEventListener("storage",e=>{if(KEYS.includes(e.key))scheduleSync()});
 setInterval(()=>{if(!document.hidden)void sync()},10000);
 document.addEventListener("visibilitychange",()=>{if(!document.hidden){void sync();tryRefresh()}});
 window.addEventListener("focus",()=>{void sync();tryRefresh()});
 document.addEventListener("focusout",()=>setTimeout(tryRefresh,0));
 panel.addEventListener("close",tryRefresh);
 if(connected()){status("기존 연결 발견 · 동기화 확인 중");setTimeout(sync,1200)}
 importOwnedCharmLink();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();
