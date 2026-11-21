import logging
import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from model.exceptions import StorageError, ValidationError
from model.goal import Goal
from model.user import User
from service.formatting import format_date, level_text, nice_date, plural, reps_text, result_text, training_text, weight_text
from service.progression import check_goal, goal_percent, score
from service.tracker import Tracker

# папка веб-версии
FOLDER = os.path.dirname(os.path.abspath(__file__))


# при запуске включаем журнал
@asynccontextmanager
async def lifespan(app):
    os.makedirs(config.DATA_FOLDER, exist_ok=True)
    logging.basicConfig(filename=config.LOG_FILE, encoding="utf-8", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Веб-версия запущена")
    yield


app = FastAPI(title="Трекер тренировок", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(FOLDER, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(FOLDER, "templates"))


# показать страницу по шаблону
def page(request, name, data, status=200):
    return templates.TemplateResponse(request, name, data, status_code=status)


# перейти на другую страницу
def go(url):
    return RedirectResponse(url, status_code=303)


# ошибка ввода - код 400
@app.exception_handler(ValidationError)
def validation_error(request: Request, error: ValidationError):
    return page(request, "error.html", {"message": str(error)}, 400)


# ошибка базы - код 500
@app.exception_handler(StorageError)
def storage_error(request: Request, error: StorageError):
    return page(request, "error.html", {"message": str(error)}, 500)


# стрелка с пробелом или ничего
def arrow_text(advice):
    if advice.arrow:
        return " " + advice.arrow
    return ""


# тренировка по id или 404
def get_training(tracker, training_id):
    training = tracker.find_training(training_id)
    if training is None:
        raise HTTPException(404, "Тренировка не найдена")
    return training


# упражнение по id или 404
def get_exercise(tracker, exercise_id):
    info = tracker.catalog.get(exercise_id)
    if info is None:
        raise HTTPException(404, "Упражнение не найдено")
    return info


# главная со списком тренировок
@app.get("/")
def index(request: Request):
    tracker = Tracker()
    rows = []
    for training in sorted(tracker.trainings, key=lambda t: t.date, reverse=True):
        rows.append({"id": training.id, "title": nice_date(training.date), "text": training_text(tracker.exercise_names(training))})
    counter = plural(len(rows), "тренировка", "тренировки", "тренировок")
    return page(request, "index.html", {"rows": rows, "counter": counter, "level": level_text(tracker.user), "today": date.today().isoformat()})


# создать тренировку
@app.post("/trainings")
def create_training(day: str = Form(...)):
    training = Tracker().add_training(day)
    logging.info(f"Добавлена тренировка {format_date(day)}")
    return go(f"/trainings/{training.id}")


# страница одной тренировки
@app.get("/trainings/{training_id}")
def training_page(request: Request, training_id: int, exercise: str = ""):
    tracker = Tracker()
    training = get_training(tracker, training_id)
    rows = []
    for item in training.exercises:
        info = tracker.catalog.get(item.exercise_id)
        name = tracker.exercise_name(item)
        if info is None:
            name += " (нет в базе)"
        rows.append({"id": item.id, "name": name, "weight": weight_text(info, item.weight), "reps": reps_text(info, item.reps)})

    # совет для выбранного упражнения
    info = tracker.catalog.get(exercise)
    weight, reps = 0, 1
    hint = "Выберите упражнение, вес и повторения подставятся сами."
    if info is not None:
        reps = info.rep_range[0]
        advice = tracker.advice(info, training)
        if advice is None:
            hint = "Заполните профиль, чтобы получать рекомендации."
        elif advice.weight is None:
            hint = advice.text
        else:
            weight, reps = advice.weight, advice.reps
            hint = f"Рекомендация: {result_text(info, weight, reps)}{arrow_text(advice)}. {advice.text}"
    data = {"training": training, "title": nice_date(training.date), "rows": rows, "groups": tracker.catalog.groups(), "selected": exercise, "weight": weight, "reps": reps, "hint": hint}
    return page(request, "training.html", data)


# добавить подход
@app.post("/trainings/{training_id}/exercises")
def add_exercise(training_id: int, exercise: str = Form(""), weight: float = Form(0), reps: int = Form(1)):
    tracker = Tracker()
    training = get_training(tracker, training_id)
    info = tracker.catalog.get(exercise)
    added = tracker.add_exercise(training, info, weight, reps)
    logging.info(f"{format_date(training.date)}: добавлено {added.name} {result_text(info, weight, reps)}")
    return go(f"/trainings/{training_id}?exercise={exercise}")


# удалить подход
@app.post("/trainings/{training_id}/exercises/{row_id}/delete")
def delete_exercise(training_id: int, row_id: int):
    tracker = Tracker()
    training = get_training(tracker, training_id)
    for item in training.exercises:
        if item.id == row_id:
            tracker.delete_exercise(training, item)
            logging.info(f"{format_date(training.date)}: удалено {tracker.exercise_name(item)}")
            break
    return go(f"/trainings/{training_id}")


# поменять дату тренировки
@app.post("/trainings/{training_id}/date")
def change_date(training_id: int, day: str = Form(...)):
    tracker = Tracker()
    tracker.change_date(get_training(tracker, training_id), day)
    return go(f"/trainings/{training_id}")


# удалить тренировку
@app.post("/trainings/{training_id}/delete")
def delete_training(training_id: int):
    tracker = Tracker()
    training = get_training(tracker, training_id)
    tracker.delete_training(training)
    logging.info(f"Удалена тренировка {format_date(training.date)}")
    return go("/")


# страница профиля
@app.get("/profile")
def profile_page(request: Request):
    tracker = Tracker()
    user = tracker.user
    if user is None:
        user = User("Мужской", 175, 70, None)
    return page(request, "profile.html", {"user": user, "level": level_text(tracker.user), "today": date.today().isoformat()})


# сохранить профиль
@app.post("/profile")
def save_profile(gender: str = Form(...), height: int = Form(...), weight: float = Form(...), training_since: str = Form(...)):
    tracker = Tracker()
    tracker.save_user(User(gender, height, weight, training_since))
    logging.info(f"Профиль изменён, уровень: {tracker.level()}")
    return go("/")


# экран «Мой прогресс»
@app.get("/progress")
def progress_page(request: Request, show_all: bool = False):
    tracker = Tracker()
    return page(request, "progress.html", {"groups": tracker.progress(show_all), "show_all": show_all, "level": level_text(tracker.user)})


# карточка упражнения
@app.get("/exercises/{exercise_id}")
def exercise_page(request: Request, exercise_id: str):
    tracker = Tracker()
    info = get_exercise(tracker, exercise_id)
    records = tracker.history(info)
    now = "нет записей"
    if records:
        now = result_text(info, records[-1][1], records[-1][2])

    # совет на следующую тренировку
    advice = tracker.advice(info)
    if advice is None:
        advice_text = "Заполните профиль, чтобы получать рекомендации."
    elif advice.weight is None:
        advice_text = advice.text
    else:
        advice_text = f"Дальше: {result_text(info, advice.weight, advice.reps)}{arrow_text(advice)}. {advice.text}"

    # точки для графика
    labels, values = [], []
    for day, weight, reps in records:
        if score(info, weight, reps) is not None:
            labels.append(format_date(day)[:5])
            values.append(round(score(info, weight, reps), 1))

    # цель, процент и линия цели
    goal = tracker.goals.get(info.id)
    goal_text, percent, goal_line = "Цель не задана", None, []
    if goal is not None:
        goal_text = "Цель: " + result_text(info, goal.weight, goal.reps)
        percent = goal_percent(records, info, goal)
        goal_line = [round(score(info, goal.weight, goal.reps), 1)] * len(values)

    # в форме цели последний результат
    goal_weight, goal_reps = 0, info.rep_range[0]
    if records:
        goal_weight, goal_reps = records[-1][1], records[-1][2]
    data = {"info": info, "now": now, "advice": advice_text, "goal": goal, "goal_text": goal_text, "percent": percent, "goal_line": goal_line,
            "labels": labels, "values": values, "rows": tracker.history_rows(info), "goal_weight": goal_weight, "goal_reps": goal_reps}
    return page(request, "exercise.html", data)


# поставить цель
@app.post("/exercises/{exercise_id}/goal")
def set_goal(exercise_id: str, weight: float = Form(0), reps: int = Form(...)):
    tracker = Tracker()
    info = get_exercise(tracker, exercise_id)
    if info.is_bodyweight():
        weight = 0
    goal = Goal(weight, reps)
    check_goal(tracker.history(info), info, goal)
    tracker.set_goal(info.id, goal)
    logging.info(f"{info.name}: цель изменена")
    return go(f"/exercises/{exercise_id}")


# удалить цель
@app.post("/exercises/{exercise_id}/goal/delete")
def delete_goal(exercise_id: str):
    tracker = Tracker()
    tracker.set_goal(get_exercise(tracker, exercise_id).id, None)
    return go(f"/exercises/{exercise_id}")


# график активности
@app.get("/activity")
def activity_page(request: Request):
    labels, values = Tracker().activity()
    return page(request, "activity.html", {"labels": labels, "values": values})


# журнал, новые записи сверху
@app.get("/log")
def log_page(request: Request):
    lines = []
    if os.path.exists(config.LOG_FILE):
        with open(config.LOG_FILE, encoding="utf-8") as file:
            lines = file.read().splitlines()
    return page(request, "log.html", {"lines": list(reversed(lines))})
