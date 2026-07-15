# AEO Grader — спецификация MVP

## 1. Продукт в одном абзаце

AEO Grader — веб-приложение, которое генерирует разовый отчёт о видимости бренда в AI-поисковой выдаче Perplexity. Пользователь вводит URL сайта, система автоматически анализирует бренд, генерирует 10 релевантных поисковых запросов, прогоняет их через Perplexity Sonar Pro, парсит ответы и возвращает отчёт со Score 0–100, метриками, диаграммой Source Share of Voice, разбивкой по запросам и actionable-инсайтами. Аналог западного GEO-tooling (Profound, Otterly, Peec), но для российского рынка и в формате tripwire-аудита (single-shot отчёт, без подписки).

В MVP — без платежей, бесплатно для валидации спроса.

## 2. User flow

1. Лендинг: одно поле ввода — URL сайта, кнопка «Проанализировать»
2. Бэк парсит сайт (главная + до 3 ключевых страниц через ссылки)
3. LLM анализирует содержимое и извлекает:
   - Название бренда + список альтернативных написаний (для русского: «Тинькофф», «Tinkoff», «Т-Банк»)
   - Домен бренда
   - Описание (1-2 предложения)
   - Отрасль, ниша, целевая аудитория
   - 3–5 предполагаемых конкурентов с доменами
4. Отдельным вызовом LLM генерирует 10 поисковых запросов (промптов), которые целевая аудитория задаёт в AI-поисковиках
5. Пользователь видит страницу подтверждения с предзаполненными полями — может править бренд, конкурентов, промпты
6. Жмёт «Сгенерировать отчёт»
7. Бэк запускает прогон: 10 промптов через Perplexity Sonar Pro параллельно
8. Для каждого ответа парсит: citations (источники), упоминания бренда в тексте, упоминания конкурентов, тональность
9. Рассчитывает все метрики, сохраняет, отдаёт отчёт
10. Пользователь видит страницу отчёта на публичном URL `/report/{id}` — можно делиться ссылкой

Время от ввода URL до готового отчёта: ~60–90 секунд.

## 3. Технический стек

**Бэкенд:**
- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async) + Alembic
- PostgreSQL 16
- httpx (async HTTP)
- BeautifulSoup4 + lxml (парсинг сайтов)
- pydantic v2
- loguru (логирование)

**Фронтенд:**
- Next.js 15 (App Router) + TypeScript
- Tailwind CSS
- Минимум внешних библиотек: Recharts для диаграмм, никаких state managers — useState/useEffect

**Инфра:**
- Docker + docker-compose для локальной разработки
- `.env` для конфигурации

## 4. LLM-доступ — OpenRouter (единая точка входа)

Все LLM-вызовы идут через **OpenRouter**. Это OpenAI-совместимый API, который маршрутизирует запросы к десяткам провайдеров (Perplexity, OpenAI, Anthropic и др.) через один эндпоинт.

**Используемые модели:**
- `perplexity/sonar-pro` — основной прогон, измерение видимости. Возвращает citations (источники), что критично для продукта.
- `openai/gpt-4o-mini` — вспомогательные задачи (анализ сайта, генерация промптов, sentiment-классификация). Дешёвая, быстрая, для этих задач хватает с запасом.

**Конфигурация (env):**
```
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MODEL_MAIN=perplexity/sonar-pro
MODEL_AUX=openai/gpt-4o-mini
```

**Архитектура провайдер-агностична.** Любой OpenAI-совместимый эндпоинт можно подставить, поменяв `OPENROUTER_BASE_URL` и ключ. Это страховка на случай проблем с OpenRouter — можно за 5 минут переключиться на российский агрегатор (ProxyAPI, AITunnel) без изменений в коде.

**Critical risk to verify on day 1:**
Citations от Perplexity через OpenRouter возвращаются как кастомное поле `citations` в корне ответа (массив URL), либо в `choices[0].message.annotations`. Это **обязательно проверить первым же тестовым вызовом** перед написанием любого другого кода. Если citations не пробрасываются — продукт не работает, и нужно искать обходной путь (пробросить через `extra_body`, использовать прямой Perplexity API через посредника, итд).

## 5. Архитектура

Простой монолит без отдельной очереди:

```
[Next.js фронт] <-> [FastAPI бэк] <-> [PostgreSQL]
                         |
                         +-> OpenRouter API (все LLM-вызовы)
                         +-> Site scraping
```

Долгие задачи (анализ сайта + генерация отчёта) — FastAPI BackgroundTasks. Фронт polls статус каждые 2 секунды. Никакого Redis/Celery в MVP.

## 6. Структура проекта

```
aeo-grader/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry
│   │   ├── config.py               # настройки из env
│   │   ├── database.py             # async session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── report.py
│   │   │   └── prompt_result.py
│   │   ├── schemas/                # Pydantic
│   │   │   ├── analyze.py
│   │   │   └── report.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── analyze.py
│   │   │   └── report.py
│   │   ├── services/
│   │   │   ├── llm_client.py        # единый клиент OpenRouter
│   │   │   ├── site_parser.py
│   │   │   ├── brand_analyzer.py
│   │   │   ├── prompt_generator.py
│   │   │   ├── citation_matcher.py
│   │   │   ├── mention_matcher.py
│   │   │   ├── sentiment_classifier.py
│   │   │   ├── score_calculator.py
│   │   │   └── source_aggregator.py
│   │   ├── tasks/
│   │   │   ├── analyze_site.py
│   │   │   └── generate_report.py
│   │   └── prompts/                # тексты LLM-промптов
│   │       ├── brand_analyzer.txt
│   │       ├── prompt_generator.txt
│   │       └── sentiment_classifier.txt
│   ├── alembic/
│   ├── tests/
│   │   └── test_openrouter_citations.py    # critical day-1 проверка
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # лендинг
│   │   ├── analyze/[id]/page.tsx   # подтверждение
│   │   └── report/[id]/page.tsx    # отчёт
│   ├── components/
│   │   ├── UrlForm.tsx
│   │   ├── ConfirmationForm.tsx
│   │   ├── ScoreHero.tsx
│   │   ├── MetricCards.tsx
│   │   ├── SourceShareOfVoice.tsx
│   │   ├── PromptBreakdown.tsx
│   │   ├── ActionableInsights.tsx
│   │   ├── Methodology.tsx
│   │   └── LoadingState.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── README.md
└── SPEC.md
```

## 7. API endpoints

### POST /api/analyze
Запрос: `{ url: string }`
Действие: создаёт `Report` со статусом `analyzing`, запускает background task `analyze_site`
Ответ: `{ id: string, status: "analyzing" }`

### GET /api/analyze/{id}
Ответ: текущий статус + (если готово) объект с brand_name, brand_domain, brand_description, brand_aliases, competitors, suggested_prompts

### PATCH /api/analyze/{id}
Запрос: пользовательские правки — brand_name, brand_aliases, competitors, prompts, email (опц.)
Действие: сохраняет правки, меняет статус на `generating`, запускает background task `generate_report`
Ответ: `{ id, status: "generating" }`

### GET /api/report/{id}
Ответ: текущий статус + (если completed) полный отчёт со всеми полями (см. модель Report)

### GET /api/health
Просто `{ "status": "ok" }`

## 8. БД-модели

### Report
- `id` — UUID, primary key
- `created_at`, `updated_at` — timestamps
- `status` — enum: `analyzing`, `awaiting_confirmation`, `generating`, `completed`, `failed`
- `url` — string
- `brand_name` — string nullable
- `brand_domain` — string nullable (нормализованный, без www и схемы)
- `brand_aliases` — JSON (массив строк: альтернативные написания)
- `brand_description` — text nullable
- `industry` — string nullable
- `competitors` — JSON (массив `{ name: string, domain: string }`)
- `prompts` — JSON (массив строк)
- `email` — string nullable
- `aeo_score` — float nullable
- `citation_rate` — float nullable (0–1)
- `mention_rate` — float nullable (0–1)
- `sentiment_summary` — enum nullable: `positive`, `neutral`, `mixed`, `negative`
- `source_share_of_voice` — JSON nullable (массив `{ domain: string, count: int, is_brand: bool, is_competitor: bool }`, отсортированный по count)
- `error` — text nullable

### PromptResult
- `id` — UUID
- `report_id` — FK
- `prompt` — text
- `raw_response` — text (полный ответ Perplexity)
- `citations` — JSON (массив доменов, извлечённых из источников)
- `brand_cited` — bool
- `brand_mentioned` — bool
- `competitors_cited` — JSON (массив доменов)
- `competitors_mentioned` — JSON (массив названий)
- `sentiment` — enum nullable: `positive`, `neutral`, `negative`
- `created_at` — timestamp

## 9. Логика сервисов

### llm_client.py — единый клиент OpenRouter

Async-функция `query(prompt: str, model: str, response_format: dict | None = None) -> LLMResponse`:
- POST на `{OPENROUTER_BASE_URL}/chat/completions`
- Headers: `Authorization: Bearer {OPENROUTER_API_KEY}`, рекомендованные OpenRouter заголовки `HTTP-Referer` (OPENROUTER_SITE_URL) и `X-Title` (OPENROUTER_APP_NAME) — нужны для статистики и приоритезации
- Body: `{ "model": model, "messages": [{"role": "user", "content": prompt}], "response_format": response_format }`
- Возврат: dataclass `LLMResponse(text: str, citations: list[str], raw: dict)`
- Citations извлекаются из ответа: проверять оба места — корневое поле `citations` и `choices[0].message.annotations`. Для не-Perplexity моделей — пустой массив.
- Таймаут 30 секунд на запрос
- Один ретрай на 5xx с экспоненциальным backoff

**Важно:** клиент один на всё приложение, модель передаётся параметром. Никаких отдельных perplexity_client / openai_client.

### site_parser.py
- httpx GET главной страницы (timeout 10s, follow_redirects, User-Agent как у обычного браузера)
- BeautifulSoup → извлечение `<title>`, `<meta name="description">`, всего видимого текста (`<p>`, `<h1-h3>`, `<li>`)
- Поиск ссылок на типичные служебные страницы (about, о-нас, услуги, продукты, services, products) — берётся до 3 ссылок
- Загрузка этих страниц, добавление текста
- На выходе словарь: `{ home_text: str, sub_pages: list[str], meta: dict, url: str }`, общий объём текста до 10000 символов

### brand_analyzer.py
Один вызов `llm_client.query(model=MODEL_AUX, response_format={"type": "json_object"})` с system prompt из `prompts/brand_analyzer.txt`. На вход — собранный текст сайта + URL. На выход — JSON со структурой:
```json
{
  "brand_name": "Тинькофф",
  "brand_domain": "tinkoff.ru",
  "brand_aliases": ["Тинькофф", "Tinkoff", "Т-Банк", "Тиньков"],
  "brand_description": "Российский онлайн-банк...",
  "industry": "Финансы / банкинг",
  "competitors": [
    { "name": "Сбер", "domain": "sber.ru" },
    { "name": "Альфа-Банк", "domain": "alfabank.ru" }
  ]
}
```
Важно: бренд-aliases должны включать кириллические и латинские варианты, склонения, сокращения. Это используется в mention_matcher.

### prompt_generator.py
Один вызов `llm_client.query(model=MODEL_AUX)` с system prompt из `prompts/prompt_generator.txt`. На вход — данные о бренде. На выход — массив из 10 строк.

Принципы для промпта (явно прописать в system prompt):
- Запросы на русском языке
- Высокая коммерческая ценность (сравнения, рекомендации, «лучший», «как выбрать», «что выбрать для X»)
- Без прямого упоминания самого бренда
- Конкретные, отражающие реальный путь пользователя
- Разнообразие: ~40% сравнений, ~30% «как выбрать», ~30% «топ/лучший»

### citation_matcher.py
Принимает: список URL + `brand_domain` + `competitor_domains`
- Извлекает домен из каждого URL (через urllib.parse, нормализация: lowercase, удаление www., удаление пути)
- Сравнивает с brand_domain (через `endswith` для поддоменов: `blog.tinkoff.ru` тоже считается)
- Возврат: `{ brand_cited: bool, competitors_cited: list[domain], all_cited_domains: list[str] }`

### mention_matcher.py
Принимает: текст ответа + `brand_aliases` + `competitor_names`
- Для каждого alias строит regex с word boundary для кириллицы: использовать lookahead/lookbehind с `[\W_]` или явные проверки на не-буквенные символы вокруг alias (стандартный `\b` плохо работает с кириллицей)
- Case-insensitive
- Возврат: `{ brand_mentioned: bool, competitors_mentioned: list[name] }`

### sentiment_classifier.py
Только если `brand_mentioned == True` (экономит токены: у большинства брендов видимость низкая, и львиная доля промптов не будет иметь упоминаний). Один вызов `llm_client.query(model=MODEL_AUX, response_format={"type": "json_object"})` с system prompt из `prompts/sentiment_classifier.txt`. На вход — текст ответа + название бренда. На выход — одно из трёх: `positive`, `neutral`, `negative`.

### score_calculator.py
```python
def calculate_aeo_score(
    citation_rate: float,
    mention_rate: float,
    sentiment_summary: str,
) -> float:
    base = (citation_rate * 0.6 + mention_rate * 0.4) * 100
    if sentiment_summary == "negative":
        penalty = 0.7
    elif sentiment_summary == "mixed":
        penalty = 0.85
    else:
        penalty = 1.0
    return round(base * penalty, 1)


def determine_sentiment_summary(sentiments: list[str]) -> str:
    """Из списка тональностей упоминаний → агрегированная оценка."""
    has_neg = "negative" in sentiments
    has_pos = "positive" in sentiments
    if has_neg and has_pos:
        return "mixed"
    if has_neg:
        return "negative"
    if has_pos:
        return "positive"
    return "neutral"
```

### source_aggregator.py
Принимает список всех PromptResult → собирает все домены из citations всех ответов → считает частоту → возвращает топ-15 с пометками `is_brand`, `is_competitor`.

## 10. Страница отчёта — структура блоков

### Hero
- Большая цифра Score (0–100) с цветной меткой уровня:
  - 0–19 «Невидимы для AI» (красный)
  - 20–39 «Слабая видимость» (оранжевый)
  - 40–59 «Средняя видимость» (жёлтый)
  - 60–79 «Сильная видимость» (зелёный)
  - 80–100 «Лидер ниши» (тёмно-зелёный)
- Одно предложение-summary: «Brand X виден в Perplexity слабо: цитируется в 2 из 10 запросов, конкуренты Y и Z цитируются в 7 и 6». Генерируется на лету по шаблону (без LLM, чистый Python).
- Дельта до следующего уровня

### Метрики (4 карточки)
- Citation Rate (% запросов с цитатой бренда в источниках)
- Mention Rate (% запросов с упоминанием бренда в тексте)
- Sentiment (агрегированная оценка)
- Authority Rank (позиция домена бренда в Source Share of Voice; если нет в топе — «вне топ-15»)

### Source Share of Voice
- Горизонтальная bar-диаграмма топ-15 доменов
- Цвета: зелёный = бренд, синий = конкурент из списка, серый = остальные
- Под диаграммой: «Топ-5 “чужих” доменов в вашей нише» — кликабельные ссылки

### Разбивка по промптам
- Таблица: промпт, citation (✅/❌), mention (✅/❌), sentiment, конкуренты вместо вас
- По клику строка раскрывается: полный raw response, все citations (полные URL-ы), подсветка упоминаний бренда и конкурентов в тексте

### Actionable insights
- «Приоритетные промпты для проработки»: 3–5 «красных» промптов с указанием конкретных конкурирующих доменов
- «Топ-источники для размещения»: 5–10 чужих доменов из SoV, где вас нет, но которые цитируются
- «Sentiment-флаги» (только если есть негатив): промпты с негативным sentiment + сырые цитаты

### Методология (раскрывающийся блок)
- Список использованных промптов
- Какая модель (Perplexity Sonar Pro через OpenRouter), дата прогона
- Формула Score (текстом и кодом)
- Как определяется sentiment
- Дисклеймер: «Score основан на 10 промптах × 1 прогон. Точность ±10 пунктов из-за стохастичности AI-ответов».

### CTA внизу
- «Скопировать публичную ссылку»
- «Скачать PDF» (заглушка в MVP — кнопка с подписью «Скоро»)
- «Заказать deep-аудит» (форма с email — собирает предзаказы)

## 11. Что НЕ входит в MVP

- Платежи
- Email-уведомления (только страница с polling)
- PDF-генерация
- Личный кабинет / история отчётов
- Регистрация
- Мониторинг во времени
- YandexGPT, ChatGPT, GigaChat в качестве предметов измерения — только Perplexity (хотя через тот же OpenRouter их легко добавить в v2)
- Скрейпинг Яндекс Нейро
- Глубокие content-рекомендации с готовыми текстами
- Алерты в Telegram
- Multi-language (только русский на старте)
- Vertical-specific промпт-библиотеки

## 12. Конфигурация (.env.example)

```
DATABASE_URL=postgresql+asyncpg://aeo:aeo@db:5432/aeo

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MODEL_MAIN=perplexity/sonar-pro
MODEL_AUX=openai/gpt-4o-mini

# Опциональные заголовки OpenRouter для статистики
OPENROUTER_APP_NAME=AEO Grader
OPENROUTER_SITE_URL=http://localhost:3000

FRONTEND_ORIGIN=http://localhost:3000
LOG_LEVEL=INFO
```

## 13. Обработка ошибок

- Сайт недоступен / 404 → статус `failed`, error: «Не удалось загрузить сайт»
- Сайт без читаемого контента → статус `failed`, error: «Сайт не содержит достаточно контента для анализа»
- OpenRouter timeout на одном из промптов основного прогона → конкретный PromptResult помечается ошибкой, остальные продолжают; если упало >50% промптов → весь отчёт `failed`
- OpenRouter timeout на вспомогательном вызове → ретрай 1 раз с backoff, потом fail
- 401/403 от OpenRouter → отдельный понятный лог про ключ
- Все ошибки логируются через loguru с полным контекстом

## 14. Безопасность и rate limiting

- Простой in-memory rate limit по IP: 5 анализов в час (для MVP достаточно, при масштабировании заменим на Redis)
- Валидация URL: только http/https, не локальные адреса (127.0.0.1, 192.168.*, 10.*, и т. д.)
- Все user-input санитизируются перед сохранением

## 15. Acceptance criteria для MVP

1. `docker-compose up` поднимает всю систему
2. Тестовый вызов Perplexity Sonar Pro через OpenRouter возвращает текст + массив citations (проверено на этапе 0)
3. Пользователь вводит URL известного российского бренда → получает заполненную форму подтверждения за ~15 секунд
4. После подтверждения отчёт генерируется за ~60–90 секунд
5. Отчёт содержит все блоки из раздела 10, цифры обоснованы и видны в детализации
6. Публичная ссылка работает: можно поделиться, любой откроет
7. Тестовый прогон на двух сайтах: один крупный (например, tinkoff.ru), один малоизвестный B2B SaaS — оба завершаются без ошибок и дают осмысленные результаты
