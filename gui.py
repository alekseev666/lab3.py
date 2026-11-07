import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from main import TRAININGS_PATH, format_date
from service.training_storage import load_trainings


class MainWindow(QWidget):
    """Главное окно: заголовок, список тренировок и кнопка выхода."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Трекер тренировок")
        self.resize(400, 300)

        # Виджеты — «кирпичики» окна.
        self.count_label = QLabel()
        self.training_list = QListWidget()
        exit_button = QPushButton("Выход")

        # Сигнал clicked кнопки подключаем к методу close окна.
        exit_button.clicked.connect(self.close)

        # Layout сам расставляет виджеты сверху вниз и тянет их при изменении размера.
        layout = QVBoxLayout(self)
        layout.addWidget(self.count_label)
        layout.addWidget(self.training_list)
        layout.addWidget(exit_button)

        self.show_trainings()

    def show_trainings(self) -> None:
        trainings = load_trainings(TRAININGS_PATH)
        self.count_label.setText(f"Всего тренировок: {len(trainings)}")
        self.training_list.clear()
        for training in trainings:
            self.training_list.addItem(
                f"{format_date(training.date)} — упражнений: {len(training.exercises)}"
            )


def main() -> None:
    app = QApplication(sys.argv)  # Одно на всё приложение, создаётся первым.
    window = MainWindow()
    window.show()
    sys.exit(app.exec())  # Цикл событий: ждёт кликов, пока окно не закроют.


if __name__ == "__main__":
    main()
