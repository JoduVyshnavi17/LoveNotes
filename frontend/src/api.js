const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8001';
export async function api(path,{method='GET',body,headers={}}={}){
 const h={...headers}; const t=localStorage.getItem('nm_token'); if(t)h.Authorization=`Bearer ${t}`;
 if(body && !(body instanceof FormData))h['Content-Type']='application/json';
 const r=await fetch(API+path,{method,headers:h,body:body instanceof FormData?body:body?JSON.stringify(body):undefined});
 if(!r.ok){let msg=`Request failed (${r.status})`;try{msg=(await r.json()).detail||msg}catch{}throw new Error(msg)}
 const type=r.headers.get('content-type')||'';return type.includes('application/json')?r.json():r.blob();
}
