from pathlib import Path
import pytest
from app.config import settings
from app.database.db import migrate

@pytest.fixture(autouse=True)
def temp_db(tmp_path:Path):
    old=settings.database_path
    settings.database_path=tmp_path/'tracker.db'
    migrate()
    yield
    settings.database_path=old
