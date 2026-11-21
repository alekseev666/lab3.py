import logging

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QSpinBox, QVBoxLayout

from model.exceptions import StorageError, ValidationError
from service.formatting import format_date, nice_date, reps_text, result_text, weight_text
from ui.widgets import fill_table, make_button, make_card, make_label, make_table


# окно выбора даты
class DateDialog(QDialog):
    def __init__(self, title, start=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        # поле даты с календарём
        self.date_edit = QDateEdit(QDate.currentDate())
        if start is not None:
            self.date_edit.setDate(QDate.fromString(start, "yyyy-MM-dd"))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")

        # кнопки ОК и Отмена
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(make_label(title, "title"))
        layout.addWidget(self.date_edit)
        layout.addWidget(buttons)

    # дата для сохранения в файл
    def get_date(self):
        return self.date_edit.date().toString("yyyy-MM-dd")


# окно выбора упражнения
class PickerDialog(QDialog):
    def __init__(self, catalog, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор упражнения")
        self.resize(400, 560)
        self.selected = None

        # строка поиска
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск")
        self.search.textChanged.connect(self.filter)

        # список по группам мышц
        self.list = QListWidget()
        self.list.itemClicked.connect(self.choose)
        for group, exercises in catalog.groups().items():
            # заголовок группы нельзя выбрать
            header = QListWidgetItem(group.upper())
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(header)
            for info in exercises:
                item = QListWidgetItem(info.name)
                # запоминаем id упражнения
                item.setData(Qt.ItemDataRole.UserRole, info.id)
                self.list.addItem(item)

        cancel_button = make_button("Отмена")
        cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        layout.addWidget(cancel_button, alignment=Qt.AlignmentFlag.AlignRight)

    # фильтр списка по поиску
    def filter(self, text):
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) is None:
                # заголовки групп прячем, пока что-то ищем
                item.setHidden(text != "")
            else:
                item.setHidden(text.lower() not in item.text().lower())

    # выбрали упражнение кликом
    def choose(self, item):
        if item.data(Qt.ItemDataRole.UserRole) is not None:
            self.selected = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


# окно одной тренировки
class TrainingDialog(QDialog):
    def __init__(self, training, tracker, parent=None):
        super().__init__(parent)
        self.training = training
        self.tracker = tracker
        self.info = None
        self.advice = None
        self.setWindowTitle("Тренировка")
        self.resize(600, 640)

        # заголовок с датой
        self.title = make_label("", "title")
        date_button = make_button("Изменить дату", "link")
        date_button.clicked.connect(self.change_date)
        top = QHBoxLayout()
        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(date_button)

        # таблица подходов
        self.table = make_table(["Упражнение", "Вес", "Повторения"])

        # выбор упражнения и поля
        self.pick_button = make_button("Выберите упражнение  ›", "picker")
        self.pick_button.clicked.connect(self.pick_exercise)
        self.weight = QDoubleSpinBox()
        self.weight.setRange(0, 1000)
        self.weight.setDecimals(1)
        self.weight.setSuffix(" кг")
        self.reps = QSpinBox()
        self.reps.setRange(1, 1000)
        self.reps.setSuffix(" повт.")
        add_button = make_button("Добавить", "primary")
        add_button.setDefault(True)
        add_button.clicked.connect(self.add_exercise)
        # подсказка с рекомендацией
        self.hint = make_label("Выберите упражнение, вес и повторения подставятся сами.", "muted", True)

        # карточка нового упражнения
        inputs = QHBoxLayout()
        inputs.addWidget(self.weight)
        inputs.addWidget(self.reps)
        inputs.addWidget(add_button)
        card, card_layout = make_card()
        card_layout.addWidget(self.pick_button)
        card_layout.addLayout(inputs)
        card_layout.addWidget(self.hint)

        # нижние кнопки
        delete_exercise_button = make_button("Удалить упражнение")
        delete_exercise_button.clicked.connect(self.delete_exercise)
        delete_training_button = make_button("Удалить тренировку", "danger")
        delete_training_button.clicked.connect(self.delete_training)
        done_button = make_button("Готово", "primary")
        done_button.clicked.connect(self.accept)
        bottom = QHBoxLayout()
        bottom.addWidget(delete_exercise_button)
        bottom.addWidget(delete_training_button)
        bottom.addStretch()
        bottom.addWidget(done_button)

        # собираем всё в окно
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(make_label("НОВОЕ УПРАЖНЕНИЕ", "section"))
        layout.addWidget(card)
        layout.addLayout(bottom)
        self.update_table()

    # обновить таблицу и заголовок
    def update_table(self):
        self.title.setText(nice_date(self.training.date))
        rows = []
        for exercise in self.training.exercises:
            info = self.tracker.catalog.get(exercise.exercise_id)
            name = self.tracker.exercise_name(exercise)
            if info is None:
                name += " (нет в базе)"
            rows.append([name, weight_text(info, exercise.weight), reps_text(info, exercise.reps)])
        fill_table(self.table, rows)

    # открыть выбор упражнения
    def pick_exercise(self):
        dialog = PickerDialog(self.tracker.catalog, self)
        if dialog.exec():
            self.info = self.tracker.catalog.get(dialog.selected)
            self.show_advice()

    # подставить рекомендацию в поля
    def show_advice(self):
        info = self.info
        self.pick_button.setText(info.name + "  ›")
        # у планки секунды
        if info.is_timed():
            self.reps.setSuffix(" с")
        else:
            self.reps.setSuffix(" повт.")
        self.weight.setValue(0)
        self.reps.setValue(info.rep_range[0])

        # совет по прошлым тренировкам
        self.advice = self.tracker.advice(info, self.training)
        if self.advice is None:
            self.hint.setText("Заполните профиль, чтобы получать рекомендации.")
        elif self.advice.weight is None:
            self.hint.setText(self.advice.text)
        else:
            self.weight.setValue(self.advice.weight)
            self.reps.setValue(self.advice.reps)
            text = result_text(info, self.advice.weight, self.advice.reps)
            self.hint.setText(f"Рекомендация: {text} {self.advice.arrow}\n{self.advice.text}")

    # добавить подход
    def add_exercise(self):
        try:
            exercise = self.tracker.add_exercise(self.training, self.info, self.weight.value(), self.reps.value())
        except (ValidationError, StorageError) as error:
            logging.warning(str(error))
            QMessageBox.warning(self, "Ошибка", str(error))
            return
        logging.info(f"{format_date(self.training.date)}: добавлено {exercise.name} {result_text(self.info, exercise.weight, exercise.reps)}")
        # отдельно отмечаем разгрузку
        if self.advice is not None and self.advice.arrow == "↓":
            logging.info(f"{exercise.name}: разгрузка, вес -10%")
        self.update_table()

    # удалить выделенный подход
    def delete_exercise(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите упражнение в таблице.")
            return
        exercise = self.training.exercises[row]
        try:
            self.tracker.delete_exercise(self.training, exercise)
        except StorageError as error:
            QMessageBox.critical(self, "Ошибка", str(error))
            return
        logging.info(f"{format_date(self.training.date)}: удалено {self.tracker.exercise_name(exercise)}")
        self.update_table()

    # удалить всю тренировку
    def delete_training(self):
        answer = QMessageBox.question(self, "Удаление", "Удалить эту тренировку?")
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.tracker.delete_training(self.training)
            except StorageError as error:
                QMessageBox.critical(self, "Ошибка", str(error))
                return
            logging.info(f"Удалена тренировка {format_date(self.training.date)}")
            self.accept()

    # поменять дату тренировки
    def change_date(self):
        dialog = DateDialog("Дата тренировки", self.training.date, self)
        if dialog.exec():
            try:
                self.tracker.change_date(self.training, dialog.get_date())
            except StorageError as error:
                QMessageBox.critical(self, "Ошибка", str(error))
                return
            self.update_table()
            if self.info is not None:
                self.show_advice()
