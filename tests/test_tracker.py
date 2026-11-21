import json
from datetime import date, timedelta

import pytest

import config
from model.exceptions import StorageError, ValidationError
from model.goal import Goal
from model.user import User
from service.tracker import Tracker


# тренировка и подход сохраняются
def test_training_saved(tracker):
    training = tracker.add_training("2026-11-20")
    tracker.add_exercise(training, tracker.catalog.get("bench_press"), 50, 8)
    again = Tracker()
    assert len(again.trainings) == 1
    assert again.trainings[0].exercises[0].name == "Жим лёжа"
    assert again.trainings[0].exercises[0].weight == 50


# удаление подхода и тренировки
def test_delete(tracker):
    training = tracker.add_training("2026-11-20")
    first = tracker.add_exercise(training, tracker.catalog.get("squat"), 80, 8)
    tracker.add_exercise(training, tracker.catalog.get("squat"), 80, 7)
    tracker.delete_exercise(training, first)
    assert len(Tracker().trainings[0].exercises) == 1
    tracker.delete_training(training)
    assert Tracker().trainings == []


# смена даты тренировки
def test_change_date(tracker):
    training = tracker.add_training("2026-11-20")
    tracker.change_date(training, "2026-11-18")
    assert Tracker().trainings[0].date == "2026-11-18"


# неправильный ввод не сохраняется
def test_wrong_input(tracker):
    training = tracker.add_training("2026-11-20")
    with pytest.raises(ValidationError):
        tracker.add_exercise(training, None, 50, 8)
    with pytest.raises(ValidationError):
        tracker.add_exercise(training, tracker.catalog.get("squat"), 2000, 8)
    with pytest.raises(ValidationError):
        tracker.add_training("21.11.2026")
    assert Tracker().trainings[0].exercises == []


# профиль сохраняется и проверяется
def test_user(tracker):
    tracker.save_user(User("Женский", 165, 58, "2024-01-15"))
    assert Tracker().user.gender == "Женский"
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        tracker.save_user(User("Женский", 165, 58, tomorrow))
    with pytest.raises(ValidationError):
        tracker.save_user(User("Женский", 20, 58, "2024-01-15"))


# цели ставятся и удаляются
def test_goals(tracker):
    tracker.set_goal("squat", Goal(100, 5))
    assert Tracker().goals["squat"].weight == 100
    tracker.set_goal("squat", None)
    assert Tracker().goals == {}


# прогресс, история и активность
def test_progress(tracker):
    tracker.save_user(User("Мужской", 178, 75, "2025-01-01"))
    training = tracker.add_training(date.today().isoformat())
    tracker.add_exercise(training, tracker.catalog.get("bench_press"), 50, 7)
    tracker.set_goal("bench_press", Goal(60, 5))
    groups = tracker.progress()
    assert groups[0][0] == "Грудь"
    row = groups[0][1][0]
    assert row["now"] == "50 кг × 7"
    assert row["next"] == "50 кг × 8"
    assert row["percent"] == 0
    assert tracker.history_rows(tracker.catalog.get("bench_press"))[0][3] == "61,7 кг"
    assert tracker.activity()[1] == [1]


# перенос старых json файлов
def test_import_json(folder):
    (folder / "user.json").write_text(json.dumps({"gender": "male", "height": 172, "weight": 52.0, "level": 2}), encoding="utf-8")
    trainings = [{"date": "2026-11-07", "exercises": [{"name": "Жим", "weight": 50, "reps": 6}]}]
    (folder / "trainings.json").write_text(json.dumps(trainings), encoding="utf-8")
    tracker = Tracker()
    assert tracker.user.gender == "Мужской"
    assert tracker.trainings[0].exercises[0].name == "Жим"
    assert len(Tracker().trainings) == 1


# сломанная база упражнений
def test_broken_catalog(folder, monkeypatch):
    broken = folder / "broken.json"
    broken.write_text("{не json", encoding="utf-8")
    monkeypatch.setattr(config, "CATALOG_FILE", str(broken))
    with pytest.raises(StorageError):
        Tracker()


# нет доступа к базе
def test_bad_database(folder):
    with pytest.raises(StorageError):
        Tracker("sqlite:///" + str(folder / "нет" / "папки" / "t.db"))
