from datetime import date
from pathlib import Path

from model.training import Exercise, Training
from model.user import User
from service.training_storage import add_training, load_trainings
from service.user_storage import load_user, save_user

DATA_DIR = Path(__file__).parent / "data"
USER_PATH = DATA_DIR / "user.json"
TRAININGS_PATH = DATA_DIR / "trainings.json"

LEVELS = {
    1: "Начинающий (0–3 месяца)",
    2: "Средний (3 месяца – 1,5 года)",
    3: "Продвинутый (больше 2 лет)",
}


def ask_number(
    prompt: str,
    number_type: type = int,
    allowed=None,
    min_value: float = 1,
) -> int | float:
    """Спрашивает число, пока пользователь не введёт корректное."""
    while True:
        try:
            value = number_type(input(prompt).replace(",", "."))
        except ValueError:
            print("Нужно ввести число.")
            continue
        if value < min_value or (allowed is not None and value not in allowed):
            print("Недопустимое значение.")
            continue
        return value


def ask_text(prompt: str) -> str:
    while True:
        text = input(prompt).strip()
        if text:
            return text
        print("Строка не должна быть пустой.")


def register_user() -> User:
    print("Заполните профиль.")
    gender = ask_text("Ваш пол: ")
    height = ask_number("Ваш рост (см): ")
    weight = ask_number("Ваш вес (кг): ", float)
    print("Уровень подготовки:")
    for number, description in LEVELS.items():
        print(f"  {number} - {description}")
    level = ask_number("Выберите уровень 1-3: ", allowed=LEVELS)
    return User(gender, height, weight, level)


def ask_training() -> Training:
    name = ask_text("Название тренировки: ")
    exercises_count = ask_number("Сколько упражнений: ")
    exercises = []
    for index in range(1, exercises_count + 1):
        print(f"Упражнение {index}:")
        exercises.append(
            Exercise(
                name=ask_text("  Название: "),
                weight=ask_number("  Вес (кг, 0 - без веса): ", float, min_value=0),
                reps=ask_number("  Повторения: "),
            )
        )
    return Training(date.today().isoformat(), name, exercises)


def main() -> None:
    user = load_user(USER_PATH)
    if user is None:
        user = register_user()
        save_user(user, USER_PATH)

    while True:
        trainings_count = len(load_trainings(TRAININGS_PATH))
        print(f"\nВсего тренировок: {trainings_count}")
        print("1 - Добавить тренировку")
        print("0 - Выход")
        choice = input("Выбор: ").strip()
        if choice == "1":
            add_training(ask_training(), TRAININGS_PATH)
            print("Тренировка сохранена.")
        elif choice == "0":
            break
        else:
            print("Нет такого пункта.")


if __name__ == "__main__":
    main()
