import logging

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QSize, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QSpinBox, QVBoxLayout, QWidget

from model.exceptions import StorageError, ValidationError
from model.goal import Goal
from service.formatting import level_text, result_text
from service.progression import check_goal, goal_percent, score
from ui.widgets import fill_table, make_button, make_card, make_label, make_table

# миллисекунд в одном дне
DAY = 24 * 60 * 60 * 1000


# цветная стрелка для текста
def arrow_html(arrow):
    if arrow == "↑":
        return " <span style='color:#248A3D'>↑</span>"
    if arrow == "↓":
        return " <span style='color:#C93400'>↓</span>"
    return ""


# график результатов и цели
def make_chart(info, records, goal):
    chart = QChart()
    chart.legend().hide()
    # линия результатов по датам
    line = QLineSeries()
    line.setColor(QColor("#E6A700"))
    line.setPointsVisible(True)
    values = []
    for day, weight, reps in records:
        value = score(info, weight, reps)
        if value is not None:
            line.append(QDateTime.fromString(day, "yyyy-MM-dd").toMSecsSinceEpoch(), value)
            values.append(value)
    chart.addSeries(line)
    # рисовать пока нечего
    if not values:
        return chart

    # отступ день по краям
    first = line.at(0).x() - DAY
    last = line.at(line.count() - 1).x() + DAY
    if goal is not None:
        # пунктир на уровне цели
        target = score(info, goal.weight, goal.reps)
        goal_line = QLineSeries()
        goal_line.setPen(QPen(QColor("#248A3D"), 1.5, Qt.PenStyle.DashLine))
        goal_line.append(first, target)
        goal_line.append(last, target)
        chart.addSeries(goal_line)
        values.append(target)

    # ось дат и ось значений
    x_axis = QDateTimeAxis()
    x_axis.setFormat("dd.MM")
    x_axis.setRange(QDateTime.fromMSecsSinceEpoch(int(first)), QDateTime.fromMSecsSinceEpoch(int(last)))
    y_axis = QValueAxis()
    y_axis.setRange(min(values) * 0.9, max(values) * 1.1)
    y_axis.applyNiceNumbers()
    y_axis.setLabelFormat("%.0f")
    chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
    # привязываем линии к осям
    for series in chart.series():
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)
    return chart


# окно «Мой прогресс»
class ProgressDialog(QDialog):
    def __init__(self, tracker, parent=None):
        super().__init__(parent)
        self.tracker = tracker
        self.setWindowTitle("Мой прогресс")
        self.resize(600, 700)

        # показать все или только свои
        self.show_all = QCheckBox("Показать все упражнения")
        self.show_all.toggled.connect(self.update_list)
        self.empty_label = make_label("Пока пусто. Добавьте упражнения в тренировку или отметьте «Показать все упражнения».", "muted", True)
        # список упражнений
        self.list = QListWidget()
        self.list.setObjectName("progress")
        self.list.itemClicked.connect(self.open_exercise)
        close_button = make_button("Закрыть", "primary")
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(make_label("Мой прогресс", "title"))
        layout.addWidget(make_label(level_text(tracker.user), "muted"))
        layout.addWidget(self.show_all)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.list)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.update_list()

    # заполнить список заново
    def update_list(self):
        self.list.clear()
        for group, rows in self.tracker.progress(self.show_all.isChecked()):
            self.add_header(group)
            for row in rows:
                self.add_row(row)
        # подсказка для пустого списка
        self.empty_label.setVisible(self.list.count() == 0)

    # строка с названием группы
    def add_header(self, group):
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(0, 34))
        self.list.addItem(item)
        self.list.setItemWidget(item, make_label(group.upper(), "section"))

    # строка одного упражнения
    def add_row(self, row):
        # что делать дальше
        details = ""
        if row["next"]:
            details = "Дальше: " + row["next"] + arrow_html(row["arrow"])
        # цель и процент
        if row["goal"]:
            details += "   → цель " + row["goal"]
        if row["percent"] is not None:
            details += f" ({row['percent']:.0f} %)"

        # строка с полосой прогресса
        widget = QWidget()
        box = QVBoxLayout(widget)
        box.setContentsMargins(10, 6, 10, 8)
        box.addWidget(QLabel(f"<b>{row['name']}</b> — {row['now']}<br><span style='color:#6C6C70'>{details}</span>"))
        if row["percent"] is not None:
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setValue(round(row["percent"]))
            box.addWidget(bar)
        # клики проходят в список
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, row["id"])
        item.setSizeHint(QSize(0, widget.sizeHint().height()))
        self.list.addItem(item)
        self.list.setItemWidget(item, widget)

    # открыть карточку упражнения
    def open_exercise(self, item):
        exercise_id = item.data(Qt.ItemDataRole.UserRole)
        if exercise_id is not None:
            ExerciseDialog(self.tracker.catalog.get(exercise_id), self.tracker, self).exec()
            self.update_list()


# карточка одного упражнения
class ExerciseDialog(QDialog):
    def __init__(self, info, tracker, parent=None):
        super().__init__(parent)
        self.info = info
        self.tracker = tracker
        self.records = tracker.history(info)
        self.setWindowTitle(info.name)
        self.resize(600, 800)

        # результат, совет и цель
        self.result_label = make_label("", "value")
        self.advice_label = make_label("", "muted", True)
        self.goal_label = make_label("", "value")
        self.goal_bar = QProgressBar()
        self.goal_bar.setTextVisible(False)
        # кнопки для цели
        goal_button = make_button("Изменить цель", "link")
        goal_button.clicked.connect(self.edit_goal)
        self.remove_button = make_button("Удалить цель", "danger_link")
        self.remove_button.clicked.connect(self.remove_goal)
        goal_buttons = QHBoxLayout()
        goal_buttons.addWidget(goal_button)
        goal_buttons.addWidget(self.remove_button)
        goal_buttons.addStretch()

        # всё в белой карточке
        card, card_layout = make_card()
        card_layout.addWidget(self.result_label)
        card_layout.addWidget(self.advice_label)
        card_layout.addWidget(self.goal_label)
        card_layout.addWidget(self.goal_bar)
        card_layout.addLayout(goal_buttons)

        # график и история
        self.chart_view = QChartView()
        self.chart_view.setMinimumHeight(240)
        self.table = make_table(["Дата", "Вес", "Повторения", "Максимум"])
        # без веса максимум не считаем
        self.table.setColumnHidden(3, info.is_bodyweight())
        close_button = make_button("Закрыть", "primary")
        close_button.clicked.connect(self.accept)

        low, high = info.rep_range
        word = "секунд" if info.is_timed() else "повторений"
        layout = QVBoxLayout(self)
        layout.addWidget(make_label(info.name, "title"))
        layout.addWidget(make_label(f"{info.group} · {low}–{high} {word}", "muted"))
        layout.addWidget(card)
        layout.addWidget(self.chart_view)
        layout.addWidget(self.table)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.update_info()

    # обновить всё в окне
    def update_info(self):
        info = self.info
        # последний результат
        if self.records:
            self.result_label.setText("Сейчас: " + result_text(info, self.records[-1][1], self.records[-1][2]))
        else:
            self.result_label.setText("Сейчас: нет записей")

        # совет на следующую тренировку
        advice = self.tracker.advice(info)
        if advice is None:
            self.advice_label.setText("Заполните профиль, чтобы получать рекомендации.")
        elif advice.weight is None:
            self.advice_label.setText(advice.text)
        else:
            text = result_text(info, advice.weight, advice.reps)
            self.advice_label.setText(f"Дальше: {text} {advice.arrow}\n{advice.text}")

        # цель и полоса прогресса
        goal = self.tracker.goals.get(info.id)
        self.goal_bar.setVisible(goal is not None)
        self.remove_button.setVisible(goal is not None)
        if goal is None:
            self.goal_label.setText("Цель не задана")
        else:
            text = "Цель: " + result_text(info, goal.weight, goal.reps)
            percent = goal_percent(self.records, info, goal)
            if percent is not None:
                text += f" ({percent:.0f} %)"
                self.goal_bar.setValue(round(percent))
            self.goal_label.setText(text)
        # перерисовываем график
        self.chart_view.setChart(make_chart(info, self.records, goal))

        # история, новые сверху
        fill_table(self.table, self.tracker.history_rows(info))

    # открыть окно цели
    def edit_goal(self):
        dialog = GoalDialog(self.info, self.records, self)
        if dialog.exec():
            self.save_goal(dialog.goal)

    # убрать цель
    def remove_goal(self):
        self.save_goal(None)

    # сохранить цель в файл
    def save_goal(self, goal):
        try:
            self.tracker.set_goal(self.info.id, goal)
        except StorageError as error:
            QMessageBox.critical(self, "Ошибка", str(error))
            return
        logging.info(f"{self.info.name}: цель изменена")
        self.update_info()


# окно новой цели
class GoalDialog(QDialog):
    def __init__(self, info, records, parent=None):
        super().__init__(parent)
        self.info = info
        self.records = records
        self.goal = None
        self.setWindowTitle("Цель")

        # поля веса и повторений
        self.weight = QDoubleSpinBox()
        self.weight.setRange(0, 1000)
        self.weight.setDecimals(1)
        self.weight.setSuffix(" кг")
        self.reps = QSpinBox()
        self.reps.setRange(1, 1000)
        # сначала последний результат
        if records:
            self.weight.setValue(records[-1][1])
            self.reps.setValue(records[-1][2])

        # вес только для снарядов
        form = QFormLayout()
        if not info.is_bodyweight():
            form.addRow("Вес:", self.weight)
        if info.is_timed():
            form.addRow("Секунды:", self.reps)
        else:
            form.addRow("Повторения:", self.reps)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(make_label("Цель", "title"))
        layout.addWidget(make_label(info.name, "muted"))
        layout.addLayout(form)
        layout.addWidget(buttons)

    # проверить и сохранить цель
    def save(self):
        weight = self.weight.value()
        # без снаряда вес ноль
        if self.info.is_bodyweight():
            weight = 0
        goal = Goal(weight, self.reps.value())
        try:
            check_goal(self.records, self.info, goal)
        except ValidationError as error:
            logging.warning(str(error))
            QMessageBox.warning(self, "Ошибка", str(error))
            return
        self.goal = goal
        self.accept()
