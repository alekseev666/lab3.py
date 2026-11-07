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
            name=raw["name"],
            exercises=[Exercise(**exercise) for exercise in raw["exercises"]],
        )
        for raw in raw_trainings
    ]


def add_training(training: Training, path: Path) -> None:
    trainings = load_trainings(path)
    trainings.append(training)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            [asdict(item) for item in trainings],
            file,
            ensure_ascii=False,
            indent=4,
        )
