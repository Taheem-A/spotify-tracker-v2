from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os, tomllib

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.toml"

@dataclass(slots=True)
class Settings:
    app_name: str
    app_version: str
    user_timezone: str
    database_path: Path
    backup_directory: Path
    imports_directory: Path
    spotify_client_id: str
    spotify_redirect_uri: str
    active_poll_interval_seconds: int
    paused_poll_interval_seconds: int
    inactive_poll_interval_seconds: int
    recent_sync_interval_seconds: int
    enable_derived_listening_metrics: bool


def load_settings() -> Settings:
    raw = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    app = raw["app"]
    spotify = raw["spotify"]
    features = raw["features"]
    env_flag = os.getenv("ENABLE_DERIVED_LISTENING_METRICS")
    flag = features.get("enable_derived_listening_metrics", False)
    if env_flag is not None:
        flag = env_flag.strip().lower() in {"1", "true", "yes", "on"}
    client_id = os.getenv("SPOTIFY_CLIENT_ID", spotify.get("client_id", ""))
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", spotify.get("redirect_uri", ""))
    return Settings(
        app_name=app["name"], app_version=app["version"], user_timezone=app["user_timezone"],
        database_path=ROOT / app["database_path"], backup_directory=ROOT / app["backup_directory"],
        imports_directory=ROOT / app["imports_directory"], spotify_client_id=client_id,
        spotify_redirect_uri=redirect_uri,
        active_poll_interval_seconds=int(spotify["active_poll_interval_seconds"]),
        paused_poll_interval_seconds=int(spotify["paused_poll_interval_seconds"]),
        inactive_poll_interval_seconds=int(spotify["inactive_poll_interval_seconds"]),
        recent_sync_interval_seconds=int(spotify["recent_sync_interval_seconds"]),
        enable_derived_listening_metrics=bool(flag),
    )

settings = load_settings()
