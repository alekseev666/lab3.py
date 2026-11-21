from PySide6.QtWidgets import QFrame, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout


# надпись с нужным стилем
def make_label(text, name=None, wrap=False):
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


# кнопка с нужным стилем
def make_button(text, name=None):
    button = QPushButton(text)
    if name:
        button.setObjectName(name)
    # чтобы Enter не нажимал кнопку
    button.setAutoDefault(False)
    return button


# белая карточка со скруглением
def make_card():
    card = QFrame()
    card.setObjectName("card")
    return card, QVBoxLayout(card)


# таблица только для чтения
def make_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().hide()
    table.setShowGrid(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    # первый столбец тянется на всю ширину
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    return table


# заполнить таблицу строками
def fill_table(table, rows):
    table.setRowCount(len(rows))
    for i in range(len(rows)):
        for j in range(len(rows[i])):
            table.setItem(i, j, QTableWidgetItem(rows[i][j]))
