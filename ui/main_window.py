import logging
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QToolButton, QVBoxLayout, QWidget

from config import ICONS_FOLDER
from model.exceptions import StorageError, ValidationError
from service.formatting import format_date, level_text, nice_date, plural, training_text
from ui.dialogs import ChartDialog, LogDialog, UserDialog
from ui.progress_window import ProgressDialog
from ui.training_window import DateDialog, TrainingDialog
from ui.widgets import make_label


# кнопка-картинка без рамки
def icon_button(file, tip, size=26):
    button = QToolButton()
    button.setObjectName("icon")
    button.setIcon(QIcon(os.path.join(ICONS_FOLDER, file)))
    button.setIconSize(QSize(size, size))
    button.setToolTip(tip)
    return button


# главное окно программы
class MainWindow(QMainWindow):
    def __init__(self, tracker):
        super().__init__()
        self.tracker = tracker
        self.rows = []
        self.setWindowTitle("Трекер тренировок")
        self.resize(560, 680)

        # заголовок и кнопка профиля
        self.level_label = make_label("", "muted")
        user_button = icon_button("user.svg", "Профиль", 40)
        user_button.setText("Пользователь")
        user_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        user_button.clicked.connect(self.edit_profile)
        titles = QVBoxLayout()
        titles.addWidget(make_label("Тренировки", "title"))
        titles.addWidget(self.level_label)
        header = QHBoxLayout()
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(user_button)

        # список тренировок
        self.list = QListWidget()
        self.list.setObjectName("trainings")
        self.list.itemClicked.connect(self.open_training)

        # нижняя панель с кнопками
        progress_button = icon_button("info.svg", "Мой прогресс")
        progress_button.clicked.connect(self.show_progress)
        add_button = icon_button("compose.svg", "Новая тренировка")
        add_button.clicked.connect(self.add_training)
        self.counter = make_label("", "muted")
        bottom = QHBoxLayout()
        bottom.addWidget(progress_button)
        bottom.addStretch()
        bottom.addWidget(self.counter)
        bottom.addStretch()
        bottom.addWidget(add_button)

        # собираем окно
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 12, 20, 10)
        layout.addLayout(header)
        layout.addWidget(self.list)
        layout.addLayout(bottom)
        self.setCentralWidget(central)

        # меню «Файл»
        file_menu = self.menuBar().addMenu("Файл")
        action = file_menu.addAction("Новая тренировка")
        action.setShortcut("Ctrl+N")
        action.triggered.connect(self.add_training)
        action = file_menu.addAction("Пользователь")
        action.setShortcut("Ctrl+P")
        action.triggered.connect(self.edit_profile)
        file_menu.addSeparator()
        action = file_menu.addAction("Выход")
        action.setShortcut("Ctrl+Q")
        action.triggered.connect(self.close)

        # меню «Вид»
        view_menu = self.menuBar().addMenu("Вид")
        action = view_menu.addAction("Мой прогресс")
        action.setShortcut("Ctrl+I")
        action.triggered.connect(self.show_progress)
        action = view_menu.addAction("График активности")
        action.setShortcut("Ctrl+G")
        action.triggered.connect(self.show_chart)
        action = view_menu.addAction("Журнал")
        action.setShortcut("Ctrl+L")
        action.triggered.connect(self.show_log)

        self.update_list()

    # обновить список тренировок
    def update_list(self):
        self.list.clear()
        # новые тренировки сверху
        self.rows = sorted(self.tracker.trainings, key=lambda t: t.date, reverse=True)
        for training in self.rows:
            text = training_text(self.tracker.exercise_names(training))
            # длинный текст обрезаем
            if len(text) > 60:
                text = text[:60] + "..."
            self.add_row(f"<b>{nice_date(training.date)}</b><br><span style='color:#6C6C70'>{text}</span>")
        # подсказка, если пусто
        if not self.rows:
            self.add_row("Тренировок пока нет. Нажмите ✎ справа внизу.")
        self.counter.setText(plural(len(self.rows), "тренировка", "тренировки", "тренировок"))
        self.level_label.setText(level_text(self.tracker.user))

    # строка списка с текстом
    def add_row(self, text):
        label = QLabel(text)
        # клики проходят в список
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 58))
        self.list.addItem(item)
        self.list.setItemWidget(item, label)

    # клик по тренировке
    def open_training(self, item):
        row = self.list.row(item)
        # строка-подсказка не открывается
        if row < len(self.rows):
            self.edit_training(self.rows[row])

    # новая тренировка
    def add_training(self):
        dialog = DateDialog("Новая тренировка", None, self)
        if dialog.exec():
            try:
                training = self.tracker.add_training(dialog.get_date())
            except StorageError as error:
                logging.error(str(error))
                QMessageBox.critical(self, "Ошибка", str(error))
                return
            logging.info(f"Добавлена тренировка {format_date(training.date)}")
            self.edit_training(training)

    # открыть тренировку
    def edit_training(self, training):
        TrainingDialog(training, self.tracker, self).exec()
        self.update_list()

    # изменить профиль
    def edit_profile(self):
        dialog = UserDialog(self.tracker.user, self)
        if dialog.exec():
            try:
                self.tracker.save_user(dialog.get_user())
            except (ValidationError, StorageError) as error:
                logging.error(str(error))
                QMessageBox.critical(self, "Ошибка", str(error))
                return
            logging.info(f"Профиль изменён, уровень: {self.tracker.level()}")
            self.update_list()

    # окно «Мой прогресс»
    def show_progress(self):
        ProgressDialog(self.tracker, self).exec()

    # окно графика
    def show_chart(self):
        ChartDialog(self.tracker, self).exec()

    # окно журнала
    def show_log(self):
        LogDialog(self).exec()
