import os
import tempfile
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
def override_db_path():
    """
    Переопределяет путь к БД на временный файл для каждого теста.
    Это изолирует тесты друг от друга и не загрязняет dev-БД.
    """
    original_db_path = os.environ.get("MINIWIKI_DB_PATH")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        os.environ["MINIWIKI_DB_PATH"] = tmp.name
    yield
    # Очистка: удаляем временный файл
    db_path = os.environ.get("MINIWIKI_DB_PATH")
    if db_path and os.path.exists(db_path):
        os.unlink(db_path)
    if original_db_path:
        os.environ["MINIWIKI_DB_PATH"] = original_db_path
    elif "MINIWIKI_DB_PATH" in os.environ:
        del os.environ["MINIWIKI_DB_PATH"]


@pytest_asyncio.fixture
async def client():
    """Создаёт httpx AsyncClient для тестирования FastAPI.
    Инициализирует БД, т.к. lifespan не вызывается в тестах.
    """
    # Инициализируем БД вручную — lifespan не вызывается в тестах
    init_db()
    transport = ASGITransport(app=app)
    # follow_redirects=True автоматически следует за редиректами (307 → 200)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac
