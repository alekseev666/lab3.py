from sqlalchemy import Column, Float, ForeignKey, Integer, MetaData, String, Table, create_engine

metadata = MetaData()

# профиль, всегда одна строка
users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("gender", String(20)),
    Column("height", Integer),
    Column("weight", Float),
    Column("training_since", String(10)),
)

# тренировки по дням
trainings = Table(
    "trainings", metadata,
    Column("id", Integer, primary_key=True),
    Column("date", String(10)),
)

# подходы внутри тренировок
exercises = Table(
    "exercises", metadata,
    Column("id", Integer, primary_key=True),
    Column("training_id", Integer, ForeignKey("trainings.id")),
    Column("name", String(100)),
    Column("weight", Float),
    Column("reps", Integer),
    Column("exercise_id", String(50)),
)

# цели по упражнениям
goals = Table(
    "goals", metadata,
    Column("exercise_id", String(50), primary_key=True),
    Column("weight", Float),
    Column("reps", Integer),
)

# уже открытые подключения
engines = {}


# подключение к базе по адресу
def get_engine(url):
    if url not in engines:
        engine = create_engine(url)
        # создаём таблицы, если их нет
        metadata.create_all(engine)
        engines[url] = engine
    return engines[url]
