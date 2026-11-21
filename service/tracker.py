import json
import os
from datetime import date

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

import config
from model.catalog import Catalog, CatalogExercise
from model.exceptions import StorageError, ValidationError
from model.goal import Goal
from model.training import Exercise, Training
from model.user import User
from service.database import exercises, get_engine, goals, trainings, users
from service.formatting import format_date, format_number, reps_text, result_text, weight_text
from service.progression import get_advice, get_history, goal_percent, one_rep_max


# прочитать json файл
def read_json(path, default):
    # файла нет - значение по умолчанию
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(f"Не удалось прочитать {os.path.basename(path)}: {error}")


# проверка даты из формы
def check_date(text):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        raise ValidationError(f"Неверная дата: {text}")


# все данные программы
class Tracker:
    def __init__(self, url=None):
        # база упражнений из файла
        catalog = read_json(config.CATALOG_FILE, None)
        if catalog is None:
            raise StorageError("Не найден файл с упражнениями catalog/exercises.json")
        try:
            self.catalog = Catalog([CatalogExercise(**e) for e in catalog])
        except TypeError as error:
            raise StorageError(f"Ошибка в базе упражнений: {error}")
        # подключаемся к базе данных
        try:
            self.engine = get_engine(url or config.DATABASE_URL)
        except SQLAlchemyError as error:
            raise StorageError(f"Нет связи с базой данных: {error}")
        self.load()
        # первый запуск - переносим json
        if self.user is None and not self.trainings and not self.goals:
            self.import_json()

    # выполнить запрос к базе
    def run(self, query):
        try:
            with self.engine.begin() as connection:
                result = connection.execute(query)
                if result.returns_rows:
                    return result.fetchall()
                return result
        except SQLAlchemyError as error:
            raise StorageError(f"Ошибка базы данных: {error}")

    # загрузить всё из базы
    def load(self):
        self.user = None
        for row in self.run(select(users)):
            self.user = User(row.gender, row.height, row.weight, row.training_since)
        self.goals = {}
        for row in self.run(select(goals)):
            self.goals[row.exercise_id] = Goal(row.weight, row.reps)
        self.trainings = []
        by_id = {}
        for row in self.run(select(trainings).order_by(trainings.c.date, trainings.c.id)):
            by_id[row.id] = Training(row.date, [], row.id)
            self.trainings.append(by_id[row.id])
        for row in self.run(select(exercises).order_by(exercises.c.id)):
            # подход без тренировки пропускаем
            if row.training_id in by_id:
                by_id[row.training_id].exercises.append(Exercise(row.name, row.weight, row.reps, row.exercise_id, row.id))

    # перенос из старых json файлов
    def import_json(self):
        folder = config.DATA_FOLDER
        try:
            u = read_json(os.path.join(folder, "user.json"), None)
            if u is not None:
                # прошлая версия сохраняла пол как male/female
                gender = {"male": "Мужской", "female": "Женский"}.get(u["gender"], u["gender"])
                self.user = User(gender, u["height"], u["weight"], u.get("training_since"))
                self.run(insert(users).values(id=1, gender=gender, height=u["height"], weight=u["weight"], training_since=u.get("training_since")))
            for t in read_json(os.path.join(folder, "trainings.json"), []):
                training = self.add_training(t["date"])
                for e in t["exercises"]:
                    self.save_exercise(training, Exercise(e["name"], e["weight"], e["reps"], e.get("exercise_id")))
            for key, g in read_json(os.path.join(folder, "goals.json"), {}).items():
                self.set_goal(key, Goal(g["weight"], g["reps"]))
        except (KeyError, TypeError, AttributeError) as error:
            raise StorageError(f"Ошибка в старых json файлах: {error}")

    # уровень пользователя или None
    def level(self):
        if self.user is None:
            return None
        return self.user.level()

    # найти тренировку по id
    def find_training(self, training_id):
        for training in self.trainings:
            if training.id == training_id:
                return training
        return None

    # новая тренировка
    def add_training(self, day):
        check_date(day)
        result = self.run(insert(trainings).values(date=day))
        training = Training(day, [], result.inserted_primary_key[0])
        self.trainings.append(training)
        return training

    # удалить тренировку с подходами
    def delete_training(self, training):
        self.run(delete(exercises).where(exercises.c.training_id == training.id))
        self.run(delete(trainings).where(trainings.c.id == training.id))
        self.trainings.remove(training)

    # поменять дату тренировки
    def change_date(self, training, day):
        check_date(day)
        self.run(update(trainings).where(trainings.c.id == training.id).values(date=day))
        training.date = day

    # добавить подход с проверкой
    def add_exercise(self, training, info, weight, reps):
        if info is None:
            raise ValidationError("Сначала выберите упражнение.")
        if weight < 0 or weight > 1000 or reps < 1 or reps > 1000:
            raise ValidationError("Вес от 0 до 1000 кг, повторения от 1 до 1000.")
        return self.save_exercise(training, Exercise(info.name, weight, reps, info.id))

    # записать подход в базу
    def save_exercise(self, training, exercise):
        query = insert(exercises).values(training_id=training.id, name=exercise.name, weight=exercise.weight, reps=exercise.reps, exercise_id=exercise.exercise_id)
        exercise.id = self.run(query).inserted_primary_key[0]
        training.exercises.append(exercise)
        return exercise

    # удалить один подход
    def delete_exercise(self, training, exercise):
        self.run(delete(exercises).where(exercises.c.id == exercise.id))
        training.exercises.remove(exercise)

    # сохранить профиль с проверкой
    def save_user(self, user):
        if user.gender not in ("Мужской", "Женский"):
            raise ValidationError("Укажите пол.")
        if user.height < 100 or user.height > 230 or user.weight < 30 or user.weight > 250:
            raise ValidationError("Рост от 100 до 230 см, вес от 30 до 250 кг.")
        if check_date(user.training_since) > date.today():
            raise ValidationError("Дата начала занятий не может быть в будущем.")
        self.run(delete(users))
        self.run(insert(users).values(id=1, gender=user.gender, height=user.height, weight=user.weight, training_since=user.training_since))
        self.user = user

    # поставить или удалить цель
    def set_goal(self, exercise_id, goal):
        self.run(delete(goals).where(goals.c.exercise_id == exercise_id))
        self.goals.pop(exercise_id, None)
        if goal is not None:
            self.run(insert(goals).values(exercise_id=exercise_id, weight=goal.weight, reps=goal.reps))
            self.goals[exercise_id] = goal

    # название упражнения из базы
    def exercise_name(self, exercise):
        info = self.catalog.get(exercise.exercise_id)
        if info is None:
            return exercise.name
        return info.name

    # названия упражнений без повторов
    def exercise_names(self, training):
        names = []
        for exercise in training.exercises:
            name = self.exercise_name(exercise)
            if name not in names:
                names.append(name)
        return names

    # история результатов упражнения
    def history(self, info, before=None):
        return get_history(self.trainings, info, before)

    # совет для упражнения
    def advice(self, info, training=None):
        if self.level() is None:
            return None
        if training is None:
            return get_advice(self.history(info), info, self.level(), date.today())
        return get_advice(self.history(info, training), info, self.level(), date.fromisoformat(training.date))

    # строки для экрана прогресса
    def progress(self, show_all=False):
        result = []
        for group, items in self.catalog.groups().items():
            rows = []
            for info in items:
                records = self.history(info)
                goal = self.goals.get(info.id)
                # без записей и цели пропускаем
                if not records and goal is None and not show_all:
                    continue
                row = {"id": info.id, "name": info.name, "now": "нет записей", "next": "", "arrow": "", "goal": "", "percent": None}
                if records:
                    row["now"] = result_text(info, records[-1][1], records[-1][2])
                advice = self.advice(info)
                if advice is not None and advice.weight is not None:
                    row["next"] = result_text(info, advice.weight, advice.reps)
                    row["arrow"] = advice.arrow
                if goal is not None:
                    row["goal"] = result_text(info, goal.weight, goal.reps)
                    row["percent"] = goal_percent(records, info, goal)
                rows.append(row)
            if rows:
                result.append((group, rows))
        return result

    # таблица истории, новые сверху
    def history_rows(self, info):
        rows = []
        for day, weight, reps in reversed(self.history(info)):
            best = one_rep_max(weight, reps)
            best_text = "—" if best is None else format_number(round(best, 1)) + " кг"
            rows.append([format_date(day), weight_text(info, weight), reps_text(info, reps), best_text])
        return rows

    # упражнений за последние дни
    def activity(self, days=12):
        counts = {}
        for training in self.trainings:
            counts[training.date] = counts.get(training.date, 0) + len(training.exercises)
        last_days = sorted(counts)[-days:]
        return [format_date(day)[:5] for day in last_days], [counts[day] for day in last_days]
