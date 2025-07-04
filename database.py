import os
from sqlalchemy import Column, String, Integer, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# Определяем путь к файлу БД:
# - если задано DB_PATH в окружении — используем его (продакшн на Amvera, например: /data/bot.db)
# - иначе локальный файл bot.db рядом с этим скриптом (для разработки)
env_path = os.getenv("DB_PATH")
if env_path:
    DB_FILE = env_path
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(base_dir, "bot.db")

# Убедимся, что директория для файла существует
db_dir = os.path.dirname(DB_FILE)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# Создаем движок SQLite с отключенной проверкой потоков и статическим пулом
engine = create_engine(
    f"sqlite:///{DB_FILE}",
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Настраиваем WAL-журнал и полную синхронизацию для надежности
with engine.begin() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL;"))
    conn.execute(text("PRAGMA synchronous=FULL;"))

# Базовый класс для ORM-моделей
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, unique=True, nullable=False)

class Stat(Base):
    __tablename__ = "stats"
    event = Column(String, primary_key=True)
    count = Column(Integer, nullable=False, default=0)

# Создаем таблицы в БД, если их еще нет
Base.metadata.create_all(engine)

# Фабрика сессий
SessionLocal = sessionmaker(bind=engine, future=True)

def add_user(chat_id: int) -> bool:
    """Добавляет нового пользователя по chat_id. Возвращает True, если добавлен, False если уже существует."""
    with SessionLocal() as session:
        exists = session.query(User).filter(User.chat_id == chat_id).first()
        if exists:
            return False
        user = User(chat_id=chat_id)
        session.add(user)
        session.commit()
        return True


def get_all_ids() -> list[int]:
    """Возвращает список всех chat_id зарегистрированных пользователей."""
    with SessionLocal() as session:
        users = session.query(User.chat_id).all()
        return [u.chat_id for u in users]


def inc_stat(event_name: str) -> None:
    """Увеличивает счетчик события event_name."""
    with SessionLocal() as session:
        stat = session.get(Stat, event_name)
        if stat:
            stat.count += 1
        else:
            stat = Stat(event=event_name, count=1)
            session.add(stat)
        session.commit()


def get_stats() -> dict[str, int]:
    """Возвращает все счетчики в виде словаря {event: count}."""
    with SessionLocal() as session:
        results = session.query(Stat).all()
        return {s.event: s.count for s in results}
