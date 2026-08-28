PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_batch (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_sha256 TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  requested_at TEXT,
  imported_at TEXT NOT NULL,
  first_event_at TEXT,
  last_event_at TEXT,
  record_count INTEGER NOT NULL DEFAULT 0,
  new_record_count INTEGER NOT NULL DEFAULT 0,
  duplicate_record_count INTEGER NOT NULL DEFAULT 0,
  error_count INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  application_version TEXT NOT NULL,
  importer_version TEXT NOT NULL,
  notes TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_import_file_hash ON import_batch(file_sha256, source_type);

CREATE TABLE IF NOT EXISTS raw_export_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  import_batch_id INTEGER NOT NULL REFERENCES import_batch(id) ON DELETE CASCADE,
  raw_json TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  UNIQUE(source_fingerprint)
);

CREATE TABLE IF NOT EXISTS artist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spotify_uri TEXT UNIQUE,
  spotify_id TEXT UNIQUE,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS album (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spotify_uri TEXT UNIQUE,
  spotify_id TEXT UNIQUE,
  name TEXT NOT NULL,
  album_type TEXT,
  release_date TEXT,
  total_tracks INTEGER,
  artwork_url TEXT,
  metadata_updated_at TEXT
);

CREATE TABLE IF NOT EXISTS track (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spotify_uri TEXT UNIQUE,
  spotify_id TEXT UNIQUE,
  name TEXT NOT NULL,
  album_id INTEGER REFERENCES album(id),
  duration_ms INTEGER,
  explicit INTEGER,
  disc_number INTEGER,
  track_number INTEGER,
  is_local INTEGER NOT NULL DEFAULT 0,
  metadata_updated_at TEXT
);

CREATE TABLE IF NOT EXISTS track_artist (
  track_id INTEGER NOT NULL REFERENCES track(id) ON DELETE CASCADE,
  artist_id INTEGER NOT NULL REFERENCES artist(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(track_id, artist_id)
);

CREATE TABLE IF NOT EXISTS podcast_show (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spotify_uri TEXT UNIQUE,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS episode (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spotify_uri TEXT UNIQUE,
  name TEXT NOT NULL,
  show_id INTEGER REFERENCES podcast_show(id),
  duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS normalized_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_export_event_id INTEGER UNIQUE REFERENCES raw_export_event(id) ON DELETE CASCADE,
  content_type TEXT NOT NULL,
  track_id INTEGER REFERENCES track(id),
  episode_id INTEGER REFERENCES episode(id),
  ended_at_utc TEXT NOT NULL,
  started_at_utc TEXT,
  ms_played INTEGER NOT NULL,
  platform TEXT,
  country_code TEXT,
  ip_address TEXT,
  user_agent TEXT,
  reason_start TEXT,
  reason_end TEXT,
  shuffle INTEGER,
  skipped INTEGER,
  offline INTEGER,
  offline_timestamp TEXT,
  private_session INTEGER
);
CREATE INDEX IF NOT EXISTS ix_normalized_ended ON normalized_event(ended_at_utc);
CREATE INDEX IF NOT EXISTS ix_normalized_track ON normalized_event(track_id);

CREATE TABLE IF NOT EXISTS canonical_play (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_type TEXT NOT NULL,
  track_id INTEGER REFERENCES track(id),
  episode_id INTEGER REFERENCES episode(id),
  started_at_utc TEXT,
  ended_at_utc TEXT NOT NULL,
  canonical_ms_played INTEGER,
  reason_start TEXT,
  reason_end TEXT,
  shuffle INTEGER,
  skipped INTEGER,
  offline INTEGER,
  offline_timestamp TEXT,
  private_session INTEGER,
  platform TEXT,
  country_code TEXT,
  reconciliation_status TEXT NOT NULL DEFAULT 'RECONCILED',
  confidence REAL NOT NULL DEFAULT 1.0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_play_ended ON canonical_play(ended_at_utc DESC);
CREATE INDEX IF NOT EXISTS ix_play_started ON canonical_play(started_at_utc);
CREATE INDEX IF NOT EXISTS ix_play_track ON canonical_play(track_id);
CREATE INDEX IF NOT EXISTS ix_play_status ON canonical_play(reconciliation_status);

CREATE TABLE IF NOT EXISTS field_provenance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_play_id INTEGER NOT NULL REFERENCES canonical_play(id) ON DELETE CASCADE,
  field_name TEXT NOT NULL,
  value_source TEXT NOT NULL,
  source_record_id INTEGER,
  certainty TEXT NOT NULL,
  last_updated TEXT NOT NULL,
  UNIQUE(canonical_play_id, field_name)
);

CREATE TABLE IF NOT EXISTS reconciliation_match (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_play_id INTEGER NOT NULL REFERENCES canonical_play(id) ON DELETE CASCADE,
  source_record_type TEXT NOT NULL,
  source_record_id INTEGER NOT NULL,
  match_score REAL NOT NULL,
  match_class TEXT NOT NULL,
  matched_at TEXT NOT NULL,
  algorithm_version INTEGER NOT NULL,
  evidence_json TEXT,
  UNIQUE(source_record_type, source_record_id)
);

CREATE TABLE IF NOT EXISTS playback_observation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  observed_at_utc TEXT NOT NULL,
  spotify_state_timestamp INTEGER,
  content_uri TEXT,
  progress_ms INTEGER,
  is_playing INTEGER,
  device_id TEXT,
  device_name TEXT,
  device_type TEXT,
  device_is_active INTEGER,
  device_volume_percent INTEGER,
  shuffle_state INTEGER,
  repeat_state TEXT,
  context_type TEXT,
  context_uri TEXT,
  currently_playing_type TEXT,
  raw_payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_observation_time ON playback_observation(observed_at_utc DESC);

CREATE TABLE IF NOT EXISTS tracker_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_play_id INTEGER REFERENCES canonical_play(id) ON DELETE SET NULL,
  observed_at_utc TEXT NOT NULL,
  event_type TEXT NOT NULL,
  from_progress_ms INTEGER,
  to_progress_ms INTEGER,
  device_id TEXT,
  certainty TEXT NOT NULL,
  details_json TEXT
);

CREATE TABLE IF NOT EXISTS oauth_token (
  id INTEGER PRIMARY KEY CHECK(id=1),
  access_token TEXT,
  refresh_token TEXT,
  expires_at INTEGER,
  scope TEXT,
  token_type TEXT
);

CREATE TABLE IF NOT EXISTS app_setting (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backup_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT,
  verified INTEGER NOT NULL DEFAULT 0,
  size_bytes INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(kind, entity_id UNINDEXED, name, subtitle);
