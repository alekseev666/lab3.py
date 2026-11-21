from datetime import date


# сколько полных месяцев прошло
def count_months(start, end):
    months = (end.year - start.year) * 12 + end.month - start.month
    if end.day < start.day:
        months -= 1
    return max(months, 0)


# уровень по стажу
def get_level(months):
    if months < 12:
        return "Новичок"
    if months < 36:
        return "Средний"
    return "Опытный"


# профиль пользователя
class User:
    def __init__(self, gender, height, weight, training_since=None):
        self.gender = gender
        self.height = height
        self.weight = weight
        self.training_since = training_since

    # стаж в месяцах
    def months(self):
        return count_months(date.fromisoformat(self.training_since), date.today())

    # None, если нет даты
    def level(self):
        if self.training_since is None:
            return None
        return get_level(self.months())
