# AEO Grader

Веб-приложение для разового отчёта о видимости бренда в AI-поисковой выдаче Perplexity. Подробности — в [SPEC.md](./SPEC.md).

## Стек

- Backend: Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 16
- Frontend: Next.js 15 (App Router) + TypeScript + Tailwind
- LLM-доступ: OpenRouter (модели `perplexity/sonar-pro` и `openai/gpt-4o-mini`)

## Быстрый старт

1. Скопируй `backend/.env.example` в `backend/.env` и заполни `OPENROUTER_API_KEY`:
   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```
2. Подними стек:
   ```powershell
   docker-compose up --build
   ```
3. Открой:
   - Фронт: http://localhost:3000 — должна отобразиться надпись «AEO Grader»
   - Healthcheck бэка: http://localhost:8000/api/health → `{"status":"ok"}`

## Миграции БД

Alembic запускается изнутри контейнера backend:

```powershell
docker-compose exec backend alembic revision --autogenerate -m "init"
docker-compose exec backend alembic upgrade head
```

На этапе 0 моделей ещё нет — миграции появятся начиная с этапа 1.

## Тесты

```powershell
docker-compose exec backend pytest
```

Критический тест проверки citations через OpenRouter (этап 0.5):
```powershell
docker-compose exec backend pytest tests/test_openrouter_citations.py -s
```

## Структура

```
aeo-grader/
├── backend/   # FastAPI, SQLAlchemy, Alembic
├── frontend/  # Next.js 15
├── docker-compose.yml
└── SPEC.md    # полное ТЗ
```
