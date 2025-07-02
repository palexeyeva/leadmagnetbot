from sqlalchemy import Column, String, Integer, BigInteger, create_engine
from sqlalchemy.orm import declarative_base, Session

# Подключаемся к SQLite (файл bot.db в папке проекта)
engine = create_engine("sqlite:///bot.db", echo=False, future=True)
Base = declarative_base()

# Модель пользователей для базы user_id (для рассылок)
class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)

# Модель агрегированных статистики
class Stat(Base):
    __tablename__ = "stats"
    event = Column(String, primary_key=True)   # имя события
    count = Column(Integer, nullable=False)    # количество раз

# Создаём таблицы, если ещё не существуют
Base.metadata.create_all(engine)

# --- Функции работы с пользователями ---
def add_user(user_id: int):
    """Добавляет пользователя в базу, если его там нет."""
    with Session(engine) as s:
        if not s.get(User, user_id):
            s.add(User(id=user_id))
            s.commit()


def get_all_ids() -> list[int]:
    """Возвращает список всех user_id."""
    with Session(engine) as s:
        return [u.id for u in s.query(User.id).all()]

# --- Функции агрегированной статистики ---
def inc_stat(event_name: str):
    """Увеличивает счётчик для события event_name."""
    with Session(engine) as s:
        stat = s.get(Stat, event_name)
        if stat:
            stat.count += 1
        else:
            s.add(Stat(event=event_name, count=1))
        s.commit()


def get_stats() -> dict[str, int]:
    """Возвращает все агрегированные счётчики как {event: count}."""
    with Session(engine) as s:
        return {st.event: st.count for st in s.query(Stat).all()}
