from datetime import date, timedelta

import pytest

from model.catalog import CatalogExercise
from model.exceptions import ValidationError
from model.goal import Goal
from model.training import Exercise, Training
from model.user import count_months, get_level
from service.progression import check_goal, get_advice, get_history, goal_percent, one_rep_max

# день, от которого считаем
TODAY = date(2026, 11, 21)
BENCH = CatalogExercise("bench_press", "Жим лёжа", "Грудь", "barbell", False, [6, 10], 2.5)
SQUAT = CatalogExercise("squat", "Приседания", "Ноги", "barbell", True, [6, 10], 2.5)
PULL_UP = CatalogExercise("pull_up", "Подтягивания", "Спина", "bodyweight", True, [6, 12], 2.5)
PLANK = CatalogExercise("plank", "Планка", "Кор", "bodyweight", False, [30, 90], 0, "seconds")


# тренировки через день до вчера
def sessions(*sets):
    first = TODAY - timedelta(days=2 * len(sets) - 1)
    return [((first + timedelta(days=2 * i)).isoformat(), weight, reps) for i, (weight, reps) in enumerate(sets)]


# примеры из ТЗ и крайние случаи
@pytest.mark.parametrize("records, info, level, expected", [
    (sessions((50, 10)), BENCH, "Новичок", (52.5, 6, "↑")),
    (sessions((50, 10)), BENCH, "Средний", (50, 10, "")),
    (sessions((50, 10), (50, 10)), BENCH, "Средний", (52.5, 6, "↑")),
    (sessions((50, 10), (50, 10)), BENCH, "Опытный", (52.5, 6, "↑")),
    (sessions((100, 10)), SQUAT, "Новичок", (105, 6, "↑")),
    (sessions((100, 10), (100, 10)), SQUAT, "Средний", (102.5, 6, "↑")),
    (sessions((100, 10), (100, 10)), SQUAT, "Опытный", (102.5, 6, "↑")),
    (sessions((50, 7)), BENCH, "Новичок", (50, 8, "")),
    (sessions((47.5, 10), (50, 10)), BENCH, "Средний", (50, 10, "")),
    ([("2026-11-01", 50, 8)], BENCH, "Новичок", (50, 8, "")),
    (sessions((50, 5), (50, 4)), BENCH, "Средний", (45, 6, "↓")),
    (sessions((0, 12)), PULL_UP, "Новичок", (2.5, 6, "↑")),
    (sessions((0, 4), (0, 5)), PULL_UP, "Новичок", (0, 6, "")),
    (sessions((0, 90)), PLANK, "Опытный", (0, 95, "")),
])
def test_advice(records, info, level, expected):
    advice = get_advice(records, info, level, TODAY)
    assert (advice.weight, advice.reps, advice.arrow) == expected


# без записей подсказка про диапазон
def test_advice_without_records():
    advice = get_advice([], BENCH, "Новичок", TODAY)
    assert advice.weight is None
    assert "6–10" in advice.text


# формула Эпли
def test_one_rep_max():
    assert one_rep_max(100, 5) == pytest.approx(116.67, abs=0.01)
    assert one_rep_max(100, 1) == 100
    assert one_rep_max(50, 15) is None


# процент пути к цели
def test_goal_percent():
    assert goal_percent(sessions((45, 8), (50, 7)), BENCH, Goal(60, 5)) == pytest.approx(35.9, abs=0.05)
    assert goal_percent(sessions((70, 5)), BENCH, Goal(60, 5)) == 100
    assert goal_percent(sessions((0, 6), (0, 10)), PULL_UP, Goal(0, 15)) == pytest.approx(44.4, abs=0.05)


# цель ниже результата нельзя
def test_goal_below_current():
    with pytest.raises(ValidationError):
        check_goal(sessions((60, 8)), BENCH, Goal(60, 5))


# цель больше 12 повторений нельзя
def test_goal_with_many_reps():
    with pytest.raises(ValidationError):
        check_goal([], BENCH, Goal(80, 15))


# лучший подход за тренировку
def test_history_best_set():
    trainings = [
        Training("2026-11-20", [Exercise("Жим лёжа", 50, 6, "bench_press"), Exercise("Жим лёжа", 50, 8, "bench_press")]),
        Training("2026-11-18", [Exercise("Жим лёжа", 47.5, 10, "bench_press")]),
    ]
    assert get_history(trainings, BENCH) == [("2026-11-18", 47.5, 10), ("2026-11-20", 50, 8)]


# история до текущей тренировки
def test_history_before_training():
    first = Training("2026-11-18", [Exercise("Жим лёжа", 47.5, 10, "bench_press")])
    current = Training("2026-11-20", [Exercise("Жим лёжа", 50, 8, "bench_press")])
    later = Training("2026-11-21", [Exercise("Жим лёжа", 52.5, 6, "bench_press")])
    assert get_history([first, current, later], BENCH, current) == [("2026-11-18", 47.5, 10)]


# границы уровней по стажу
@pytest.mark.parametrize("since, level", [
    ("2025-11-22", "Новичок"),
    ("2025-11-21", "Средний"),
    ("2023-11-22", "Средний"),
    ("2023-11-21", "Опытный"),
])
def test_levels(since, level):
    assert get_level(count_months(date.fromisoformat(since), TODAY)) == level
