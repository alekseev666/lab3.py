from datetime import date

# названия дней и месяцев
WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]


# дата в виде 21.11.2026
def format_date(text):
    return date.fromisoformat(text).strftime("%d.%m.%Y")


# дата словами: «Суббота, 21 ноября»
def nice_date(text):
    day = date.fromisoformat(text)
    result = f"{WEEKDAYS[day.weekday()]}, {day.day} {MONTHS[day.month - 1]}"
    # чужой год пишем явно
    if day.year != date.today().year:
        result += f" {day.year}"
    return result


# склонение: 1 день, 2 дня
def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


# число с запятой вместо точки
def format_number(value):
    return f"{value:g}".replace(".", ",")


# вес для таблицы
def weight_text(info, weight):
    if info is not None and info.is_bodyweight():
        if weight == 0:
            return "—"
        return f"+{format_number(weight)} кг"
    return f"{format_number(weight)} кг"


# повторения или секунды
def reps_text(info, reps):
    if info is not None and info.is_timed():
        return f"{reps} с"
    return str(reps)


# результат вида «50 кг × 6»
def result_text(info, weight, reps):
    if info is not None and info.is_bodyweight() and weight == 0:
        if info.is_timed():
            return f"{reps} с"
        return plural(reps, "повторение", "повторения", "повторений")
    return f"{weight_text(info, weight)} × {reps_text(info, reps)}"


# строка: «3 упражнения · Жим, Присед»
def training_text(names):
    return plural(len(names), "упражнение", "упражнения", "упражнений") + " · " + ", ".join(names)


# стаж годами и месяцами
def experience_text(months):
    years = months // 12
    months = months % 12
    if years == 0 and months == 0:
        return "меньше месяца"
    text = ""
    if years > 0:
        text += f"{years} г "
    if months > 0:
        text += f"{months} мес"
    return text.strip()


# строка с уровнем и стажем
def level_text(user):
    if user is None or user.training_since is None:
        return "Профиль не заполнен"
    return f"{user.level()} уровень · стаж {experience_text(user.months())}"
