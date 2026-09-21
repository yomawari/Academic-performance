# Учёт успеваемости

Информационная система для учёта успеваемости студентов: учебные группы, дисциплины,
преподаватели, занятия, оценки и посещаемость. Курсовой проект по дисциплине
«Технологии разработки программного обеспечения».

## Стек

- **Python 3.14**, **FastAPI**, **Uvicorn**
- **SQLite** через стандартный модуль `sqlite3` (без ORM и без отдельного сервера БД)
- **Pydantic v2** — модели, сгенерированные из OpenAPI-контракта
- **Ванильный JavaScript** (SPA без сборщика), HTML и CSS
- **pytest** + `TestClient` — автотесты API

## Структура проекта

```
academic performance/
├── api/
│   └── openapi.yaml          # контракт API — источник истины (API First)
├── backend/
│   ├── schema.sql            # схема БД: 11 таблиц, связи M2M
│   ├── seed.py               # демонстрационные данные
│   └── app/
│       ├── main.py           # приложение FastAPI, статика, обработчики ошибок
│       ├── config.py         # пути, параметры сессии
│       ├── db.py             # подключение к SQLite, инициализация
│       ├── security.py       # scrypt-хеши, подпись cookie
│       ├── deps.py           # аутентификация и проверка ролей
│       ├── audit.py          # журнал действий
│       ├── contract/models.py# Pydantic-модели из OpenAPI
│       ├── repositories/     # SQL-запросы (параметризованные)
│       └── routers/          # эндпоинты API
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js, js/api-client.js
├── scripts/
│   ├── generate_models.py    # OpenAPI → Pydantic
│   └── generate_client.py    # OpenAPI → JS-клиент
├── tests/                    # pytest
├── requirements.txt
└── run.ps1
```

## Запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\run.ps1
```

Приложение откроется на <http://127.0.0.1:8000>, документация API —
<http://127.0.0.1:8000/docs>.

База данных `backend/data/academic.db` создаётся автоматически при первом запуске
и заполняется демонстрационными данными (12 студентов, 3 группы, 3 преподавателя,
5 дисциплин, 39 занятий, 142 оценки).

### Демонстрационные учётные записи

| Роль | Логин | Пароль |
|------|-------|--------|
| Администратор | `admin` | `admin123` |
| Преподаватель | `teacher` | `teacher123` |
| Студент | `student` | `student123` |

## API First

Контракт [`api/openapi.yaml`](api/openapi.yaml) описывает все эндпоинты, схемы и коды
ответов. Из него генерируются:

```powershell
python scripts/generate_models.py   # backend/app/contract/models.py
python scripts/generate_client.py   # frontend/js/api-client.js
```

Тест `tests/test_contract.py` проверяет, что фактическая схема FastAPI совпадает
с контрактом.

## База данных

11 таблиц: `users`, `teachers`, `groups`, `students`, `subjects`, `lessons`, `grades`,
`attendance`, `teacher_subject`, `group_subject`, `audit_log`.

- связи «один ко многим»: группа → студенты, преподаватель → дисциплины, дисциплина → занятия;
- связи «многие ко многим»: `teacher_subject`, `group_subject`, `grades`, `attendance`;
- ограничения `FOREIGN KEY`, `UNIQUE`, `CHECK`; каскадное удаление и `ON DELETE SET NULL`;
- все запросы параметризованы — SQL-инъекции исключены.

Пароли хранятся в виде scrypt-хешей, сессия — в HttpOnly cookie с HMAC-подписью.
Все изменения фиксируются в журнале `audit_log`.

## Тесты

```powershell
python -m pytest -q
```

Покрыты: аутентификация, разграничение ролей, CRUD справочников, защита от SQL-инъекций,
соответствие контракту.

## Этапы разработки

- **Этап 1 (текущий):** схема БД, OpenAPI-контракт, аутентификация, простые справочники
  (группы, студенты, преподаватели, дисциплины), главная страница, тесты.
- **Этап 2:** занятия, журнал оценок и посещаемости, отчёты, экспорт.
- **Этап 3:** проектная документация (UML, BPMN, Draw.io), скриншоты, пояснительная записка.
