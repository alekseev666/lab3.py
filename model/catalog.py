# упражнение из базы
class CatalogExercise:
    def __init__(self, id, name, group, equipment, large_group, rep_range, step_kg, unit="reps"):
        self.id = id
        self.name = name
        self.group = group
        self.equipment = equipment
        self.large_group = large_group
        self.rep_range = rep_range
        self.step_kg = step_kg
        self.unit = unit

    # упражнение с собственным весом
    def is_bodyweight(self):
        return self.equipment == "bodyweight"

    # результат в секундах
    def is_timed(self):
        return self.unit == "seconds"


# вся база упражнений
class Catalog:
    def __init__(self, exercises):
        self.exercises = exercises

    # найти упражнение по id
    def get(self, exercise_id):
        for exercise in self.exercises:
            if exercise.id == exercise_id:
                return exercise
        return None

    # упражнения по группам мышц
    def groups(self):
        groups = {}
        for exercise in self.exercises:
            if exercise.group not in groups:
                groups[exercise.group] = []
            groups[exercise.group].append(exercise)
        return groups
