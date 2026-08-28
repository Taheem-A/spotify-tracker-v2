from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any


def parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    dt = datetime.fromisoformat(value)
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def normalize_export_row(row: dict[str, Any]) -> dict[str, Any]:
    ts = row.get("ts") or row.get("endTime") or row.get("end_time")
    if not ts:
        raise ValueError("Streaming-history row is missing end timestamp")
    ended = parse_ts(ts)
    ms = int(row.get("ms_played", row.get("msPlayed", 0)) or 0)
    track_uri = row.get("spotify_track_uri")
    episode_uri = row.get("spotify_episode_uri")
    content_type = "episode" if episode_uri else "track"
    return {
        "content_type": content_type,
        "ended_at_utc": ended.isoformat().replace("+00:00", "Z"),
        "started_at_utc": (ended - timedelta(milliseconds=max(ms,0))).isoformat().replace("+00:00", "Z"),
        "ms_played": max(ms, 0),
        "platform": row.get("platform"),
        "country_code": row.get("conn_country"),
        "ip_address": row.get("ip_addr"),
        "user_agent": row.get("user_agent_decrypted") or row.get("user_agent"),
        "track_name": row.get("master_metadata_track_name") or row.get("trackName"),
        "artist_name": row.get("master_metadata_album_artist_name") or row.get("artistName"),
        "album_name": row.get("master_metadata_album_album_name"),
        "track_uri": track_uri,
        "episode_name": row.get("episode_name"),
        "show_name": row.get("episode_show_name"),
        "episode_uri": episode_uri,
        "reason_start": row.get("reason_start"),
        "reason_end": row.get("reason_end"),
        "shuffle": row.get("shuffle"),
        "skipped": row.get("skipped"),
        "offline": row.get("offline"),
        "offline_timestamp": row.get("offline_timestamp"),
        "private_session": row.get("incognito_mode"),
    }
