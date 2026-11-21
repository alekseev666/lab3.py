import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from model.goal import Goal
from service.tracker import Tracker
from ui.main_window import MainWindow
from ui.progress_window import ExerciseDialog, ProgressDialog
from ui.training_window import TrainingDialog


# одно приложение Qt на все тесты
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


# главное окно показывает тренировки
def test_main_window(app, tracker):
    tracker.add_training("2026-11-20")
    window = MainWindow(tracker)
    assert window.list.count() == 1
    assert window.counter.text() == "1 тренировка"


# подход добавляется через окно
def test_training_dialog_adds(app, tracker):
    dialog = TrainingDialog(tracker.add_training("2026-11-20"), tracker)
    dialog.info = tracker.catalog.get("squat")
    dialog.show_advice()
    dialog.weight.setValue(80)
    dialog.reps.setValue(8)
    dialog.add_exercise()
    assert dialog.table.rowCount() == 1
    assert Tracker().trainings[0].exercises[0].weight == 80


# без упражнения показывается ошибка
def test_training_dialog_error(app, tracker, monkeypatch):
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[2]))
    dialog = TrainingDialog(tracker.add_training("2026-11-20"), tracker)
    dialog.add_exercise()
    assert messages == ["Сначала выберите упражнение."]


# прогресс и карточка упражнения
def test_progress_windows(app, tracker):
    training = tracker.add_training("2026-11-20")
    tracker.add_exercise(training, tracker.catalog.get("bench_press"), 50, 8)
    tracker.set_goal("bench_press", Goal(60, 5))
    progress = ProgressDialog(tracker)
    assert progress.list.count() == 2
    card = ExerciseDialog(tracker.catalog.get("bench_press"), tracker)
    assert card.goal_label.text() == "Цель: 60 кг × 5 (0 %)"
    assert card.table.rowCount() == 1
