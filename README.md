# Пульт мониторинга технической системы

Пет-проект: веб-сайт на Flask, который собирает показания датчиков (температура, давление, вибрация) от симулятора, хранит их в базе, определяет состояние системы (норма/предупреждение/неисправность) и показывает всё это на живом дашборде с графиками. Тема данных взята из собственной научной работы автора; проект делается для практики полного цикла веб-разработки — от кода и базы до хостинга.

## Быстрый старт локально

```bash
git clone https://github.com/McFluury-1337/sensor-dashboard.git
cd sensor-dashboard

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env
```

Открыть `.env` и подставить свои значения вместо `changeme` (`DB_*` трогать не нужно — по умолчанию используется SQLite):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"   # для API_KEY и SECRET_KEY
```

`ADMIN_PASSWORD` — любой пароль, которым будете входить в `/login`.

Дальше — два терминала:

```bash
# терминал 1 — сайт + API + админка
source .venv/bin/activate
python app.py
```

```bash
# терминал 2 — отправить показание через API (можно запускать многократно)
source .venv/bin/activate
python simulator.py
```

Открыть [http://127.0.0.1:5000/](http://127.0.0.1:5000/) — таблица и график должны показывать данные, а после каждого `python simulator.py` — новую строку.

Админка: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login), логин/пароль — `ADMIN_USERNAME`/`ADMIN_PASSWORD` из `.env`.

Тесты:

```bash
pytest
```

На macOS, если сервер стартовал, а страница не открывается — см. `LESSONS.md` про порт 5000 и AirPlay Receiver.

## Деплой на хостинг (Beget)

Код готов к выкладке: `passenger_wsgi.py` (точка входа для Phusion Passenger) и MySQL-бэкенд в `db.py` (переключается переменной `DB_BACKEND=mysql` в серверном `.env`) уже в репозитории. Полная пошаговая инструкция — в [harness/stage-6/RUNBOOK.md](harness/stage-6/RUNBOOK.md): регистрация аккаунта, создание сайта, SSH и Docker-окружение, MySQL в панели, `.env` на сервере, HTTPS через Let's Encrypt, cron для симулятора.

**Статус на сейчас: развёрнуто и работает.** Живой сайт: [https://sensor-dashboard.ru](https://sensor-dashboard.ru) (HTTP автоматически редиректит на HTTPS), MySQL-бэкенд, cron каждые 5 минут пишет новые показания через `simulator.py`. Детали и хронология деплоя — в [harness/stage-6/REPORT.md](harness/stage-6/REPORT.md).

## Стек

Python 3, Flask, SQLite (локально) / MySQL (на хостинге), Chart.js, Pico CSS — без Bootstrap/Tailwind, без ORM и фреймворков поверх Flask. Подробности и обоснования — в [DECISIONS.md](DECISIONS.md).

## Структура проекта и журналы

- [harness/PROJECT.md](harness/PROJECT.md) — карта проекта: модули, точки входа, известные особенности.
- [DECISIONS.md](DECISIONS.md) — инженерные решения с причинами (пороги состояний, устройство API, выбор MySQL-драйвера и т.д.).
- [LESSONS.md](LESSONS.md) — реальные грабли по ходу разработки, не «всё прошло гладко».
- `harness/stage-1/` … `harness/stage-7/` — BRIEF/PLAN/REPORT по каждому этапу разработки (этапы описаны в задании куратора).

## Что ещё не готово

- Хостинг развёрнут и HTTPS работает (см. выше), но требование «сайт живёт минимум неделю без сдачи» (Этап 6) может быть подтверждено только по факту истечения этого срока с 2026-09-22 — не раньше 2026-09-29.

Всё остальное — локальный запуск, тесты, API, админка, внешний вид, деплой, HTTPS — сделано и проверено, детали в `harness/stage-N/REPORT.md`.
