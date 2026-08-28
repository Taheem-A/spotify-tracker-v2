export function duration(ms:number|null|undefined){if(ms==null)return '—';const s=Math.round(ms/1000),h=Math.floor(s/3600),m=Math.floor((s%3600)/60),r=s%60;return h?`${h}h ${m}m`:`${m}:${String(r).padStart(2,'0')}`}
export function hours(ms:number|null|undefined){if(ms==null)return '—';const h=ms/3600000;return h>=10?`${h.toFixed(0)}h ${Math.round((h%1)*60)}m`:`${h.toFixed(1)}h`}
export function when(v:string|null|undefined){if(!v)return '—';return new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(v))}
export function pct(v:number|null|undefined){return v==null?'—':`${Math.round(v*100)}%`}
