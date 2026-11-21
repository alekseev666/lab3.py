from model.catalog import CatalogExercise
from service.formatting import experience_text, format_date, format_number, plural, result_text, training_text

BENCH = CatalogExercise("bench_press", "Жим лёжа", "Грудь", "barbell", False, [6, 10], 2.5)
PULL_UP = CatalogExercise("pull_up", "Подтягивания", "Спина", "bodyweight", True, [6, 12], 2.5)
PLANK = CatalogExercise("plank", "Планка", "Кор", "bodyweight", False, [30, 90], 0, "seconds")


# склонение слов по числу
def test_plural():
    assert plural(1, "день", "дня", "дней") == "1 день"
    assert plural(3, "день", "дня", "дней") == "3 дня"
    assert plural(11, "день", "дня", "дней") == "11 дней"
    assert plural(22, "день", "дня", "дней") == "22 дня"


# числа и даты
def test_numbers_and_dates():
    assert format_number(52.5) == "52,5"
    assert format_number(50.0) == "50"
    assert format_date("2026-11-21") == "21.11.2026"


# результат подхода текстом
def test_result_text():
    assert result_text(BENCH, 52.5, 6) == "52,5 кг × 6"
    assert result_text(PULL_UP, 0, 12) == "12 повторений"
    assert result_text(PULL_UP, 2.5, 8) == "+2,5 кг × 8"
    assert result_text(PLANK, 0, 60) == "60 с"


# стаж и строка тренировки
def test_experience_and_training():
    assert experience_text(0) == "меньше месяца"
    assert experience_text(16) == "1 г 4 мес"
    assert training_text(["Жим лёжа", "Планка"]) == "2 упражнения · Жим лёжа, Планка"
