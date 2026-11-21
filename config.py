import os

# папка с программой
FOLDER = os.path.dirname(os.path.abspath(__file__))
# папка с данными пользователя
DATA_FOLDER = os.environ.get("TRACKER_DATA", os.path.join(FOLDER, "data"))
# адрес базы, по умолчанию sqlite
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(DATA_FOLDER, "tracker.db").replace("\\", "/"))
# база упражнений
CATALOG_FILE = os.path.join(FOLDER, "catalog", "exercises.json")
# журнал действий
LOG_FILE = os.path.join(DATA_FOLDER, "app.log")
# оформление окон
STYLE_FILE = os.path.join(FOLDER, "style.qss")
# картинки для кнопок
ICONS_FOLDER = os.path.join(FOLDER, "icons")
