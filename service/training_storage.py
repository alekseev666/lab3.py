import json
from dataclasses import asdict
from pathlib import Path

from model.training import Exercise, Training


def load_trainings(path: Path) -> list[Training]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        raw_trainings = json.load(file)
    return [
        Training(
            date=raw["date"],
            exercises=[Exercise(**exercise) for exercise in raw["exercises"]],
        )
        for raw in raw_trainings
    ]


def save_trainings(trainings: list[Training], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            [asdict(training) for training in trainings],
            file,
            ensure_ascii=False,
            indent=4,
        )
