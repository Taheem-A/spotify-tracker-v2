from app.config import settings
from app.tracking.derived import DerivedTelemetry

def test_derived_metrics_default_off():
    assert settings.enable_derived_listening_metrics is False

def test_disabled_telemetry_does_not_persist():
    t=DerivedTelemetry();t.observe({'item':{'uri':'spotify:track:x'}})
    from app.database.db import connect
    with connect() as con: assert con.execute('select count(*) from playback_observation').fetchone()[0]==0
