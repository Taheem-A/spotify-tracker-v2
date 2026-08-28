from __future__ import annotations
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.config import settings
from app.database.db import connect


def _range(start: str|None,end: str|None):
    tz=ZoneInfo(settings.user_timezone)
    if end: e=datetime.fromisoformat(end).replace(tzinfo=tz)+timedelta(days=1)
    else: e=datetime.now(tz)+timedelta(seconds=1)
    if start: s=datetime.fromisoformat(start).replace(tzinfo=tz)
    else: s=e-timedelta(days=28)
    return s.astimezone(timezone.utc).isoformat(), e.astimezone(timezone.utc).isoformat()

def overview(start=None,end=None):
    s,e=_range(start,end)
    with connect() as con:
        base=con.execute("""SELECT COUNT(*) plays, COALESCE(SUM(canonical_ms_played),0) ms, COUNT(DISTINCT track_id) tracks
          FROM canonical_play WHERE ended_at_utc>=? AND ended_at_utc<?""",(s,e)).fetchone()
        artists=con.execute("""SELECT COUNT(DISTINCT ta.artist_id) n FROM canonical_play cp JOIN track_artist ta ON ta.track_id=cp.track_id WHERE cp.ended_at_utc>=? AND cp.ended_at_utc<?""",(s,e)).fetchone()[0]
        daily=[dict(r) for r in con.execute("""SELECT substr(ended_at_utc,1,10) day, SUM(canonical_ms_played) ms, COUNT(*) plays FROM canonical_play WHERE ended_at_utc>=? AND ended_at_utc<? GROUP BY day ORDER BY day""",(s,e))]
        top_tracks=[dict(r) for r in con.execute("""SELECT t.id,t.name,COALESCE(a.name,'Unknown artist') artist,COUNT(*) plays,SUM(cp.canonical_ms_played) ms,al.artwork_url
          FROM canonical_play cp JOIN track t ON t.id=cp.track_id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id LEFT JOIN album al ON al.id=t.album_id
          WHERE cp.ended_at_utc>=? AND cp.ended_at_utc<? GROUP BY t.id ORDER BY ms DESC LIMIT 5""",(s,e))]
        top_artists=[dict(r) for r in con.execute("""SELECT a.id,a.name,COUNT(*) plays,SUM(cp.canonical_ms_played) ms FROM canonical_play cp JOIN track_artist ta ON ta.track_id=cp.track_id JOIN artist a ON a.id=ta.artist_id WHERE cp.ended_at_utc>=? AND cp.ended_at_utc<? GROUP BY a.id ORDER BY ms DESC LIMIT 5""",(s,e))]
        recent=[dict(r) for r in con.execute("""SELECT cp.id,cp.ended_at_utc,cp.canonical_ms_played,t.name track,COALESCE(a.name,'Unknown artist') artist,al.artwork_url,cp.skipped,cp.reconciliation_status FROM canonical_play cp LEFT JOIN track t ON t.id=cp.track_id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id LEFT JOIN album al ON al.id=t.album_id ORDER BY cp.ended_at_utc DESC LIMIT 8""")]
        sources=[dict(r) for r in con.execute("SELECT reconciliation_status status,COUNT(*) count FROM canonical_play GROUP BY reconciliation_status")]
        return {"period":{"start":s,"end":e},"listening_ms":base["ms"],"plays":base["plays"],"tracks":base["tracks"],"artists":artists,"daily":daily,"top_tracks":top_tracks,"top_artists":top_artists,"recent":recent,"sources":sources}

def history(q="",limit=100,offset=0,start=None,end=None):
    s,e=_range(start,end); like=f"%{q}%"
    with connect() as con:
        sql="""SELECT cp.id,cp.started_at_utc,cp.ended_at_utc,cp.canonical_ms_played,cp.skipped,cp.platform,cp.reconciliation_status,cp.confidence,
        t.name track,al.name album,COALESCE(a.name,'Unknown artist') artist,al.artwork_url,t.duration_ms
        FROM canonical_play cp LEFT JOIN track t ON t.id=cp.track_id LEFT JOIN album al ON al.id=t.album_id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id
        WHERE cp.ended_at_utc>=? AND cp.ended_at_utc<? AND (t.name LIKE ? OR a.name LIKE ? OR al.name LIKE ?) ORDER BY cp.ended_at_utc DESC LIMIT ? OFFSET ?"""
        rows=[dict(r) for r in con.execute(sql,(s,e,like,like,like,limit,offset))]
        total=con.execute("""SELECT COUNT(*) FROM canonical_play cp LEFT JOIN track t ON t.id=cp.track_id LEFT JOIN album al ON al.id=t.album_id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id WHERE cp.ended_at_utc>=? AND cp.ended_at_utc<? AND (t.name LIKE ? OR a.name LIKE ? OR al.name LIKE ?)""",(s,e,like,like,like)).fetchone()[0]
    return {"rows":rows,"total":total,"limit":limit,"offset":offset}

def entity_list(kind: str,limit=200):
    with connect() as con:
        if kind=="tracks":
            rows=con.execute("""SELECT t.id,t.name,COALESCE(a.name,'Unknown artist') subtitle,COUNT(cp.id) plays,COALESCE(SUM(cp.canonical_ms_played),0) ms,al.artwork_url FROM track t LEFT JOIN canonical_play cp ON cp.track_id=t.id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id LEFT JOIN album al ON al.id=t.album_id GROUP BY t.id ORDER BY ms DESC LIMIT ?""",(limit,))
        elif kind=="artists":
            rows=con.execute("""SELECT a.id,a.name,'' subtitle,COUNT(cp.id) plays,COALESCE(SUM(cp.canonical_ms_played),0) ms,NULL artwork_url FROM artist a LEFT JOIN track_artist ta ON ta.artist_id=a.id LEFT JOIN canonical_play cp ON cp.track_id=ta.track_id GROUP BY a.id ORDER BY ms DESC LIMIT ?""",(limit,))
        else:
            rows=con.execute("""SELECT al.id,al.name,COALESCE(a.name,'') subtitle,COUNT(cp.id) plays,COALESCE(SUM(cp.canonical_ms_played),0) ms,al.artwork_url FROM album al LEFT JOIN track t ON t.album_id=al.id LEFT JOIN canonical_play cp ON cp.track_id=t.id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id GROUP BY al.id ORDER BY ms DESC LIMIT ?""",(limit,))
        return [dict(r) for r in rows]

def track_detail(track_id:int):
    with connect() as con:
        t=con.execute("""SELECT t.*,al.name album,al.artwork_url,COALESCE(a.name,'Unknown artist') artist FROM track t LEFT JOIN album al ON al.id=t.album_id LEFT JOIN track_artist ta ON ta.track_id=t.id AND ta.position=0 LEFT JOIN artist a ON a.id=ta.artist_id WHERE t.id=?""",(track_id,)).fetchone()
        if not t: return None
        stats=con.execute("""SELECT COUNT(*) plays,SUM(canonical_ms_played) ms,AVG(CASE WHEN t.duration_ms>0 THEN MIN(1.0,canonical_ms_played*1.0/t.duration_ms) END) avg_completion,AVG(CASE WHEN skipped IS NOT NULL THEN skipped*1.0 END) skip_rate,MIN(ended_at_utc) first_heard,MAX(ended_at_utc) last_heard FROM canonical_play cp JOIN track t ON t.id=cp.track_id WHERE cp.track_id=?""",(track_id,)).fetchone()
        daily=[dict(r) for r in con.execute("SELECT substr(ended_at_utc,1,10) day,SUM(canonical_ms_played) ms,COUNT(*) plays FROM canonical_play WHERE track_id=? GROUP BY day ORDER BY day",(track_id,))]
        recent=[dict(r) for r in con.execute("SELECT id,ended_at_utc,canonical_ms_played,skipped,platform,reconciliation_status FROM canonical_play WHERE track_id=? ORDER BY ended_at_utc DESC LIMIT 50",(track_id,))]
        return {"track":dict(t),"stats":dict(stats),"daily":daily,"recent":recent}

def artist_detail(artist_id:int):
    with connect() as con:
        a=con.execute("SELECT * FROM artist WHERE id=?",(artist_id,)).fetchone()
        if not a: return None
        stats=con.execute("""SELECT COUNT(cp.id) plays,COALESCE(SUM(cp.canonical_ms_played),0) ms,COUNT(DISTINCT cp.track_id) tracks,MIN(cp.ended_at_utc) first_heard,MAX(cp.ended_at_utc) last_heard FROM track_artist ta JOIN canonical_play cp ON cp.track_id=ta.track_id WHERE ta.artist_id=?""",(artist_id,)).fetchone()
        daily=[dict(r) for r in con.execute("""SELECT substr(cp.ended_at_utc,1,10) day,SUM(cp.canonical_ms_played) ms FROM track_artist ta JOIN canonical_play cp ON cp.track_id=ta.track_id WHERE ta.artist_id=? GROUP BY day ORDER BY day""",(artist_id,))]
        tracks=[dict(r) for r in con.execute("""SELECT t.id,t.name,COUNT(cp.id) plays,SUM(cp.canonical_ms_played) ms,al.artwork_url FROM track_artist ta JOIN track t ON t.id=ta.track_id LEFT JOIN canonical_play cp ON cp.track_id=t.id LEFT JOIN album al ON al.id=t.album_id WHERE ta.artist_id=? GROUP BY t.id ORDER BY ms DESC LIMIT 10""",(artist_id,))]
        return {"artist":dict(a),"stats":dict(stats),"daily":daily,"top_tracks":tracks}

def album_detail(album_id:int):
    with connect() as con:
        al=con.execute("SELECT * FROM album WHERE id=?",(album_id,)).fetchone()
        if not al: return None
        stats=con.execute("""SELECT COUNT(cp.id) plays,COALESCE(SUM(cp.canonical_ms_played),0) ms,MIN(cp.ended_at_utc) first_heard,MAX(cp.ended_at_utc) last_heard FROM track t LEFT JOIN canonical_play cp ON cp.track_id=t.id WHERE t.album_id=?""",(album_id,)).fetchone()
        tracks=[dict(r) for r in con.execute("""SELECT t.id,t.name,COUNT(cp.id) plays,COALESCE(SUM(cp.canonical_ms_played),0) ms FROM track t LEFT JOIN canonical_play cp ON cp.track_id=t.id WHERE t.album_id=? GROUP BY t.id ORDER BY t.track_number,t.name""",(album_id,))]
        daily=[dict(r) for r in con.execute("""SELECT substr(cp.ended_at_utc,1,10) day,SUM(cp.canonical_ms_played) ms FROM track t JOIN canonical_play cp ON cp.track_id=t.id WHERE t.album_id=? GROUP BY day ORDER BY day""",(album_id,))]
        artists=[r[0] for r in con.execute("""SELECT DISTINCT a.name FROM track t JOIN track_artist ta ON ta.track_id=t.id JOIN artist a ON a.id=ta.artist_id WHERE t.album_id=? ORDER BY ta.position,a.name""",(album_id,))]
        return {"album":dict(al),"artists":artists,"stats":dict(stats),"tracks":tracks,"daily":daily}
