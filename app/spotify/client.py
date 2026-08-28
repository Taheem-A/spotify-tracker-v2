from __future__ import annotations
import httpx, asyncio
from app.auth.pkce import access_token

BASE="https://api.spotify.com/v1"
async def get(path:str,params=None):
    token=await access_token()
    if not token: return None
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.get(BASE+path,headers={"Authorization":f"Bearer {token}"},params=params)
        if r.status_code==204: return None
        if r.status_code==429:
            await asyncio.sleep(min(int(r.headers.get("Retry-After","1")),30)); return None
        r.raise_for_status(); return r.json()

async def current_playback(): return await get("/me/player")
async def recently_played(limit=50,after=None):
    params={"limit":min(max(limit,1),50)}
    if after is not None: params["after"]=after
    return await get("/me/player/recently-played",params)
