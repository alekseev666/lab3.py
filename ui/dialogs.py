from datetime import date

from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QPlainTextEdit, QSpinBox, QVBoxLayout

from config import LOG_FILE
from model.user import User, count_months, get_level
from service.formatting import experience_text
from ui.widgets import make_button, make_card, make_label


# окно профиля
class UserDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Пользователь")

        # поля профиля
        self.gender_box = QComboBox()
        self.gender_box.addItems(["Мужской", "Женский"])
        self.height_box = QSpinBox()
        self.height_box.setRange(100, 230)
        self.height_box.setSuffix(" см")
        self.height_box.setValue(175)
        self.weight_box = QDoubleSpinBox()
        self.weight_box.setRange(30, 250)
        self.weight_box.setDecimals(1)
        self.weight_box.setSuffix(" кг")
        self.weight_box.setValue(70)
        self.since_box = QDateEdit(QDate.currentDate())
        self.since_box.setCalendarPopup(True)
        self.since_box.setDisplayFormat("dd.MM.yyyy")
        self.since_box.setMaximumDate(QDate.currentDate())
        self.level_label = QLabel()

        # подставляем сохранённые данные
        if user is not None:
            self.gender_box.setCurrentText(user.gender)
            self.height_box.setValue(user.height)
            self.weight_box.setValue(user.weight)
            if user.training_since is not None:
                self.since_box.setDate(QDate.fromString(user.training_since, "yyyy-MM-dd"))
        # стаж меняется вместе с датой
        self.since_box.dateChanged.connect(self.update_level)
        self.update_level()

        # подписи слева, поля справа
        form = QFormLayout()
        form.addRow("Пол:", self.gender_box)
        form.addRow("Рост:", self.height_box)
        form.addRow("Вес:", self.weight_box)
        form.addRow("Занимаюсь с:", self.since_box)
        form.addRow("Стаж:", self.level_label)
        card, card_layout = make_card()
        card_layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(make_label("Профиль", "title"))
        layout.addWidget(make_label("От стажа зависит, как быстро прибавлять вес.", "muted", True))
        layout.addWidget(card)
        layout.addWidget(buttons)

    # показать стаж и уровень
    def update_level(self):
        months = count_months(self.since_box.date().toPython(), date.today())
        self.level_label.setText(f"{experience_text(months)} — {get_level(months)}")

    # собрать профиль из полей
    def get_user(self):
        since = self.since_box.date().toString("yyyy-MM-dd")
        return User(self.gender_box.currentText(), self.height_box.value(), self.weight_box.value(), since)


# окно графика активности
class ChartDialog(QDialog):
    def __init__(self, tracker, parent=None):
        super().__init__(parent)
        self.setWindowTitle("График активности")
        self.resize(660, 460)

        # упражнений за последние дни
        labels, values = tracker.activity()

        # столбики графика
        bars = QBarSet("Упражнения")
        bars.setColor(QColor("#E6A700"))
        for value in values:
            bars.append(value)
        series = QBarSeries()
        series.append(bars)
        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        # подписи дат и чисел
        x_axis = QBarCategoryAxis()
        x_axis.append(labels)
        y_axis = QValueAxis()
        y_axis.setLabelFormat("%d")
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)
        y_axis.applyNiceNumbers()

        close_button = make_button("Закрыть", "primary")
        close_button.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(make_label("Активность", "title"))
        layout.addWidget(make_label("Сколько упражнений сделано за день, последние 12 тренировок", "muted"))
        layout.addWidget(QChartView(chart))
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)


# окно журнала действий
class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Журнал")
        self.resize(760, 480)

        # текст журнала из файла
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        with open(LOG_FILE, encoding="utf-8") as file:
            text.setPlainText(file.read())
        # сразу к последним записям
        text.moveCursor(QTextCursor.MoveOperation.End)

        close_button = make_button("Закрыть", "primary")
        close_button.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(make_label("Журнал", "title"))
        layout.addWidget(text)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
