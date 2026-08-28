import json
from app.importers.extended_history import import_package
from app.analytics.service import overview

def test_overview_uses_canonical_rows():
    r={'ts':'2026-08-28T14:00:00Z','ms_played':60000,'master_metadata_track_name':'A','master_metadata_album_artist_name':'B','spotify_track_uri':'spotify:track:x'}
    import_package('a.json',json.dumps([r]).encode())
    d=overview('2026-08-28','2026-08-28')
    assert d['plays']==1 and d['listening_ms']==60000
