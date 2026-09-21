# Карта проекта: sensor-dashboard

## Что это
Пет-проект: веб-дашборд на Flask, показывающий показания датчиков (температура, давление, вибрация), которые симулятор отправляет по HTTP на собственный API. Сайт сам определяет состояние системы по порогам и живьём считает статистику по состояниям. Делается для практики полного цикла веб-разработки — от БД до хостинга.

## Стек
- Python 3.14 (venv в `.venv/`, в репозитории не хранится)
- Flask 3.1.3 — веб-сервер: страница `/` и API `/api/readings`, без шаблонов и стилей
- SQLite (файл `sensors.db`, в репозитории не хранится) — хранилище показаний и порогов, доступ только через `db.py`, чтобы позже можно было переключиться на MySQL
- Chart.js 4 через CDN (`<script>` в `app.py`) — график показаний с переключателем сырые/нормализованные/стандартизированные
- pytest — тесты чистых функций (`state.py`, `preprocessing.py`), API (`test_client()`) и сверка с данными НИР, зависимость только для разработки (`requirements-dev.txt`)
- Секреты (`API_KEY`, `API_URL`) — в `.env` (не в репозитории), читаются своим минимальным загрузчиком `config.py` на стандартной библиотеке

## Структура
```
app.py               # Flask: индикатор состояния, график Chart.js, таблица среднее±σ, таблица последних 50; API POST/GET /api/readings
db.py                # единственный модуль работы с БД (readings + thresholds) — точка переезда на MySQL
config.py            # минимальный загрузчик .env (без внешних зависимостей)
state.py             # чистые функции определения состояния по порогам (без БД и Flask)
preprocessing.py     # чистые функции normalize()/standardize() (без БД и Flask)
simulator.py         # генерирует одну запись показаний и отправляет POST /api/readings (не трогает БД напрямую)
requirements.txt     # рантайм-зависимости (flask)
requirements-dev.txt # зависимости для разработки (pytest)
pytest.ini           # добавляет корень проекта в PYTHONPATH для tests/
.env.example         # плейсхолдер для API_KEY/API_URL — реальный .env не в репозитории
tests/               # pytest: test_state.py, test_preprocessing.py, test_against_nir.py, test_api.py, conftest.py (временная БД для API-тестов), fixtures/data_raw.csv
harness/             # PROJECT.md и BRIEF/PLAN/REPORT по этапам (harness/stage-N/)
```

## Ключевые модули и точки входа
| Модуль | Где | За что отвечает |
|--------|-----|-----------------|
| `db.py` | `db.py` | Подключение к SQLite, таблицы `readings` и `thresholds`, CRUD-функции. Единственное место с SQL. Все функции принимают `path=None` → используют `db.DB_PATH` в момент вызова (не в момент объявления) — тесты подставляют временный файл через `monkeypatch.setattr(db, "DB_PATH", ...)`. |
| `config.py` | `config.py` | Читает `.env` (или переменные окружения — у них приоритет) без внешних зависимостей. `config.get("API_KEY")`. |
| `state.py` | `state.py` | `classify_metric(value, warn, fault)` — состояние одного параметра по порогам; `classify_reading(temp, pressure, vibration, thresholds)` — итоговое состояние показания, правило «худшее из трёх» (см. DECISIONS.md). Чистые функции, без БД/Flask. |
| `preprocessing.py` | `preprocessing.py` | `normalize(values)` — приведение к [0,1]; `standardize(values)` — z-score. Чистые функции, без БД/Flask. |
| `simulator.py` | `simulator.py` | Выбирает состояние, генерирует temp/pressure/vibration через `random.normalvariate` по mu/sd из НИР, отправляет `POST /api/readings` с заголовком `X-API-Key` через `urllib.request`. |
| `app.py` | `app.py` | Роут `/` — индикатор, график, таблицы (как раньше). `POST /api/readings` — проверка ключа (`hmac.compare_digest`), проверка типов/знака трёх полей, запись через `db.py`, 201/400/401. `GET /api/readings?limit=N` — без проверки ключа, JSON последних N записей. |

## Как запустить / проверить
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env       # и подставить свой API_KEY (например: python3 -c "import secrets; print(secrets.token_hex(32))")
python app.py               # запустить сайт + API на http://127.0.0.1:5000/
python simulator.py         # в другом терминале — отправить одну запись через HTTP (можно запускать многократно)
pytest                       # прогнать все тесты (логика, API на временной БД, сверка с НИР)
```

## Known issues
- `app.py` собирает HTML прямой f-строкой без экранирования — безопасно только пока в таблице нет строковых данных, приходящих извне (сейчас всё из своего симулятора).
- `app.run(debug=True)` — только для разработки, для деплоя нужно будет заменить на прод-WSGI сервер.
- `simulator.py` отправляет ровно одну запись за запуск, непрерывного сбора (цикл/планировщик) пока нет — отдельный этап (Этап 6, cron).
- `GET /api/readings` не защищён ключом API — осознанное решение (только читает то же, что уже открыто на `/`), см. `DECISIONS.md`.
- Таблица «среднее ± σ» на сайте группирует показания по вычисленному через пороги состоянию (другого способа для реальных данных нет), поэтому её числа заметно отличаются от Таблицы 1 НИР (которая считалась по истинным меткам генерации) — см. `LESSONS.md`, запись про «худшее из трёх». Это ожидаемое поведение, не баг.
- На macOS порт 5000 может быть занят AirPlay Receiver — см. `LESSONS.md`.
- Пороги/агрегация/окно графика/устройство API — инженерные решения проекта, записаны в `DECISIONS.md` с обоснованием.
