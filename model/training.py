# один подход: вес и повторения
class Exercise:
    def __init__(self, name, weight, reps, exercise_id=None, id=None):
        self.name = name
        self.weight = weight
        self.reps = reps
        self.exercise_id = exercise_id
        self.id = id


# тренировка за один день
class Training:
    def __init__(self, date, exercises=None, id=None):
        self.date = date
        self.exercises = exercises or []
        self.id = id
