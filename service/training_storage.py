import json
from dataclasses import asdict
from pathlib import Path

from model.exceptions import StorageError, ValidationError
from model.training import Exercise, Training


def load_trainings(path: Path) -> list[Training]:
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as file:
            raw_trainings = json.load(file)
        return [
            Training(
                date=raw["date"],
                exercises=[Exercise(**exercise) for exercise in raw["exercises"]],
            )
            for raw in raw_trainings
        ]
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(f"Не удалось прочитать {path.name}: {error}") from error
    except (KeyError, TypeError, ValidationError) as error:
        raise StorageError(f"В файле {path.name} неверные данные: {error}") from error


def save_trainings(trainings: list[Training], path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(
                [asdict(training) for training in trainings],
                file,
                ensure_ascii=False,
                indent=4,
            )
    except OSError as error:
        raise StorageError(f"Не удалось сохранить {path.name}: {error}") from error
