// MH4G sync API. Deploy as Cloudflare Worker with D1 binding "DB".
// The connection code is a 256-bit bearer secret. Anyone with the code can access the saved data.
const HEADERS = {"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
const ALLOWED_KEYS = ["mh4g-builds-v1","mh4g-owned-charms-v1","mh4g-owned-relic-weapons-v1","mh4g-owned-relic-armors-v1","mh4g-planner-v1"];
function response(data,status=200,origin="") {
  return new Response(JSON.stringify(data),{status,headers:{...HEADERS,...(origin?{"Access-Control-Allow-Origin":origin,"Vary":"Origin"}:{})}});
}
export default {
 async fetch(request,env) {
  const origin=request.headers.get("Origin")||"";
  const allowed=env.ALLOWED_ORIGIN||"https://skhkil.github.io";
  const cors=origin===allowed?origin:"";
  if(request.method==="OPTIONS") {
    if(!cors)return new Response(null,{status:403});
    return new Response(null,{status:204,headers:{"Access-Control-Allow-Origin":cors,"Access-Control-Allow-Methods":"GET,PUT,OPTIONS","Access-Control-Allow-Headers":"Authorization,Content-Type","Access-Control-Max-Age":"3600","Vary":"Origin"}});
  }
  const u=new URL(request.url);
  if(u.pathname==="/health"&&request.method==="GET")return response({ok:true,service:"mh4g-sync"});
  if(u.pathname!=="/v1/sync")return response({error:"not_found"},404,cors);
  if(!cors)return response({error:"origin_denied"},403,cors);
  if(!env.DB)return response({error:"db_not_configured"},503,cors);
  const token=(request.headers.get("Authorization")||"").replace(/^Bearer /i,"").trim();
  if(!/^[A-Za-z0-9_-]{43}$/.test(token))return response({error:"invalid_connection_code"},401,cors);
  const secret=Uint8Array.from(atob(token.replace(/-/g,"+").replace(/_/g,"/")+"="),c=>c.charCodeAt(0));
  if(secret.length!==32)return response({error:"invalid_connection_code"},401,cors);
  const digest=await crypto.subtle.digest("SHA-256",secret);
  const id=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("");
  if(request.method==="GET"){
    const row=await env.DB.prepare("SELECT payload,revision,updated_at FROM sync_records WHERE id=?").bind(id).first();
    if(!row)return response({exists:false,revision:0},200,cors);
    return response({exists:true,revision:row.revision,updatedAt:row.updated_at,data:JSON.parse(row.payload)},200,cors);
  }
  if(request.method!=="PUT")return response({error:"method_not_allowed"},405,cors);
  if(Number(request.headers.get("Content-Length")||0)>450000)return response({error:"payload_too_large"},413,cors);
  let body;
  try {
    const raw=await request.text();
    if(new TextEncoder().encode(raw).byteLength>450000)return response({error:"payload_too_large"},413,cors);
    body=JSON.parse(raw);
  }catch{return response({error:"invalid_json"},400,cors)}
  if(!Number.isSafeInteger(body.revision)||body.revision<0||!body.data||typeof body.data!=="object"||Array.isArray(body.data))
    return response({error:"invalid_payload"},400,cors);
  const keys=Object.keys(body.data);
  if(keys.length!==ALLOWED_KEYS.length||keys.some(k=>!ALLOWED_KEYS.includes(k))||ALLOWED_KEYS.some(k=>!Array.isArray(body.data[k])&&k!=="mh4g-planner-v1"))
    return response({error:"invalid_storage_keys"},400,cors);
  if(!body.data["mh4g-planner-v1"]||typeof body.data["mh4g-planner-v1"]!=="object"||Array.isArray(body.data["mh4g-planner-v1"]))
    return response({error:"invalid_planner"},400,cors);
  const payload=JSON.stringify(body.data),revision=body.revision+1;
  if(new TextEncoder().encode(payload).byteLength>440000)return response({error:"payload_too_large"},413,cors);
  const updatedAt=new Date().toISOString();
  const result=await env.DB.prepare("INSERT INTO sync_records (id,payload,revision,updated_at) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision,updated_at=excluded.updated_at WHERE sync_records.revision=?").bind(id,payload,revision,updatedAt,body.revision).run();
  if(result.meta?.changes!==1){
    const row=await env.DB.prepare("SELECT revision FROM sync_records WHERE id=?").bind(id).first();
    return response({error:"revision_conflict",revision:row?.revision||0},409,cors);
  }
  return response({ok:true,revision,updatedAt},200,cors);
 }
};
