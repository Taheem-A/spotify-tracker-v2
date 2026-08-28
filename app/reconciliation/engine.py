from __future__ import annotations
from datetime import datetime, timezone
import json

ALGORITHM_VERSION = 1

FIELDS = ["canonical_ms_played","reason_start","reason_end","shuffle","skipped","offline","offline_timestamp","private_session","platform","country_code"]

def _now(): return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_canonical_from_normalized(con, normalized_id: int) -> int:
    n = con.execute("SELECT * FROM normalized_event WHERE id=?", (normalized_id,)).fetchone()
    if not n: raise ValueError("normalized event not found")
    # Each raw event fingerprint is unique, so an existing match means idempotent import.
    existing = con.execute("SELECT canonical_play_id FROM reconciliation_match WHERE source_record_type='normalized_event' AND source_record_id=?", (normalized_id,)).fetchone()
    if existing: return int(existing[0])
    now = _now()
    cur = con.execute("""INSERT INTO canonical_play(content_type,track_id,episode_id,started_at_utc,ended_at_utc,canonical_ms_played,reason_start,reason_end,shuffle,skipped,offline,offline_timestamp,private_session,platform,country_code,reconciliation_status,confidence,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (n["content_type"], n["track_id"], n["episode_id"], n["started_at_utc"], n["ended_at_utc"], n["ms_played"], n["reason_start"], n["reason_end"], n["shuffle"], n["skipped"], n["offline"], n["offline_timestamp"], n["private_session"], n["platform"], n["country_code"], "RECONCILED", 1.0, now, now))
    pid = cur.lastrowid
    con.execute("""INSERT INTO reconciliation_match(canonical_play_id,source_record_type,source_record_id,match_score,match_class,matched_at,algorithm_version,evidence_json)
        VALUES(?,?,?,?,?,?,?,?)""", (pid,"normalized_event",normalized_id,1.0,"EXACT_MATCH",now,ALGORITHM_VERSION,json.dumps({"fingerprint":"exact raw event"})))
    source_map = {
        "canonical_ms_played":"ms_played", "reason_start":"reason_start", "reason_end":"reason_end", "shuffle":"shuffle",
        "skipped":"skipped", "offline":"offline", "offline_timestamp":"offline_timestamp", "private_session":"private_session",
        "platform":"platform", "country_code":"country_code"
    }
    for field, source_field in source_map.items():
        if n[source_field] is not None:
            con.execute("INSERT OR REPLACE INTO field_provenance(canonical_play_id,field_name,value_source,source_record_id,certainty,last_updated) VALUES(?,?,?,?,?,?)",
                        (pid,field,"spotify_extended_history",normalized_id,"authoritative",now))
    return int(pid)


def match_provisional(con, normalized_id: int) -> int | None:
    n = con.execute("SELECT * FROM normalized_event WHERE id=?", (normalized_id,)).fetchone()
    if not n: return None
    id_field = "track_id" if n["content_type"] == "track" else "episode_id"
    candidates = con.execute(f"""SELECT * FROM canonical_play WHERE reconciliation_status='PROVISIONAL' AND {id_field}=?
        AND ABS(strftime('%s',ended_at_utc)-strftime('%s',?)) <= 180 ORDER BY ABS(strftime('%s',ended_at_utc)-strftime('%s',?)) ASC LIMIT 5""",
        (n[id_field], n["ended_at_utc"], n["ended_at_utc"])).fetchall()
    if not candidates: return None
    best, score = None, 0.0
    for c in candidates:
        delta = abs((datetime.fromisoformat(c["ended_at_utc"].replace("Z","+00:00")) - datetime.fromisoformat(n["ended_at_utc"].replace("Z","+00:00"))).total_seconds())
        s = max(0.0, 1.0-delta/180.0)
        if c["platform"] and n["platform"] and c["platform"] == n["platform"]: s += .1
        if s > score: best, score = c, min(s,1.0)
    if not best or score < .80: return None
    now = _now(); pid = best["id"]
    con.execute("""UPDATE canonical_play SET started_at_utc=?,ended_at_utc=?,canonical_ms_played=?,reason_start=?,reason_end=?,shuffle=?,skipped=?,offline=?,offline_timestamp=?,private_session=?,platform=?,country_code=?,reconciliation_status='RECONCILED',confidence=1.0,updated_at=? WHERE id=?""",
                (n["started_at_utc"],n["ended_at_utc"],n["ms_played"],n["reason_start"],n["reason_end"],n["shuffle"],n["skipped"],n["offline"],n["offline_timestamp"],n["private_session"],n["platform"],n["country_code"],now,pid))
    con.execute("INSERT OR REPLACE INTO reconciliation_match(canonical_play_id,source_record_type,source_record_id,match_score,match_class,matched_at,algorithm_version,evidence_json) VALUES(?,?,?,?,?,?,?,?)",
                (pid,"normalized_event",normalized_id,score,"HIGH_CONFIDENCE_MATCH",now,ALGORITHM_VERSION,json.dumps({"matched_provisional":True,"score":score})))
    for field in FIELDS:
        con.execute("INSERT OR REPLACE INTO field_provenance(canonical_play_id,field_name,value_source,source_record_id,certainty,last_updated) VALUES(?,?,?,?,?,?)",
                    (pid,field,"spotify_extended_history",normalized_id,"authoritative",now))
    return int(pid)
