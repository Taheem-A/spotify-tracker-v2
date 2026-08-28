import json
from app.importers.extended_history import import_package
from app.database.db import connect

def row(ts='2026-08-28T14:00:00Z',uri='spotify:track:abc',ms=180000):
    return {'ts':ts,'platform':'iOS','ms_played':ms,'conn_country':'CA','master_metadata_track_name':'Paris','master_metadata_album_artist_name':'Sabrina Carpenter','master_metadata_album_album_name':'Singular: Act I','spotify_track_uri':uri,'reason_start':'trackdone','reason_end':'trackdone','shuffle':True,'skipped':False,'offline':False,'incognito_mode':False}

def test_reimport_is_idempotent():
    b=json.dumps([row()]).encode(); a=import_package('a.json',b); c=import_package('a.json',b)
    assert a['new']==1 and c['status']=='already_imported'
    with connect() as con: assert con.execute('select count(*) from canonical_play').fetchone()[0]==1

def test_overlapping_package_does_not_duplicate():
    import_package('a.json',json.dumps([row()]).encode())
    import_package('b.json',json.dumps([row(),row('2026-08-28T14:04:00Z')]).encode())
    with connect() as con: assert con.execute('select count(*) from canonical_play').fetchone()[0]==2

def test_consecutive_same_track_remains_separate():
    rows=[row('2026-08-28T14:00:00Z'),row('2026-08-28T14:03:10Z')]
    import_package('a.json',json.dumps(rows).encode())
    with connect() as con: assert con.execute('select count(*) from canonical_play').fetchone()[0]==2

def test_unknown_skip_stays_null():
    r=row();r.pop('skipped');import_package('a.json',json.dumps([r]).encode())
    with connect() as con: assert con.execute('select skipped from canonical_play').fetchone()[0] is None
