# PLAN: Этап 4 — админка

Дата: 2026-09-21

## Шаги

1. `db.py`: добавить таблицу `users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)`. `init_db()` — если пользователей ещё нет (`SELECT COUNT(*)`), засеять одного из `config.get("ADMIN_USERNAME", "admin")` / `config.get("ADMIN_PASSWORD")` (если пароль не задан — пропустить посев, без дефолтного пароля в коде). Добавить `db.get_user(username, path=None)` (возвращает `password_hash` или `None`) и `db.upsert_user(username, password_hash, path=None)` (для тестов — детерминированно задать пароль). Добавить `db.update_threshold(metric, warn_boundary, fault_boundary, path=None)`.
2. Обновить `.env`/`.env.example`: `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`. Сгенерировать реальные значения в `.env` (не в репозитории).
3. Обновить `tests/conftest.py`: после `db.init_db()` — `db.upsert_user("admin", generate_password_hash("test-password"))`, чтобы тесты не зависели от случайного пароля из `.env`. Добавить `app.secret_key` для тестового клиента (уже будет установлен из `.env`/monkeypatch).
4. Написать `tests/test_admin.py` — красные тесты (роутов ещё нет): `/admin` без логина → редирект на `/login`; POST `/login` с неверным паролем → остаёшься вне `/admin`; POST `/login` с верным паролем → `/admin` доступен; POST `/admin/readings` без логина → редирект; POST `/admin/readings` при логине → запись в БД; POST `/admin/thresholds` при логине → пороги обновлены и видны в `db.get_thresholds()`; POST `/admin/thresholds` с warn ≥ fault → не сохраняет.
5. Реализовать в `app.py`: `app.secret_key = config.get("SECRET_KEY")`, декоратор `login_required`, `/login` (GET форма, POST проверка через `check_password_hash`), `/admin/logout`, `/admin` (GET — две формы, пороги предзаполнены текущими значениями), `/admin/readings` (POST, переиспользует `_parse_reading_payload` — обобщить его под `request.form`, не только JSON-словарь), `/admin/thresholds` (POST, валидация warn<fault, обе неотрицательные, запись через `db.update_threshold`). Довести тесты до зелёного.
6. Обобщить `_parse_reading_payload`: убрать `isinstance(payload, dict)` (не подходит для `request.form`, это `ImmutableMultiDict`), полагаться на try/except при доступе по ключу — работает одинаково для JSON-словаря и form-данных. Прогнать `tests/test_api.py`, чтобы старые 7 тестов не сломались.
7. Прогнать весь `pytest` — зелёный.
8. Ручная проверка: `python app.py`, зайти на `/admin` без логина (редирект), войти с неверным паролем (отказ), войти с верным (доступ), добавить показание вручную и поправить порог — проверить, что изменения видны на `/`. Открыть `sensors.db` через `sqlite3` и показать, что `password_hash` — не открытый пароль.
9. Обновить `harness/PROJECT.md`, написать `harness/stage-4/REPORT.md`, закоммитить (без `.env`) и запушить.

## Альтернативы

- Хранить в `users` только пароль без логина (проверять один пароль без имени пользователя): отвергнуто — задание прямо говорит «страница логина», а не «страница пароля»; с логином+паролем проще писать раздельные тесты на «неверный логин» и «неверный пароль», и это стандартный паттерн, который дешевле объяснить на сдаче.
- Хранить состояние сессии в cookie без `SECRET_KEY` (например, простой orм `if request.cookies.get(...) == "1"`): отвергнуто — незащищённая кука подделывается вручную в браузере; `Flask session` с `SECRET_KEY` подписывает cookie, это и есть механизм из задания («сессия»).
- Отдельная функция валидации для формы порогов, дублирующая логику `_parse_reading_payload`: отвергнуто там, где возможно переиспользование, но пороги — это пары (warn, fault), а не тройка (temp, pressure, vibration) с другим правилом (warn < fault) — общий хелпер тут скорее усложнил бы код, чем упростил, отдельная небольшая функция обоснована.

## Риски

- 🟡 Обобщение `_parse_reading_payload` под `request.form` — единственное изменение, способное сломать уже сданный Этап 3 API. Сразу после правки прогоняю старые 7 тестов `test_api.py`.
- 🟡 `.env` получит новые ключи (`ADMIN_PASSWORD`, `SECRET_KEY`) — после генерации сразу проверяю `git status`, что `.env` по-прежнему игнорируется, до первого коммита этапа.
- 🟢 Новая таблица `users` — не трогает `readings`/`thresholds`, риска для предыдущих этапов нет.
- 🟢 `flash()` — встроенный механизм Flask, новых зависимостей не требует.

## Бюджет

- Файлов: 9 (`db.py`, `.env.example`, `tests/conftest.py`, `tests/test_admin.py`, `app.py`, `harness/PROJECT.md`, `harness/stage-4/REPORT.md`, `DECISIONS.md`, `.gitignore` — если понадобится, но `.env` уже там) — `.env` не коммитится, в счёт не идёт
- Время: ориентировочно 2–2.5 часа моей работы
- Правило: превысил → стоп и сообщаю

## Чек-лист выхода
- [x] шаги конкретны (сделан/не сделан)
- [x] есть отвергнутая альтернатива с содержательной причиной (три штуки)
- [x] красных рисков нет
- [x] бюджет назначен
