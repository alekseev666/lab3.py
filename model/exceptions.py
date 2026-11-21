class TrackerError(Exception):
    """Базовая ошибка трекера тренировок."""


class ValidationError(TrackerError):
    """Неверные данные: пустое название, недопустимый вес и т.п."""


class StorageError(TrackerError):
    """Не удалось прочитать или сохранить файл с данными."""
