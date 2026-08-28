from __future__ import annotations
import hashlib, json, zipfile, io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app import __version__
from app.database.db import transaction
from app.normalization.extended_history import normalize_export_row
from app.reconciliation.engine import create_canonical_from_normalized, match_provisional

IMPORTER_VERSION = "1"

def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

def fingerprint(row: dict[str, Any]) -> str:
    keys = ["ts","endTime","spotify_track_uri","spotify_episode_uri","ms_played","msPlayed","platform","reason_start","reason_end","shuffle","skipped","offline","offline_timestamp","incognito_mode"]
    return hashlib.sha256(json.dumps({k:row.get(k) for k in keys}, sort_keys=True, separators=(",",":"), default=str).encode()).hexdigest()

def _extract_json_files(name: str, data: bytes) -> list[tuple[str, bytes]]:
    if zipfile.is_zipfile(io.BytesIO(data)):
        out=[]
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in z.namelist():
                if n.lower().endswith(".json") and not n.endswith("/"):
                    out.append((n,z.read(n)))
        return out
    return [(name,data)]

def _parse_rows(data: bytes) -> list[dict[str,Any]]:
    obj=json.loads(data.decode("utf-8-sig"))
    if isinstance(obj,list): return [x for x in obj if isinstance(x,dict)]
    if isinstance(obj,dict):
        for key in ("items","streams","history"):
            if isinstance(obj.get(key),list): return [x for x in obj[key] if isinstance(x,dict)]
    raise ValueError("JSON does not contain a streaming-history array")

def _upsert_entities(con, n: dict[str,Any]) -> tuple[int|None,int|None]:
    if n["content_type"] == "track":
        uri=n.get("track_uri")
        album_id=None
        if n.get("album_name"):
            row=con.execute("SELECT id FROM album WHERE name=? AND spotify_uri IS NULL",(n["album_name"],)).fetchone()
            if row: album_id=row[0]
            else: album_id=con.execute("INSERT INTO album(name) VALUES(?)",(n["album_name"],)).lastrowid
        row=con.execute("SELECT id FROM track WHERE spotify_uri=?",(uri,)).fetchone() if uri else None
        if row: track_id=row[0]
        else: track_id=con.execute("INSERT INTO track(spotify_uri,spotify_id,name,album_id) VALUES(?,?,?,?)",(uri, uri.split(":")[-1] if uri else None, n.get("track_name") or "Unknown track", album_id)).lastrowid
        if n.get("artist_name"):
            ar=con.execute("SELECT id FROM artist WHERE name=? AND spotify_uri IS NULL",(n["artist_name"],)).fetchone()
            artist_id=ar[0] if ar else con.execute("INSERT INTO artist(name) VALUES(?)",(n["artist_name"],)).lastrowid
            con.execute("INSERT OR IGNORE INTO track_artist(track_id,artist_id,position) VALUES(?,?,0)",(track_id,artist_id))
        return int(track_id),None
    show_id=None
    if n.get("show_name"):
        sh=con.execute("SELECT id FROM podcast_show WHERE name=?",(n["show_name"],)).fetchone(); show_id=sh[0] if sh else con.execute("INSERT INTO podcast_show(name) VALUES(?)",(n["show_name"],)).lastrowid
    uri=n.get("episode_uri")
    ep=con.execute("SELECT id FROM episode WHERE spotify_uri=?",(uri,)).fetchone() if uri else None
    episode_id=ep[0] if ep else con.execute("INSERT INTO episode(spotify_uri,name,show_id) VALUES(?,?,?)",(uri,n.get("episode_name") or "Unknown episode",show_id)).lastrowid
    return None,int(episode_id)

def validate_package(name: str, data: bytes) -> dict[str,Any]:
    files=_extract_json_files(name,data); total=0; first=None; last=None; warnings=[]; supported=0
    for fname,raw in files:
        try: rows=_parse_rows(raw)
        except Exception as e:
            warnings.append(f"{fname}: {e}"); continue
        total += len(rows)
        for row in rows:
            try:
                n=normalize_export_row(row); supported+=1
                first=min(first,n["ended_at_utc"]) if first else n["ended_at_utc"]
                last=max(last,n["ended_at_utc"]) if last else n["ended_at_utc"]
            except Exception: pass
    return {"package_type":"spotify_extended_history","files":len(files),"events":total,"supported_events":supported,"unsupported_events":total-supported,"first_event_at":first,"last_event_at":last,"warnings":warnings,"safe_to_reimport":True}

def import_package(name: str, data: bytes) -> dict[str,Any]:
    package_hash=sha256_bytes(data); validation=validate_package(name,data)
    with transaction() as con:
        batch=con.execute("SELECT * FROM import_batch WHERE file_sha256=? AND source_type='spotify_extended_history'",(package_hash,)).fetchone()
        if batch:
            return {"status":"already_imported","batch_id":batch["id"],"events":batch["record_count"],"new":0,"duplicates":batch["record_count"],"reconciled":0}
        cur=con.execute("INSERT INTO import_batch(source_type,file_name,file_sha256,file_size,imported_at,status,application_version,importer_version) VALUES(?,?,?,?,?,'processing',?,?)",("spotify_extended_history",name,package_hash,len(data),now(),__version__,IMPORTER_VERSION))
        batch_id=cur.lastrowid; new=dup=errors=reconciled=records=0; first=last=None
        for fname,raw in _extract_json_files(name,data):
            try: rows=_parse_rows(raw)
            except Exception: errors+=1; continue
            for row in rows:
                records+=1; fp=fingerprint(row)
                exists=con.execute("SELECT id FROM raw_export_event WHERE source_fingerprint=?",(fp,)).fetchone()
                if exists: dup+=1; continue
                raw_id=con.execute("INSERT INTO raw_export_event(import_batch_id,raw_json,source_fingerprint,ingested_at) VALUES(?,?,?,?)",(batch_id,json.dumps(row,ensure_ascii=False),fp,now())).lastrowid
                try:
                    n=normalize_export_row(row); track_id,episode_id=_upsert_entities(con,n)
                    nid=con.execute("""INSERT INTO normalized_event(raw_export_event_id,content_type,track_id,episode_id,ended_at_utc,started_at_utc,ms_played,platform,country_code,ip_address,user_agent,reason_start,reason_end,shuffle,skipped,offline,offline_timestamp,private_session)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(raw_id,n["content_type"],track_id,episode_id,n["ended_at_utc"],n["started_at_utc"],n["ms_played"],n["platform"],n["country_code"],n["ip_address"],n["user_agent"],n["reason_start"],n["reason_end"],n["shuffle"],n["skipped"],n["offline"],str(n["offline_timestamp"]) if n["offline_timestamp"] is not None else None,n["private_session"])).lastrowid
                    pid=match_provisional(con,nid)
                    if pid: reconciled+=1
                    else: create_canonical_from_normalized(con,nid)
                    new+=1; first=min(first,n["ended_at_utc"]) if first else n["ended_at_utc"]; last=max(last,n["ended_at_utc"]) if last else n["ended_at_utc"]
                except Exception: errors+=1
        con.execute("UPDATE import_batch SET first_event_at=?,last_event_at=?,record_count=?,new_record_count=?,duplicate_record_count=?,error_count=?,status=? WHERE id=?",(first,last,records,new,dup,errors,"success" if errors==0 else "completed_with_warnings",batch_id))
        return {"status":"success" if errors==0 else "completed_with_warnings","batch_id":batch_id,"events":records,"new":new,"duplicates":dup,"errors":errors,"reconciled":reconciled,"validation":validation}
