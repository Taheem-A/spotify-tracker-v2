from __future__ import annotations
from datetime import datetime, timezone
import json
from app.config import settings
from app.database.db import connect

class DerivedTelemetry:
    """Isolated policy-gated telemetry. Never started when the feature flag is false."""
    def __init__(self): self.previous=None
    @property
    def enabled(self): return bool(settings.enable_derived_listening_metrics)
    def observe(self,payload:dict|None):
        if not self.enabled or not payload: return
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        item=payload.get("item") or {}; device=payload.get("device") or {}; context=payload.get("context") or {}
        uri=item.get("uri")
        with connect() as con:
            con.execute("""INSERT INTO playback_observation(observed_at_utc,spotify_state_timestamp,content_uri,progress_ms,is_playing,device_id,device_name,device_type,device_is_active,device_volume_percent,shuffle_state,repeat_state,context_type,context_uri,currently_playing_type,raw_payload) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (now,payload.get("timestamp"),uri,payload.get("progress_ms"),payload.get("is_playing"),device.get("id"),device.get("name"),device.get("type"),device.get("is_active"),device.get("volume_percent"),payload.get("shuffle_state"),payload.get("repeat_state"),context.get("type"),context.get("uri"),payload.get("currently_playing_type"),json.dumps(payload)))
        self.previous=payload
telemetry=DerivedTelemetry()
