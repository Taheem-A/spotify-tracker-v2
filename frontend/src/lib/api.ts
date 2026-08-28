const BASE = 'http://127.0.0.1:8765/api';
export async function api<T>(path:string, init?:RequestInit):Promise<T>{
 const r=await fetch(BASE+path,init); if(!r.ok) throw new Error(await r.text()); return r.json();
}
export function qs(values:Record<string,string|number|undefined|null>){ const p=new URLSearchParams(); Object.entries(values).forEach(([k,v])=>{if(v!==undefined&&v!==null&&v!=='')p.set(k,String(v))}); const s=p.toString(); return s?'?'+s:'' }
export async function upload(path:string,file:File){const f=new FormData();f.append('file',file);return api<any>(path,{method:'POST',body:f})}
