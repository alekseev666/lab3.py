from dataclasses import dataclass, field

from model.exceptions import ValidationError


@dataclass
class Exercise:
    name: str
    weight: float
    reps: int

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError("Введите название упражнения.")
        if not 0 <= self.weight <= 1000:
            raise ValidationError("Вес должен быть от 0 до 1000 кг.")
        if not 1 <= self.reps <= 1000:
            raise ValidationError("Повторений должно быть от 1 до 1000.")


@dataclass
class Training:
    date: str
    exercises: list[Exercise] = field(default_factory=list)
