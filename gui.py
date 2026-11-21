import sys

from PySide6.QtCore import QDate, QLibraryInfo, QTranslator
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from main import TRAININGS_PATH, format_date
from model.training import Exercise, Training
from service.training_storage import load_trainings, save_trainings


class DateDialog(QDialog):
    """Окно выбора даты тренировки, по умолчанию — сегодня."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новая тренировка")

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)  
        self.date_edit.setDisplayFormat("dd.MM.yyyy")

        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Дата тренировки:"))
        layout.addWidget(self.date_edit)
        layout.addWidget(buttons)

    def iso_date(self) -> str:
        """Выбранная дата в формате ГГГГ-ММ-ДД, как она хранится в файле."""
        return self.date_edit.date().toString("yyyy-MM-dd")


class TrainingDialog(QDialog):
    """Окно одной тренировки: таблица упражнений и поля для нового упражнения.

    Упражнения добавляются прямо в переданный объект training,
    сохраняет его в файл главное окно после закрытия диалога.
    """

    def __init__(self, training: Training, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.training = training
        self.deleted = False  
        self.setWindowTitle(f"Тренировка {format_date(training.date)}")
        self.resize(450, 350)

        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Упражнение", "Вес, кг", "Повторения"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )

        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название")
        self.weight_edit = QDoubleSpinBox()
        self.weight_edit.setRange(0, 1000)
        self.weight_edit.setSuffix(" кг")
        self.reps_edit = QSpinBox()
        self.reps_edit.setRange(1, 1000)
        add_button = QPushButton("Добавить")
        add_button.clicked.connect(self.add_exercise)

        form = QHBoxLayout()
        form.addWidget(self.name_edit, stretch=1)
        form.addWidget(self.weight_edit)
        form.addWidget(self.reps_edit)
        form.addWidget(add_button)

        delete_exercise_button = QPushButton("Удалить упражнение")
        delete_exercise_button.clicked.connect(self.delete_exercise)
        delete_training_button = QPushButton("Удалить тренировку")
        delete_training_button.clicked.connect(self.delete_training)
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)

        bottom = QHBoxLayout()
        bottom.addWidget(delete_exercise_button)
        bottom.addWidget(delete_training_button)
        bottom.addStretch()  
        bottom.addWidget(close_buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Новое упражнение (название, вес, повторения):"))
        layout.addLayout(form)
        layout.addLayout(bottom)

        self.show_exercises()

    def show_exercises(self) -> None:
        self.table.setRowCount(len(self.training.exercises))
        for row, exercise in enumerate(self.training.exercises):
            self.table.setItem(row, 0, QTableWidgetItem(exercise.name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{exercise.weight:g}"))
            self.table.setItem(row, 2, QTableWidgetItem(str(exercise.reps)))

    def add_exercise(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название упражнения.")
            return
        self.training.exercises.append(
            Exercise(name, self.weight_edit.value(), self.reps_edit.value())
        )
        self.show_exercises()
        self.name_edit.clear()
        self.name_edit.setFocus() 

    def delete_exercise(self) -> None:
        row = self.table.currentRow()  
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите упражнение в таблице.")
            return
        self.training.exercises.pop(row)
        self.show_exercises()

    def delete_training(self) -> None:
        answer = QMessageBox.question(
            self, "Удаление", "Удалить эту тренировку целиком?"
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.deleted = True
            self.accept()


class MainWindow(QMainWindow):
    """Главное окно: меню, заголовок, список тренировок и кнопки."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Трекер тренировок")
        self.resize(400, 300)
        self.trainings = load_trainings(TRAININGS_PATH)

        
        self.count_label = QLabel()
        self.training_list = QListWidget()
        add_button = QPushButton("Добавить тренировку")
        exit_button = QPushButton("Выход")

    
        add_button.clicked.connect(self.add_training)
        exit_button.clicked.connect(self.close)
        self.training_list.itemDoubleClicked.connect(self.open_training)

        
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(exit_button)

     
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.count_label)
        layout.addWidget(self.training_list)
        layout.addLayout(buttons)
        self.setCentralWidget(central)

        self.create_menu()
        self.show_trainings()

    def create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Файл")

        
        add_action = QAction("Добавить тренировку", self)
        add_action.setShortcut(QKeySequence("Ctrl+N"))
        add_action.triggered.connect(self.add_training)

        exit_action = QAction("Выход", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)

        file_menu.addAction(add_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def show_trainings(self) -> None:
        self.count_label.setText(f"Всего тренировок: {len(self.trainings)}")
        self.training_list.clear()
        for training in self.trainings:
            self.training_list.addItem(
                f"{format_date(training.date)} — упражнений: {len(training.exercises)}"
            )

    def add_training(self) -> None:
        dialog = DateDialog(self)
   
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        training = Training(dialog.iso_date())
        self.trainings.append(training)
        self.trainings.sort(key=lambda item: item.date)
        save_trainings(self.trainings, TRAININGS_PATH)
        self.show_trainings()
        self.edit_training(training)  

    def open_training(self, item) -> None:
   
        self.edit_training(self.trainings[self.training_list.row(item)])

    def edit_training(self, training: Training) -> None:
        dialog = TrainingDialog(training, self)
        dialog.exec()
        if dialog.deleted:
            self.trainings.remove(training)
        save_trainings(self.trainings, TRAININGS_PATH)
        self.show_trainings()


def main() -> None:
    app = QApplication(sys.argv) 

    
    translator = QTranslator()
    translator.load(
        "qtbase_ru", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    )
    app.installTranslator(translator)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())  


if __name__ == "__main__":
    main()
