from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers.pages import router as pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Инициализация базы данных при запуске приложения.
    """
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Настройка шаблонизатора Jinja2
app.state.templates = Jinja2Templates(directory="app/templates")


def format_datetime(value: str, fmt: str = "%d.%m.%Y %H:%M") -> str:
    """
    Преобразует строку даты в формат ДД.ММ.ГГГГ ЧЧ:ММ.
    Используется в шаблонах: {{ value|format_datetime }}
    """
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return value


# Добавляем кастомный фильтр для форматирования дат
app.state.templates.env.filters["format_datetime"] = format_datetime


@app.get("/")
async def root():
    """Перенаправление на список страниц."""
    return RedirectResponse(url="/pages")


@app.get("/health")
async def health():
    return {"status": "ok"}


# Подключаем роутер страниц
app.include_router(pages_router)
