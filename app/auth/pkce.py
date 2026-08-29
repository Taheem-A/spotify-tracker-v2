from __future__ import annotations
import base64, hashlib, secrets, time
from urllib.parse import urlencode
import httpx
from app.config import settings
from app.database.db import connect

AUTHORIZE="https://accounts.spotify.com/authorize"; TOKEN="https://accounts.spotify.com/api/token"
SCOPES="user-read-currently-playing user-read-playback-state user-read-recently-played"
_verifier: str|None=None
_pending_state: str|None=None

def create_authorization_url():
    global _verifier, _pending_state
    _verifier=base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge=base64.urlsafe_b64encode(hashlib.sha256(_verifier.encode()).digest()).decode().rstrip("=")
    _pending_state=secrets.token_urlsafe(24)
    params={"client_id":settings.spotify_client_id,"response_type":"code","redirect_uri":settings.spotify_redirect_uri,"scope":SCOPES,"code_challenge_method":"S256","code_challenge":challenge,"state":_pending_state}
    return AUTHORIZE+"?"+urlencode(params),_pending_state

async def exchange_code(code:str,state:str|None):
    global _verifier, _pending_state
    if not _verifier or not _pending_state:
        raise RuntimeError("PKCE authorization state missing; restart authorization")
    if not state or not secrets.compare_digest(state,_pending_state):
        _verifier=None; _pending_state=None
        raise ValueError("Spotify OAuth state mismatch")
    verifier=_verifier
    _verifier=None; _pending_state=None
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.post(TOKEN,data={"client_id":settings.spotify_client_id,"grant_type":"authorization_code","code":code,"redirect_uri":settings.spotify_redirect_uri,"code_verifier":verifier}); r.raise_for_status(); token=r.json()
    _store(token); return token

def _store(token):
    expires_at=int(time.time())+int(token.get("expires_in",3600))-30
    with connect() as con:
        old=con.execute("SELECT refresh_token FROM oauth_token WHERE id=1").fetchone()
        refresh=token.get("refresh_token") or (old[0] if old else None)
        con.execute("INSERT INTO oauth_token(id,access_token,refresh_token,expires_at,scope,token_type) VALUES(1,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET access_token=excluded.access_token,refresh_token=excluded.refresh_token,expires_at=excluded.expires_at,scope=excluded.scope,token_type=excluded.token_type",(token.get("access_token"),refresh,expires_at,token.get("scope"),token.get("token_type")))

async def access_token() -> str|None:
    with connect() as con: row=con.execute("SELECT * FROM oauth_token WHERE id=1").fetchone()
    if not row or not row["access_token"]: return None
    if row["expires_at"] and row["expires_at"] > int(time.time()): return row["access_token"]
    if not row["refresh_token"]: return None
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.post(TOKEN,data={"client_id":settings.spotify_client_id,"grant_type":"refresh_token","refresh_token":row["refresh_token"]}); r.raise_for_status(); token=r.json()
    _store(token); return token.get("access_token")
