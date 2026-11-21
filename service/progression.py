import math
from datetime import date

from model.exceptions import ValidationError
from service.formatting import format_number

# сколько раз нужен верх диапазона
TOP_TIMES = {"Новичок": 1, "Средний": 2, "Опытный": 2}
# прибавка веса в процентах
STEP_PERCENT = {"Новичок": (5, 2.5), "Средний": (2.5, None), "Опытный": (None, None)}


# рекомендация на следующую тренировку
class Advice:
    def __init__(self, weight, reps, arrow, text):
        self.weight = weight
        self.reps = reps
        self.arrow = arrow
        self.text = text


# максимум на одно повторение
def one_rep_max(weight, reps):
    # больше 12 повторений не считаем
    if reps > 12:
        return None
    if reps == 1:
        return weight
    # формула Эпли
    return weight * (1 + reps / 30)


# число для сравнения результатов
def score(info, weight, reps):
    if info.is_bodyweight():
        return reps
    return one_rep_max(weight, reps)


# лучший подход каждой тренировки
def get_history(trainings, info, before=None):
    records = []
    for training in sorted(trainings, key=lambda t: t.date):
        # пропускаем текущую и более поздние
        if before is not None and (training is before or training.date > before.date):
            continue
        sets = [e for e in training.exercises if e.exercise_id == info.id]
        if sets:
            best = max(sets, key=lambda e: score(info, e.weight, e.reps) or 0)
            records.append((training.date, best.weight, best.reps))
    return records


# на сколько прибавить вес
def weight_step(info, level, weight):
    if info.large_group:
        percent = STEP_PERCENT[level][0]
    else:
        percent = STEP_PERCENT[level][1]
    # None - минимальный шаг снаряда
    if percent is None:
        return info.step_kg
    # минимум один шаг снаряда
    steps = round(weight * percent / 100 / info.step_kg)
    return max(steps, 1) * info.step_kg


# совет по правилам из ТЗ
def get_advice(records, info, level, today):
    low, high = info.rep_range
    # записей ещё нет
    if not records:
        word = "секунд" if info.is_timed() else "повторений"
        return Advice(None, None, "", f"Записей пока нет. Подберите вес, с которым получится {low}–{high} {word}.")

    day, weight, reps = records[-1]
    # долгий перерыв - повторяем результат
    pause = (today - date.fromisoformat(day)).days
    if pause > 14:
        return Advice(weight, reps, "", f"Перерыв {pause} дн. — повторите прошлый результат.")

    # два провала подряд - разгрузка
    if len(records) > 1 and records[-2][2] < low and reps < low and weight > 0 and info.step_kg > 0:
        new_weight = math.floor(weight * 0.9 / info.step_kg) * info.step_kg
        return Advice(new_weight, low, "↓", f"Два раза подряд меньше {low} — разгрузка, вес −10 %.")

    # без веса растут только повторения
    if info.step_kg == 0:
        if info.is_timed():
            return Advice(weight, reps + 5, "", "Добавьте 5 секунд.")
        return Advice(weight, reps + 1, "", "Добавьте одно повторение.")

    # сколько раз подряд был верх
    times = 0
    for record in reversed(records):
        if record[2] < high or record[1] < weight:
            break
        times += 1
    need = TOP_TIMES[level]
    # пора прибавлять вес
    if times >= need:
        step = weight_step(info, level, weight)
        return Advice(weight + step, low, "↑", f"Верх диапазона ({high}) достигнут — добавьте {format_number(step)} кг.")
    # верх был, но мало раз
    if reps >= high:
        return Advice(weight, reps, "", f"Верх диапазона достигнут {times} раз из {need} — повторите, чтобы добавить вес.")
    # иначе плюс одно повторение
    return Advice(weight, reps + 1, "", "Добавьте одно повторение с тем же весом.")


# процент пути к цели
def goal_percent(records, info, goal):
    target = score(info, goal.weight, goal.reps)
    # собираем все результаты
    scores = []
    for day, weight, reps in records:
        if score(info, weight, reps) is not None:
            scores.append(score(info, weight, reps))
    if target is None or not scores:
        return None
    # цель уже достигнута
    if scores[-1] >= target:
        return 100
    if target <= scores[0]:
        return 0
    return max(0, (scores[-1] - scores[0]) / (target - scores[0]) * 100)


# цель должна быть выше результата
def check_goal(records, info, goal):
    target = score(info, goal.weight, goal.reps)
    if target is None:
        raise ValidationError("Для цели укажите не больше 12 повторений.")
    # сравниваем с последним результатом
    for day, weight, reps in reversed(records):
        current = score(info, weight, reps)
        if current is not None:
            if target <= current:
                raise ValidationError("Цель должна быть выше текущего результата.")
            return
