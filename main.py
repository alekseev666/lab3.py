import logging
import os
import sys

from PySide6.QtCore import QLibraryInfo, Qt, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

from config import DATA_FOLDER, LOG_FILE, STYLE_FILE
from model.exceptions import StorageError
from service.tracker import Tracker
from ui.main_window import MainWindow


# запуск всей программы
def main():
    app = QApplication(sys.argv)
    # русские надписи на кнопках
    translator = QTranslator()
    translator.load("qtbase_ru", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.installTranslator(translator)
    # всегда светлая тема
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    # оформление из style.qss
    with open(STYLE_FILE, encoding="utf-8") as file:
        app.setStyleSheet(file.read())

    # журнал пишется в data/app.log
    os.makedirs(DATA_FOLDER, exist_ok=True)
    logging.basicConfig(filename=LOG_FILE, encoding="utf-8", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Программа запущена")

    # загружаем все данные
    try:
        tracker = Tracker()
    except StorageError as error:
        logging.error(str(error))
        QMessageBox.critical(None, "Ошибка", str(error))
        return

    window = MainWindow(tracker)
    window.show()
    # без профиля сразу спрашиваем
    if tracker.level() is None:
        window.edit_profile()
    app.exec()
    logging.info("Программа закрыта")


if __name__ == "__main__":
    main()
