import pytest
from httpx import AsyncClient


class TestPageList:
    """Тесты списка страниц."""

    @pytest.mark.asyncio
    async def test_list_pages_empty(self, client: AsyncClient):
        """Список страниц пуст при отсутствии страниц."""
        response = await client.get("/pages")
        assert response.status_code == 200
        assert "Страниц пока нет".encode("utf-8") in response.content

    @pytest.mark.asyncio
    async def test_list_pages_with_data(self, client: AsyncClient):
        """Список страниц содержит созданные страницы."""
        # Создаём страницу
        await client.post("/pages/new", data={
            "path": "/test-page",
            "title": "Test Page",
            "content": "Hello world",
        })
        # Проверяем список
        response = await client.get("/pages")
        assert response.status_code == 200
        assert b"Test Page" in response.content
        assert b"/test-page" in response.content


class TestPageCreate:
    """Тесты создания страниц."""

    @pytest.mark.asyncio
    async def test_new_page_form(self, client: AsyncClient):
        """Форма создания страницы доступна."""
        response = await client.get("/pages/new")
        assert response.status_code == 200
        assert "Создание страницы".encode("utf-8") in response.content

    @pytest.mark.asyncio
    async def test_create_page(self, client: AsyncClient):
        """Создание страницы через POST."""
        response = await client.post("/pages/new", data={
            "path": "/docs/intro",
            "title": "Introduction",
            "content": "# Hello\n\nWelcome to MiniWiki.",
        })
        # follow_redirects=True → финальный статус 200 после редиректа
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_duplicate_page(self, client: AsyncClient):
        """Попытка создать страницу с дублирующим путём возвращает 409."""
        await client.post("/pages/new", data={
            "path": "/duplicate",
            "title": "First",
            "content": "Content 1",
        })
        response = await client.post("/pages/new", data={
            "path": "/duplicate",
            "title": "Second",
            "content": "Content 2",
        })
        assert response.status_code == 409


class TestPageView:
    """Тесты просмотра страниц."""

    @pytest.mark.asyncio
    async def test_view_page(self, client: AsyncClient):
        """Просмотр существующей страницы."""
        await client.post("/pages/new", data={
            "path": "/view-test",
            "title": "View Test",
            "content": "Content to view",
        })
        response = await client.get("/pages/view-test")
        assert response.status_code == 200
        assert b"View Test" in response.content
        assert b"Content to view" in response.content

    @pytest.mark.asyncio
    async def test_view_page_not_found(self, client: AsyncClient):
        """Просмотр несуществующей страницы возвращает 404."""
        response = await client.get("/pages/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_hierarchical_path(self, client: AsyncClient):
        """Иерархический путь /docs/nlp работает корректно."""
        await client.post("/pages/new", data={
            "path": "/docs/nlp",
            "title": "NLP Docs",
            "content": "Natural Language Processing",
        })
        response = await client.get("/pages/docs/nlp")
        assert response.status_code == 200
        assert b"NLP Docs" in response.content


class TestPageEdit:
    """Тесты редактирования страниц."""

    @pytest.mark.asyncio
    async def test_edit_page_form(self, client: AsyncClient):
        """Форма редактирования доступна."""
        await client.post("/pages/new", data={
            "path": "/edit-test",
            "title": "Original",
            "content": "Original content",
        })
        response = await client.get("/pages/edit-test/edit")
        assert response.status_code == 200
        assert "Редактирование страницы".encode("utf-8") in response.content

    @pytest.mark.asyncio
    async def test_update_page(self, client: AsyncClient):
        """Обновление страницы."""
        await client.post("/pages/new", data={
            "path": "/update-test",
            "title": "Original Title",
            "content": "Original content",
        })
        response = await client.post("/pages/update-test/edit", data={
            "new_path": "/update-test",
            "title": "Updated Title",
            "content": "Updated content",
        })
        # follow_redirects=True → финальный статус 200
        assert response.status_code == 200

        # Проверяем, что изменения применились
        response = await client.get("/pages/update-test")
        assert b"Updated Title" in response.content
        assert b"Updated content" in response.content

    @pytest.mark.asyncio
    async def test_rename_page(self, client: AsyncClient):
        """Изменение пути страницы."""
        await client.post("/pages/new", data={
            "path": "/old-path",
            "title": "Rename Test",
            "content": "Content",
        })
        response = await client.post("/pages/old-path/edit", data={
            "new_path": "/new-path",
            "title": "Rename Test",
            "content": "Content",
        })
        # follow_redirects=True → финальный статус 200
        assert response.status_code == 200

        # Проверяем, что старая страница удалена
        response = await client.get("/pages/old-path")
        assert response.status_code == 404

        # Проверяем, что новая страница существует
        response = await client.get("/pages/new-path")
        assert response.status_code == 200
        assert b"Rename Test" in response.content


class TestPageDelete:
    """Тесты удаления страниц."""

    @pytest.mark.asyncio
    async def test_delete_page(self, client: AsyncClient):
        """Удаление страницы."""
        await client.post("/pages/new", data={
            "path": "/delete-test",
            "title": "To Delete",
            "content": "Content",
        })
        response = await client.post("/pages/delete-test/delete")
        # follow_redirects=True → финальный статус 200 после редиректа на /pages
        assert response.status_code == 200

        # Проверяем, что страница удалена
        response = await client.get("/pages/delete-test")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient):
        """Удаление несуществующей страницы возвращает 404."""
        response = await client.post("/pages/nonexistent/delete")
        assert response.status_code == 404


class TestXSS:
    """Критические тесты XSS-безопасности."""

    @pytest.mark.asyncio
    async def test_xss_script_in_content(self, client: AsyncClient):
        """
        Тест XSS: ввод <script>alert(1)</script> в контенте.
        Скрипт НЕ должен выполняться — тег <script> должен быть удалён nh3.
        """
        xss_payload = '<script>alert(1)</script>'
        await client.post("/pages/new", data={
            "path": "/xss-test",
            "title": "XSS Test",
            "content": xss_payload,
        })
        response = await client.get("/pages/xss-test")
        assert response.status_code == 200
        # Критично: тег <script> НЕ должен присутствовать в HTML-ответе
        assert "<script>" not in response.text.lower()
        assert "<script" not in response.text.lower()

    @pytest.mark.asyncio
    async def test_xss_html_in_title(self, client: AsyncClient):
        """
        Тест XSS: ввод <img src=x onerror=alert(1)> в заголовке.
        Jinja2 автоматически экранирует вывод, поэтому тег должен быть
        представлен как текстовая строка, а не выполнен.
        """
        xss_payload = '<img src=x onerror=alert(1)>'
        await client.post("/pages/new", data={
            "path": "/xss-title-test",
            "title": xss_payload,
            "content": "Safe content",
        })
        response = await client.get("/pages/xss-title-test")
        assert response.status_code == 200
        # Jinja2 автоматически экранирует title через {{ page.title }}
        # Тег <img> должен быть экранирован как текст
        assert "<img" not in response.text.lower() or "&lt;img" in response.text

    @pytest.mark.asyncio
    async def test_xss_iframe_in_content(self, client: AsyncClient):
        """
        Тест XSS: ввод <iframe> в контенте.
        Iframe должен быть удалён nh3.
        """
        xss_payload = '<iframe src="https://evil.com"></iframe>'
        await client.post("/pages/new", data={
            "path": "/xss-iframe-test",
            "title": "Iframe XSS Test",
            "content": xss_payload,
        })
        response = await client.get("/pages/xss-iframe-test")
        assert response.status_code == 200
        assert "<iframe" not in response.text.lower()

    @pytest.mark.asyncio
    async def test_safe_html_preserved(self, client: AsyncClient):
        """
        Безопасный Markdown должен корректно рендериться.
        Теги <strong>, <h1>, <p> и т.д. должны присутствовать.
        """
        await client.post("/pages/new", data={
            "path": "/safe-markdown",
            "title": "Safe Markdown",
            "content": "# Заголовок\n\n**Жирный текст** и *курсив*",
        })
        response = await client.get("/pages/safe-markdown")
        assert response.status_code == 200
        # Безопасные теги должны присутствовать
        assert "<h1>" in response.text
        assert "<strong>" in response.text or "<b>" in response.text
        assert "<em>" in response.text or "<i>" in response.text

    @pytest.mark.asyncio
    async def test_fenced_code_blocks(self, client: AsyncClient):
        """
        Блоки кода в формате fenced code (```python) должны рендериться
        в <pre><code>...</code></pre>.
        """
        content = """# Код

```python
def hello():
    print("Hello, World!")
```
"""
        await client.post("/pages/new", data={
            "path": "/code-test",
            "title": "Code Block Test",
            "content": content,
        })
        response = await client.get("/pages/code-test")
        assert response.status_code == 200
        # Fenced code blocks должны рендериться в <pre><code>
        assert "<pre" in response.text
        assert "<code" in response.text
