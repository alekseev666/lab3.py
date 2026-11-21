# общая ошибка программы
class TrackerError(Exception):
    pass


# неправильные данные от пользователя
class ValidationError(TrackerError):
    pass


# ошибка при работе с файлами
class StorageError(TrackerError):
    pass
