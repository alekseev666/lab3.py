from dataclasses import dataclass, field


@dataclass
class Exercise:
    name: str
    weight: float
    reps: int


@dataclass
class Training:
    date: str
    name: str
    exercises: list[Exercise] = field(default_factory=list)
