import os
import sqlite3
from datetime import datetime, timezone

# Путь к директории данных
DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data"
)


def get_db_path() -> str:
    """
    Возвращает путь к файлу БД.
    Проверяет переменную окружения MINIWIKI_DB_PATH (для тестов),
    иначе использует стандартный путь.
    """
    return os.environ.get(
        "MINIWIKI_DB_PATH",
        os.path.join(DB_DIR, "miniwiki.db")
    )

# SQL для создания таблицы pages
CREATE_PAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    """
    Создаёт и возвращает подключение к SQLite.
    Создаёт директорию data/ и файл БД, если они не существуют.
    """
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """
    Инициализирует базу данных: создаёт таблицу pages, если она не существует.
    Вызывается один раз при запуске приложения.
    """
    connection = get_connection()
    try:
        connection.execute(CREATE_PAGES_TABLE_SQL)
        connection.commit()
    finally:
        connection.close()
