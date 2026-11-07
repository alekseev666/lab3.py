from datetime import date, datetime
from pathlib import Path

from model.training import Exercise, Training
from model.user import User
from service.training_storage import load_trainings, save_trainings
from service.user_storage import load_user, save_user

DATA_DIR = Path(__file__).parent / "data"
USER_PATH = DATA_DIR / "user.json"
TRAININGS_PATH = DATA_DIR / "trainings.json"

DATE_FORMAT = "%d.%m.%Y"

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


def ask_date() -> str:
    """Спрашивает дату в формате ДД.ММ.ГГГГ, пустой ввод — сегодня.

    Возвращает дату в формате ISO (ГГГГ-ММ-ДД) для хранения.
    """
    today = date.today()
    while True:
        text = input(f"Дата (ДД.ММ.ГГГГ, Enter - {today:{DATE_FORMAT}}): ").strip()
        if not text:
            return today.isoformat()
        try:
            return datetime.strptime(text, DATE_FORMAT).date().isoformat()
        except ValueError:
            print("Неверная дата.")


def format_date(iso_date: str) -> str:
    return date.fromisoformat(iso_date).strftime(DATE_FORMAT)


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


def ask_exercise() -> Exercise:
    return Exercise(
        name=ask_text("  Название упражнения: "),
        weight=ask_number("  Вес (кг, 0 - без веса): ", float, min_value=0),
        reps=ask_number("  Повторения: "),
    )


def print_training(training: Training) -> None:
    print(f"\nТренировка {format_date(training.date)}")
    if not training.exercises:
        print("  Упражнений пока нет.")
    for number, exercise in enumerate(training.exercises, start=1):
        print(f"  {number}. {exercise.name} — {exercise.weight:g} кг × {exercise.reps}")


def choose_training(trainings: list[Training]) -> Training | None:
    if not trainings:
        print("Тренировок пока нет.")
        return None
    for number, training in enumerate(trainings, start=1):
        print(
            f"  {number}. {format_date(training.date)} "
            f"(упражнений: {len(training.exercises)})"
        )
    choice = ask_number(
        "Номер тренировки (0 - назад): ",
        allowed=range(len(trainings) + 1),
        min_value=0,
    )
    return trainings[choice - 1] if choice else None


def edit_training(training: Training, trainings: list[Training]) -> None:
    """Меню одной тренировки. Каждое изменение сразу сохраняется в файл."""
    while True:
        print_training(training)
        print("1 - Добавить упражнение")
        print("2 - Удалить упражнение")
        print("3 - Изменить дату")
        print("0 - В главное меню")
        choice = input("Выбор: ").strip()
        if choice == "1":
            training.exercises.append(ask_exercise())
        elif choice == "2":
            if not training.exercises:
                print("Удалять нечего.")
                continue
            number = ask_number(
                "Номер упражнения: ",
                allowed=range(1, len(training.exercises) + 1),
            )
            training.exercises.pop(number - 1)
        elif choice == "3":
            training.date = ask_date()
        elif choice == "0":
            return
        else:
            print("Нет такого пункта.")
            continue
        trainings.sort(key=lambda item: item.date)
        save_trainings(trainings, TRAININGS_PATH)


def main() -> None:
    user = load_user(USER_PATH)
    if user is None:
        user = register_user()
        save_user(user, USER_PATH)

    trainings = load_trainings(TRAININGS_PATH)
    while True:
        print(f"\nВсего тренировок: {len(trainings)}")
        print("1 - Добавить тренировку")
        print("2 - Редактировать тренировку")
        print("0 - Выход")
        choice = input("Выбор: ").strip()
        if choice == "1":
            training = Training(ask_date())
            trainings.append(training)
            trainings.sort(key=lambda item: item.date)
            save_trainings(trainings, TRAININGS_PATH)
            edit_training(training, trainings)
        elif choice == "2":
            training = choose_training(trainings)
            if training is not None:
                edit_training(training, trainings)
        elif choice == "0":
            break
        else:
            print("Нет такого пункта.")


if __name__ == "__main__":
    main()
