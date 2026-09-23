# Карта проекта: sensor-dashboard

## Что это
Пет-проект: веб-дашборд на Flask, показывающий показания датчиков (температура, давление, вибрация), которые симулятор отправляет по HTTP на собственный API. Сайт сам определяет состояние системы по порогам и живьём считает статистику по состояниям. Есть защищённая логином админка для ручного ввода показаний и правки порогов. Делается для практики полного цикла веб-разработки — от БД до хостинга.

## Стек
- Python 3.14 (venv в `.venv/`, в репозитории не хранится)
- Flask 3.1.3 — веб-сервер: страница `/`, API `/api/readings`, админка `/admin` с сессией, без шаблонов и стилей
- SQLite (файл `sensors.db`, в репозитории не хранится) локально / MySQL на хостинге — выбор через `DB_BACKEND` в `.env`, доступ только через `db.py` (см. Этап 6)
- PyMySQL — драйвер MySQL для прод-режима хостинга; чистый Python, компилятор не нужен (важно на shared-хостинге)
- Chart.js 4 через CDN (`<script>` в `app.py`) — график показаний с переключателем сырые/нормализованные/стандартизированные
- pytest — тесты чистых функций (`state.py`, `preprocessing.py`), API и админки (`test_client()`) и сверка с данными НИР, зависимость только для разработки (`requirements-dev.txt`)
- Секреты (`API_KEY`, `API_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`) — в `.env` (не в репозитории), читаются своим минимальным загрузчиком `config.py` на стандартной библиотеке
- `werkzeug.security` (приезжает вместе с Flask) — хеширование пароля админа и сравнение при входе
- Pico CSS 2 (classless, fluid) через CDN (`<link>` в `_page()`) — вся вёрстка на семантических тегах, без Bootstrap/Tailwind; тёмная тема переопределена через CSS-переменные Pico, включая единый `--pico-border-radius` (скругления в духе iOS по всему сайту одной переменной)
- Google Fonts (Inter — интерфейс, JetBrains Mono — все числа/таблицы) через CDN `<link>` в `_page()`
- Telegram Bot API — уведомление при переходе в «неисправность» (`notifications.py`), один POST через `urllib.request` (без библиотек), токен/chat_id в `.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, опционально `TELEGRAM_CHAT_ID_STAFF` — второй получатель без деталей)

## Структура
```
app.py               # Flask: главная страница, API /api/readings(+/range,+/export.csv), админка /login + /admin + /admin/logout
db.py                # единственный модуль работы с БД (readings + thresholds + users) — точка переезда на MySQL
config.py            # минимальный загрузчик .env (без внешних зависимостей)
state.py             # чистые функции определения состояния по порогам (без БД и Flask)
preprocessing.py     # чистые функции normalize()/standardize() (без БД и Flask)
notifications.py     # is_new_fault() + send_telegram_alert() — уведомление в Telegram при переходе в «неисправность»
simulator.py         # генерирует одну запись показаний и отправляет POST /api/readings (не трогает БД напрямую)
requirements.txt     # рантайм-зависимости (flask, pymysql)
requirements-dev.txt # зависимости для разработки (pytest)
pytest.ini           # добавляет корень проекта в PYTHONPATH для tests/
passenger_wsgi.py    # точка входа для Phusion Passenger на хостинге (Beget)
.env.example         # плейсхолдер для всех секретов и DB_*/TELEGRAM_* — реальный .env не в репозитории
tests/               # pytest: test_state.py, test_preprocessing.py, test_against_nir.py, test_api.py, test_admin.py,
                      # test_db_mysql.py (реальная MariaDB, пропускается если её нет), test_notifications.py,
                      # test_export.py, conftest.py, fixtures/data_raw.csv
harness/             # PROJECT.md и BRIEF/PLAN/REPORT по этапам (harness/stage-N/, включая бонусные stage-8/stage-9)
```

## Ключевые модули и точки входа
| Модуль | Где | За что отвечает |
|--------|-----|-----------------|
| `db.py` | `db.py` | Единственное место с SQL. Таблицы `readings`, `thresholds`, `users`. Бэкенд — SQLite или MySQL (`BACKEND`/`DB_BACKEND` в `.env`), диалект SQL — через `_sql(key)` и словари `_SQLITE_SQL`/`_MYSQL_SQL`, читается заново при каждом вызове (не один раз при импорте) — иначе `monkeypatch` в тестах не переключал бы диалект. Все функции принимают `path=None` (только для SQLite) → используют `db.DB_PATH` в момент вызова. `init_db()` сеет одного пользователя из `.env`, только если таблица `users` пуста. `get_readings_in_range(start, end)` — для просмотра/CSV-выгрузки за период. |
| `config.py` | `config.py` | Читает `.env` (или переменные окружения — у них приоритет) без внешних зависимостей. `config.get("API_KEY")`. |
| `state.py` | `state.py` | `classify_metric(value, warn, fault)` — состояние одного параметра по порогам; `classify_reading(temp, pressure, vibration, thresholds)` — итоговое состояние показания, правило «худшее из трёх» (см. DECISIONS.md). Чистые функции, без БД/Flask. |
| `preprocessing.py` | `preprocessing.py` | `normalize(values)` — приведение к [0,1]; `standardize(values)` — z-score. Чистые функции, без БД/Flask. |
| `notifications.py` | `notifications.py` | `is_new_fault(previous_state, current_state)` — чистая функция, True только на переходе в «неисправность» (не на каждом показании в этом состоянии). `send_telegram_alert(message, chat_id=None)` — один POST на Bot API, тихий no-op без токена, не роняет вызывающий код при сетевой ошибке. |
| `simulator.py` | `simulator.py` | Выбирает состояние, генерирует temp/pressure/vibration через `random.normalvariate` по mu/sd из НИР, отправляет `POST /api/readings` с заголовком `X-API-Key` через `urllib.request`. |
| `app.py` | `app.py` | `/` — индикатор+причина отклонения, гейджи по метрикам с пороговыми зонами, график (с пороговыми линиями и переключателем сырые/нормализованные/стандартизированные), таблицы, панель «Анализ показаний» (опрос `/api/readings?limit=1`, имитация загрузки), секция «Показания за период» (просмотр + CSV). `POST`/`GET /api/readings` — API с ключом (см. Этап 3). `GET /api/readings/range`, `GET /api/readings/export.csv` — выборка за период по дате+времени (JSON / CSV), публичные, без ключа. `/login` — форма входа, сессия через `session`/`SECRET_KEY`. `/admin` (за `login_required`) — форма ручного ввода показания и форма правки порогов. `/admin/logout` — сброс сессии. `_record_reading()` — общий хелпер вставки показания + триггер Telegram-уведомления, переиспользуется API и админкой. `_page()`/`PAGE_STYLES`/`_nav_html()` — общая обёртка страниц. |

## Как запустить / проверить
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env       # подставить свои API_KEY/ADMIN_PASSWORD/SECRET_KEY, например: python3 -c "import secrets; print(secrets.token_hex(32))"
python app.py               # сайт + API + админка на http://127.0.0.1:5000/
python simulator.py         # в другом терминале — отправить одну запись через HTTP (можно запускать многократно)
pytest                       # прогнать все тесты (логика, API и админка на временной БД, сверка с НИР)
```
Вход в админку: `/login`, логин/пароль — из `ADMIN_USERNAME`/`ADMIN_PASSWORD` в `.env` (сеются в БД при первом `init_db()`, если пользователей ещё нет).

Проверка MySQL-бэкенда локально (нужна только для разработки `db.py`, на обычном запуске сайта не требуется): `brew install mariadb && brew services start mariadb`, создать тестовую БД/пользователя, `DB_BACKEND=mysql` — тесты в `tests/test_db_mysql.py` подключатся сами; если MariaDB не поднята, эти тесты пропускаются (`skip`), а не падают.

## Known issues
- `app.py` собирает HTML прямой f-строкой без экранирования — безопасно только пока в таблице нет строковых данных, приходящих извне (сейчас всё из своего симулятора и своей же админки).
- `app.run(debug=True)` — только для разработки, для деплоя нужно будет заменить на прод-WSGI сервер.
- `simulator.py` отправляет ровно одну запись за запуск, непрерывного сбора (цикл/планировщик) пока нет — на хостинге запускается по cron (Этап 6, Часть B).
- MySQL-путь в `db.py` реально протестирован против локальной MariaDB (`tests/test_db_mysql.py`), но не против настоящей MySQL на Beget — первая реальная проверка будет при выкладке (Этап 6, Часть B).
- `GET /api/readings`, `GET /api/readings/range`, `GET /api/readings/export.csv` не защищены ключом API — осознанное решение (только чтение того же, что уже открыто на `/`), см. `DECISIONS.md`.
- Телефон/chat_id для Telegram-уведомлений — только в `.env` (локальном и серверном), никогда не передавались в открытом виде — если токен всё же попал в чат/лог, считать скомпрометированным и отзывать через `@BotFather` (`/revoke`).
- Смена пароля администратора после первого посева не реализована (нет формы «сменить пароль») — при необходимости пока только через `db.upsert_user()` вручную; не требовалось по заданию Этапа 4.
- Таблица «среднее ± σ» на сайте группирует показания по вычисленному через пороги состоянию (другого способа для реальных данных нет), поэтому её числа заметно отличаются от Таблицы 1 НИР (которая считалась по истинным меткам генерации) — см. `LESSONS.md`, запись про «худшее из трёх». Это ожидаемое поведение, не баг.
- На macOS порт 5000 может быть занят AirPlay Receiver — см. `LESSONS.md`.
- Пороги/агрегация/окно графика/устройство API/устройство админки — инженерные решения проекта, записаны в `DECISIONS.md` с обоснованием.
