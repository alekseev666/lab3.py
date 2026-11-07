from dataclasses import dataclass


@dataclass
class User:
    gender: str
    height: int
    weight: float
    level: int
