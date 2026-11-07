import json
from dataclasses import asdict
from pathlib import Path

from model.user import User


def load_user(path: Path) -> User | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as file:
        return User(**json.load(file))


def save_user(user: User, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(asdict(user), file, ensure_ascii=False, indent=4)
