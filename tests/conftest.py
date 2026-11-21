import os

# окна Qt без экрана
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest

import config
from service.tracker import Tracker


# временная папка вместо data
@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_FOLDER", str(tmp_path))
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite:///" + str(tmp_path / "test.db").replace("\\", "/"))
    monkeypatch.setattr(config, "LOG_FILE", str(tmp_path / "app.log"))
    return tmp_path


# пустая база для теста
@pytest.fixture
def tracker(folder):
    tracker = Tracker()
    yield tracker
    tracker.engine.dispose()
