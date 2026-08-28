from __future__ import annotations
import csv, io, json, shutil, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from app.config import settings
from app.database.db import connect

def now(): return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
def backup(reason="manual"):
    settings.backup_directory.mkdir(parents=True,exist_ok=True); dest=settings.backup_directory/f"tracker-{now()}.db"
    src=connect(); dst=sqlite3.connect(dest)
    try: src.backup(dst); verified=dst.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    finally: src.close(); dst.close()
    with connect() as con: con.execute("INSERT INTO backup_record(path,created_at,reason,verified,size_bytes) VALUES(?,?,?,?,?)",(str(dest),datetime.now(timezone.utc).isoformat(),reason,int(verified),dest.stat().st_size))
    return {"path":str(dest),"verified":verified,"size_bytes":dest.stat().st_size}

def diagnostics():
    with connect() as con:
        integrity=con.execute("PRAGMA integrity_check").fetchone()[0]
        def n(t): return con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        last=con.execute("SELECT * FROM import_batch ORDER BY imported_at DESC LIMIT 1").fetchone()
        return {"integrity":integrity,"database_size":settings.database_path.stat().st_size if settings.database_path.exists() else 0,"raw_events":n("raw_export_event"),"canonical_plays":n("canonical_play"),"provisional":con.execute("SELECT COUNT(*) FROM canonical_play WHERE reconciliation_status='PROVISIONAL'").fetchone()[0],"ambiguous":con.execute("SELECT COUNT(*) FROM reconciliation_match WHERE match_class='AMBIGUOUS'").fetchone()[0],"last_import":dict(last) if last else None}

def export_data(fmt="json"):
    with connect() as con:
        rows=[dict(r) for r in con.execute("""SELECT cp.*,t.name track,al.name album,a.name artist FROM canonical_play cp LEFT JOIN track t ON t.id=cp.track_id LEFT JOIN album al ON al.id=t.album_id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id ORDER BY cp.ended_at_utc""")]
    if fmt=="csv":
        out=io.StringIO(); fields=list(rows[0].keys()) if rows else ["id"]; w=csv.DictWriter(out,fieldnames=fields); w.writeheader(); w.writerows(rows); return out.getvalue().encode(),"text/csv"
    return json.dumps(rows,ensure_ascii=False,indent=2).encode(),"application/json"
