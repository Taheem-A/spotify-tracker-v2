from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from app.config import settings
from app.database.db import connect
from app.importers.extended_history import validate_package, import_package
from app.analytics.service import overview, history, entity_list, track_detail, artist_detail, album_detail
from app.auth.pkce import create_authorization_url, exchange_code, access_token
from app.spotify.client import current_playback
from app.services.maintenance import backup, diagnostics, export_data

router=APIRouter(prefix="/api")
class FlagBody(BaseModel): enabled: bool

@router.get("/health")
def health(): return {"ok":True,"version":settings.app_version}
@router.get("/config")
def config(): return {"timezone":settings.user_timezone,"derived_metrics":settings.enable_derived_listening_metrics,"spotify_client_configured":bool(settings.spotify_client_id)}
@router.get("/overview")
def get_overview(start:str|None=None,end:str|None=None): return overview(start,end)
@router.get("/history")
def get_history(q:str="",limit:int=100,offset:int=0,start:str|None=None,end:str|None=None): return history(q,min(limit,500),offset,start,end)
@router.get("/tracks")
def tracks(): return entity_list("tracks")
@router.get("/artists")
def artists(): return entity_list("artists")
@router.get("/albums")
def albums(): return entity_list("albums")
@router.get("/albums/{album_id}")
def album(album_id:int):
    d=album_detail(album_id)
    if not d: raise HTTPException(404)
    return d

@router.get("/tracks/{track_id}")
def track(track_id:int):
    d=track_detail(track_id)
    if not d: raise HTTPException(404); return d
    return d
@router.get("/artists/{artist_id}")
def artist(artist_id:int):
    d=artist_detail(artist_id)
    if not d: raise HTTPException(404)
    return d
@router.post("/imports/validate")
async def validate_import(file:UploadFile=File(...)):
    data=await file.read(); return validate_package(file.filename or "upload",data)
@router.post("/imports/run")
async def run_import(file:UploadFile=File(...)):
    data=await file.read(); return import_package(file.filename or "upload",data)
@router.get("/imports")
def imports():
    with connect() as con: return [dict(r) for r in con.execute("SELECT * FROM import_batch ORDER BY imported_at DESC LIMIT 100")]
@router.get("/data/diagnostics")
def diag(): return diagnostics()
@router.post("/data/backup")
def make_backup(): return backup()
@router.get("/data/export/{fmt}")
def export(fmt:str):
    if fmt not in {"json","csv"}: raise HTTPException(400,"format must be json or csv")
    body,mime=export_data(fmt); return Response(body,media_type=mime,headers={"Content-Disposition":f'attachment; filename="tracker-export.{fmt}"'})
@router.get("/data/raw")
def raw(limit:int=100,offset:int=0):
    with connect() as con: return [dict(r) for r in con.execute("SELECT id,import_batch_id,source_fingerprint,ingested_at,raw_json FROM raw_export_event ORDER BY id DESC LIMIT ? OFFSET ?",(min(limit,500),offset))]
@router.get("/spotify/status")
async def spotify_status(): return {"connected":bool(await access_token()),"client_configured":bool(settings.spotify_client_id)}
@router.get("/spotify/connect")
def connect_spotify():
    if not settings.spotify_client_id: raise HTTPException(400,"Set SPOTIFY_CLIENT_ID first")
    url,_=create_authorization_url(); return {"url":url}
@router.get("/auth/callback")
async def callback(code:str,state:str|None=None,error:str|None=None):
    if error:
        raise HTTPException(400,f"Spotify authorization failed: {error}")
    try:
        await exchange_code(code,state)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400,str(exc)) from exc
    return RedirectResponse("http://127.0.0.1:5173/settings?spotify=connected")
@router.get("/spotify/now-playing")
async def now_playing(): return await current_playback()
@router.post("/settings/derived-metrics")
def set_derived(body:FlagBody):
    # Runtime setting is environment/config authoritative. Persist user's requested preference separately.
    from datetime import datetime, timezone
    with connect() as con: con.execute("INSERT INTO app_setting(key,value,updated_at) VALUES('requested_derived_metrics',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(str(body.enabled).lower(),datetime.now(timezone.utc).isoformat()))
    settings.enable_derived_listening_metrics = body.enabled
    return {"requested":body.enabled,"effective":settings.enable_derived_listening_metrics,"restart_required":False}
