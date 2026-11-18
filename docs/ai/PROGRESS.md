# Спринт 0: Настройка окружения и минимальный запуск

## Статус: Завершён

## Что сделано
- Создана Docker-конфигурация: `Dockerfile`, `docker-compose.yml`
- Инициализирован `requirements.txt` с зависимостями: FastAPI, uvicorn, Jinja2, HTMX-стек, тесты
- Создана структура проекта согласно `PROJECT.md`:
  - `app/__init__.py` — Python-пакет
  - `app/main.py` — точка входа FastAPI с эндпоинтом `GET /health`
- Настроен Docker Compose: порт 8000, volume для hot-reload (`./app:/app/app`)

## Архитектурные решения
- SQLite вместо PostgreSQL для MVP (упрощение локальной разработки и CI)
- Jinja2 + HTMX вместо React/Vue (согласно `PROJECT.md`, минимизация зависимостей)
- `uvicorn` как ASGI-сервер (совместимость с FastAPI)

---

# Спринт 1: Модель страниц, CRUD, пути, Markdown + XSS

## Статус: Завершён

## Что сделано
- **База данных:** создана таблица `pages` с полями `id`, `path`, `title`, `content`, `created_at`, `updated_at`
- **CRUD для страниц:**
  - `GET /pages/` — список всех страниц
  - `GET /pages/new` — форма создания
  - `POST /pages/new` — создание страницы
  - `GET /pages/{path}` — просмотр страницы
  - `GET /pages/{path}/edit` — форма редактирования
  - `POST /pages/{path}/edit` — обновление страницы
  - `POST /pages/{path}/delete` — удаление страницы
- **Иерархические пути:** поддержка вложенных URL (`/docs/nlp`, `/docs/nlp/api`)
- **Markdown-рендеринг:** `markdown.markdown()` → `nh3.clean()` → очищенный HTML
- **XSS-защита:** все пользовательские данные проходят очистку через `nh3` перед сохранением
- **HTML-шаблоны:** `base.html`, `index.html`, `page.html`, `edit.html`
- **Тесты:** 17 тестов (CRUD + XSS + иерархические пути), все проходят

## Архитектурные решения
- `nh3.clean()` вместо `nh3.markdown()` — в библиотеке nh3 нет функции `markdown()`, используется `clean()` с whitelist-тегами
- Порядок роутов: более специфичные (`/{path}/edit`) ДО catch-all (`/{path:path}`), иначе catch-all перехватит запрос
- Путь нормализуется в каждом handler'е: ведущий слэш добавляется, trailing слэш убирается
- Путь к БД читается из `os.environ` при каждом запросе — позволяет переопределять в тестах
- `pytest-asyncio` добавлен в `requirements.txt` для поддержки async-тестов

## Тесты (18 passed)
- `TestPageList` (2): пустой список, список со страницами
- `TestPageCreate` (3): форма, создание, дубликат → 409
- `TestPageView` (3): просмотр, 404, иерархический путь `/docs/nlp`
- `TestPageEdit` (3): форма, обновление, переименование
- `TestPageDelete` (2): удаление, удаление несуществующей → 404
- `TestXSS` (5): `<script>alert(1)</script>`, `<img onerror>`, `<iframe>`, безопасный Markdown, fenced code blocks

## Исправления после Спринта 1
- Добавлен `extensions=["fenced_code"]` в `markdown.markdown()` — блоки кода ```python теперь рендерятся корректно в `<pre><code>`

# Спринт 1.1: Хранение сырого Markdown + исправление формы редактирования

## Статус: Завершён

## Что изменено
- **Архитектура хранения:** теперь в БД сохраняется сырой Markdown, а не HTML
  - `create_page`: `content` сохраняется как есть (без `render_markdown`)
  - `update_page`: `content` сохраняется как есть
  - `view_page`: рендеринг `render_markdown(content)` перед передачей в шаблон
- **XSS-защита:** nh3.clean() вызывается при рендеринге в `view_page`, а не при сохранении
- **Исправление 422 ошибки:** в `edit.html` при редактировании `name="new_path"`, при создании `name="path"`
- **Textarea:** теперь показывает Markdown, а не HTML

## Тесты (18 passed) — все прошли
- XSS-тесты подтверждают: `<script>` удаляется nh3 при рендеринге
- Markdown-рендеринг: `**bold**` → `<strong>`, fenced code → `<pre><code>`

## Что дальше
- Аутентификация и авторизация (argon2, роли: admin, editor, reader)
- Поиск по страницам
- Теги и дерево навигации
- Экспорт страниц в `.md` (для admin)
