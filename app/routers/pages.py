import sqlite3

import markdown
import nh3
from datetime import datetime, timezone
from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.database import get_connection

router = APIRouter(prefix="/pages", tags=["pages"])


# --- Утилиты ---

def render_markdown(raw_content: str) -> str:
    """
    Преобразует Markdown-текст в HTML и очищает от XSS через nh3.
    Использует nh3.clean() — whitelists-список тегов,
    разрешённых в Markdown-выводе (<p>, <strong>, <em>, <code>, <pre>,
    <ul>, <ol>, <li>, <a>, <blockquote>, <h1>-<h6>).
    """
    html = markdown.markdown(raw_content, extensions=["fenced_code"])
    cleaned = nh3.clean(html)
    return cleaned


def now_iso() -> str:
    """Возвращает текущее время в формате ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat()


def normalize_path(raw_path: str) -> str:
    """
    Нормализует путь: добавляет ведущий слэш, убирает trailing слэш.
    Пример: 'docs/nlp' → '/docs/nlp', '/docs/nlp/' → '/docs/nlp'
    """
    normalized = "/" + raw_path.strip().lstrip("/")
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


# --- Роуты ---

@router.get("/")
async def list_pages(request: Request):
    """Отображает список всех страниц."""
    connection = get_connection()
    try:
        cursor = connection.execute(
            "SELECT path, title, created_at, updated_at FROM pages ORDER BY path ASC"
        )
        pages = [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()

    return request.app.state.templates.TemplateResponse(
        "index.html",
        {"request": request, "pages": pages}
    )


@router.get("/new")
async def new_page_form(request: Request):
    """Форма создания новой страницы."""
    return request.app.state.templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "page": None,
            "title": "Создание страницы",
        }
    )


@router.post("/new")
async def create_page(
    request: Request,
    path: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
):
    """Создаёт новую страницу. Контент сохраняется как сырой Markdown."""
    # Нормализуем путь: добавляем ведущий слэш, убираем trailing слэш
    path = normalize_path(path)

    # Сохраняем сырой Markdown — рендеринг происходит при отображении
    connection = get_connection()
    try:
        connection.execute(
            """INSERT INTO pages (path, title, content, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (path, title, content, now_iso(), now_iso()),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Страница с путём {path} уже существует",
        )
    finally:
        connection.close()

    return RedirectResponse(
        url=f"/pages{path}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ВАЖНО: более специфичные роуты ДО catch-all /{path:path}
# Иначе /{path:path} перехватит /edit-test/edit как path="edit-test/edit"

@router.get("/{path:path}/edit")
async def edit_page_form(request: Request, path: str):
    """Форма редактирования существующей страницы."""
    path = normalize_path(path)
    connection = get_connection()
    try:
        cursor = connection.execute(
            "SELECT id, path, title, content FROM pages WHERE path = ?",
            (path,),
        )
        page = cursor.fetchone()
    finally:
        connection.close()

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Страница не найдена"
        )

    return request.app.state.templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "page": dict(page),
            "title": "Редактирование страницы",
        },
    )


@router.post("/{path:path}/edit")
async def update_page(
    request: Request,
    path: str,
    new_path: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
):
    """Обновляет существующую страницу. Контент сохраняется как сырой Markdown."""
    path = normalize_path(path)
    # Нормализуем новый путь
    new_path = normalize_path(new_path)

    # Сохраняем сырой Markdown — рендеринг происходит при отображении
    connection = get_connection()
    try:
        # Проверяем, не занял ли новый путь другая страница
        cursor = connection.execute(
            "SELECT id FROM pages WHERE path = ? AND path != ?",
            (new_path, path),
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Страница с путём {new_path} уже существует",
            )

        connection.execute(
            """UPDATE pages SET path = ?, title = ?, content = ?, updated_at = ? WHERE path = ?""",
            (new_path, title, content, now_iso(), path),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Страница с путём {new_path} уже существует",
        )
    finally:
        connection.close()

    # Перенаправляем на новый путь (если изменился)
    redirect_path = new_path if new_path != path else path
    return RedirectResponse(
        url=f"/pages{redirect_path}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{path:path}/delete")
async def delete_page(request: Request, path: str):
    """Удаляет страницу."""
    path = normalize_path(path)
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM pages WHERE path = ?",
            (path,),
        )
        connection.commit()
        deleted = cursor.rowcount > 0
    finally:
        connection.close()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Страница не найдена"
        )

    return RedirectResponse(
        url="/pages",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{path:path}")
async def view_page(request: Request, path: str):
    """Отображает страницу по полному пути (включая иерархические).
    Рендерит Markdown в HTML с очисткой через nh3 перед передачей в шаблон.
    """
    path = normalize_path(path)
    connection = get_connection()
    try:
        cursor = connection.execute(
            "SELECT id, path, title, content, created_at, updated_at FROM pages WHERE path = ?",
            (path,),
        )
        page = cursor.fetchone()
    finally:
        connection.close()

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Страница не найдена"
        )

    page_dict = dict(page)
    # Рендерим Markdown в HTML с XSS-очисткой
    page_dict["content"] = render_markdown(page_dict["content"])

    return request.app.state.templates.TemplateResponse(
        "page.html",
        {"request": request, "page": page_dict},
    )
