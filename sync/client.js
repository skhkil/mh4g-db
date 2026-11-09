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
let busy=false,paused=false,uploadTimer=null,pendingRefresh=false;
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
async function api(method,body){
 const c=config(),url=WORKER_URL;
 if(!/^[a-zA-Z0-9_-]{43}$/.test(c.code||""))throw new Error("연결 코드가 올바르지 않습니다.");
 const res=await fetch(url+"/v1/sync",{method,headers:{"Authorization":"Bearer "+c.code,...(body?{"Content-Type":"application/json"}:{})},body:body?JSON.stringify(body):undefined,cache:"no-store"});
 let data;try{data=await res.json()}catch{throw new Error("서버 응답을 읽을 수 없습니다.")}
 if(res.status===409)throw Object.assign(new Error("다른 기기에서 먼저 저장했습니다. 동기화가 정지됐습니다. 아래 충돌 해결 버튼을 이용하세요."),{conflict:true});
 if(!res.ok)throw new Error(data.error||"서버 연결 오류 ("+res.status+")");
 return data;
}
function makeCode(){const b=crypto.getRandomValues(new Uint8Array(32));return btoa(String.fromCharCode(...b)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=/g,"")}
function connected(){const c=config();return Boolean(c.code)}
function setRevision(revision,data){const c=config();saveConfig({...c,revision});localStorage.setItem(BASE,signature(data))}
function lock(e){paused=true;status(e.message||String(e),true);btn("mhSyncResolve").hidden=false}
function editing(){const el=document.activeElement;return document.hasFocus()&&Boolean(el&&(el.matches?.("input,textarea,select,[contenteditable=true]")||el.isContentEditable))}
function tryRefresh(){if(!pendingRefresh||document.hidden||editing()||btn("mhSyncDialog")?.open)return;pendingRefresh=false;location.reload()}
function refreshSoon(){pendingRefresh=true;status("다른 기기의 변경을 받았습니다. 화면을 자동 갱신합니다.");tryRefresh()}
function scheduleSync(){if(!connected()||paused)return;clearTimeout(uploadTimer);uploadTimer=setTimeout(()=>{uploadTimer=null;if(busy){scheduleSync();return}void sync()},400)}
async function connect(newCode){
 if(busy)return;busy=true;
 const priorConfig=config();
 try{
   const url=WORKER_URL,code=newCode?makeCode():btn("mhSyncCode").value.trim();
   if(!/^[A-Za-z0-9_-]{43}$/.test(code))throw new Error("연결 코드는 43자리여야 합니다.");
   saveConfig({url,code,revision:0});
   const remote=await api("GET");
   if(newCode&&remote.exists)throw new Error("연결 코드가 이미 사용 중입니다.");
   const local=snapshot();let data=local,revision=remote.revision||0;
   if(remote.exists){
     const hasLocal=KEYS.slice(0,4).some(k=>Array.isArray(local[k])&&local[k].length)||
       Boolean(Object.keys(local[KEYS[4]]?.craft||{}).length||Object.keys(local[KEYS[4]]?.inventory||{}).length);
     if(hasLocal){
       if(!confirm("이 기기의 데이터와 클라우드 데이터를 병합할까요?\n중복 ID의 장비는 복제하여 보존하고, 제작 수량/보유 소재의 충돌은 현재 기기 값을 우선합니다.\n변경 전 로컬 백업도 보존합니다."))throw new Error("연결을 취소했습니다.");
       data=mergeInitial(local,remote.data); // remote copy remains on server until PUT succeeds
     }else{data=remote.data}
   }
   const updated=await api("PUT",{revision,data});revision=updated.revision;
   if(signature(snapshot())!==signature(data))saveLocal(data);
   setRevision(revision,data);
   btn("mhSyncCode").value=code;btn("mhSyncResolve").hidden=true;paused=false;
   status("연결됨 · 자동 동기화 활성화 (버전 "+revision+")");
   if(remote.exists)refreshSoon();
 }catch(e){saveConfig(priorConfig);status(e.message,true)}
 finally{busy=false;render()}
}
async function sync(){
 if(busy||paused||!connected())return;
 busy=true;
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
 const decision=prompt("충돌 해결: 1 = 클라우드 데이터로 복원 (현재 로컬 자동 백업), 2 = 로컬 데이터로 클라우드 덮어쓰기\n취소하려면 빈칸 또는 취소");
 if(!["1","2"].includes(decision))return;
 if(busy)return;busy=true;
 try{
   const remote=await api("GET");if(!remote.exists)throw new Error("원격 데이터 없음");
   if(decision==="1"){saveLocal(remote.data);setRevision(remote.revision,remote.data);refreshSoon();}
   else{backup("충돌 덮어쓰기 전");const data=snapshot();const v=await api("PUT",{revision:remote.revision,data});setRevision(v.revision,data)}
   paused=false;btn("mhSyncResolve").hidden=true;status("충돌 해결 완료");
 }catch(e){status(e.message,true)}finally{busy=false;render()}
}
function render(){
 const c=config();
 if(connected()){btn("mhSyncCode").value=c.code;btn("mhSyncCreate").hidden=true;btn("mhSyncJoin").hidden=true;btn("mhSyncDisconnect").hidden=false;btn("mhSyncNow").hidden=false}
 else{btn("mhSyncCreate").hidden=false;btn("mhSyncJoin").hidden=false;btn("mhSyncDisconnect").hidden=true;btn("mhSyncNow").hidden=true}
}
function init(){
 const button=document.createElement("button");button.type="button";button.textContent="☁ 세팅 동기화";button.id="mhSyncOpen";button.style.cssText="margin-left:auto;cursor:pointer;padding:8px 12px;border-radius:8px;border:1px solid #64748b;background:transparent;color:inherit;white-space:nowrap";
 (document.querySelector(".topbar")||document.body).append(button);
 const panel=document.createElement("dialog");panel.id="mhSyncDialog";panel.style.cssText="box-sizing:border-box;max-width:min(94vw,510px);width:100%;max-height:86dvh;overflow-y:auto;border:1px solid #64748b;border-radius:12px;padding:20px;color:#e5e7eb;background:#1d2530;box-shadow:0 20px 60px #0009";
 panel.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;gap:12px"><h2 style="margin:0;font-size:clamp(18px,5vw,24px);line-height:1.35;min-width:0">☁ 세팅 자동 동기화</h2><button type="button" id="mhSyncClose">닫기 ×</button></div>'+
 '<p style="font-size:13px;line-height:1.55">Google 로그인 없이 회사 PC와 모바일을 연결합니다. 최초 1회 연결 코드 입력 후 자동 동기화됩니다. 연결 코드는 비밀번호와 같으니 타인에게 공개하지 마세요.</p>'+
 '<label style="display:block;margin:12px 0">연결 코드<input id="mhSyncCode" type="password" placeholder="다른 기기에서 받은 43자리 코드" autocomplete="off" style="box-sizing:border-box;width:100%;padding:10px;margin-top:5px;font-family:monospace"></label>'+
 '<div id="mhSyncStatus" role="status" style="font-size:13px;min-height:32px">미연결 · 현재 세팅은 기존처럼 이 브라우저에 저장됩니다.</div>'+
 '<div style="display:flex;gap:8px;flex-wrap:wrap"><button id="mhSyncCreate">새 연결 만들기</button><button id="mhSyncJoin">기존 코드로 연결</button><button id="mhSyncCopy">코드 복사</button><button id="mhSyncNow" hidden>지금 동기화</button><button id="mhSyncResolve" hidden>충돌 해결</button><button id="mhSyncDisconnect" hidden>연결 해제</button></div>'+
 '<p style="font-size:12px;line-height:1.5;margin-top:13px">동기화: 저장 세팅 · 보유 호석 · 발굴무기 · 발굴방어구 · 즐겨찾기/제작 목록. 로컬 백업은 적용 직전 보관됩니다. 동시 수정 충돌 시 자동 동기화를 중지합니다.</p>';
 document.body.append(panel);
 btn("mhSyncOpen").onclick=()=>{render();panel.showModal()};
 btn("mhSyncClose").onclick=()=>{panel.close();tryRefresh()};
 btn("mhSyncCreate").onclick=()=>connect(true);
 btn("mhSyncJoin").onclick=()=>connect(false);
 btn("mhSyncNow").onclick=()=>sync();
 btn("mhSyncResolve").onclick=resolve;
 btn("mhSyncDisconnect").onclick=()=>{if(confirm("연결 정보를 이 기기에서 해제할까요? 로컬 세팅은 유지됩니다. 연결 코드를 잃으면 클라우드 복구가 어려울 수 있습니다.")){localStorage.removeItem(CONF);localStorage.removeItem(BASE);paused=false;status("연결 해제됨");render()}};
 btn("mhSyncCopy").onclick=async()=>{const code=btn("mhSyncCode").value;if(!code)return;try{await navigator.clipboard.writeText(code);status("연결 코드 복사됨")}catch{btn("mhSyncCode").select();status("코드가 선택됐습니다. 직접 복사하세요.")}};
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
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();
