import pytest
from fastapi.testclient import TestClient

from web.app import app


# клиент для веб-версии
@pytest.fixture
def client(tracker):
    return TestClient(app)


# главная страница открывается
def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Тренировки" in response.text


# создать тренировку и добавить подход
def test_add_training_and_exercise(client):
    response = client.post("/trainings", data={"day": "2026-11-20"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/trainings/1"
    client.post("/trainings/1/exercises", data={"exercise": "bench_press", "weight": "50", "reps": "8"})
    page = client.get("/trainings/1?exercise=bench_press").text
    assert "Жим лёжа" in page
    assert "50 кг" in page


# без упражнения ошибка ввода
def test_add_without_exercise(client):
    client.post("/trainings", data={"day": "2026-11-20"})
    response = client.post("/trainings/1/exercises", data={"exercise": "", "weight": "50", "reps": "8"})
    assert response.status_code == 400
    assert "Сначала выберите упражнение" in response.text


# профиль и рекомендация
def test_profile_and_advice(client):
    client.post("/profile", data={"gender": "Мужской", "height": "178", "weight": "75", "training_since": "2025-01-01"})
    assert "Средний уровень" in client.get("/").text
    client.post("/trainings", data={"day": "2026-11-18"})
    client.post("/trainings/1/exercises", data={"exercise": "squat", "weight": "80", "reps": "10"})
    client.post("/trainings", data={"day": "2026-11-20"})
    page = client.get("/trainings/2?exercise=squat").text
    assert "Рекомендация: 80 кг × 10. Верх диапазона" in page


# цель, прогресс и карточка
def test_goal_and_progress(client):
    client.post("/trainings", data={"day": "2026-11-20"})
    client.post("/trainings/1/exercises", data={"exercise": "bench_press", "weight": "50", "reps": "8"})
    low = client.post("/exercises/bench_press/goal", data={"weight": "50", "reps": "5"})
    assert low.status_code == 400
    client.post("/exercises/bench_press/goal", data={"weight": "60", "reps": "5"})
    assert "цель 60 кг × 5" in client.get("/progress").text
    assert "Цель: 60 кг × 5" in client.get("/exercises/bench_press").text


# удаление тренировки
def test_delete_training(client):
    client.post("/trainings", data={"day": "2026-11-20"})
    client.post("/trainings/1/delete")
    assert client.get("/trainings/1").status_code == 404


# остальные страницы открываются
def test_other_pages(client):
    for url in ["/progress?show_all=true", "/activity", "/log", "/profile"]:
        assert client.get(url).status_code == 200
    assert client.get("/exercises/nope").status_code == 404
