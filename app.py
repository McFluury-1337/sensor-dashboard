import hmac
import json
import statistics as st
from datetime import datetime
from functools import wraps

from flask import Flask, flash, get_flashed_messages, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash

import config
import db
from preprocessing import normalize, standardize
from state import classify_reading

app = Flask(__name__)
app.secret_key = config.get("SECRET_KEY")

API_KEY = config.get("API_KEY")

STATE_COLOR = {
    "норма": "#3fae59",
    "предупреждение": "#d99b2b",
    "неисправность": "#d1483f",
}

STATE_BACKGROUND = {
    "норма": "rgba(63, 174, 89, 0.14)",
    "предупреждение": "rgba(217, 155, 43, 0.14)",
    "неисправность": "rgba(209, 72, 63, 0.14)",
}

METRIC_LABEL = {
    "temperature": "Температура",
    "pressure": "Давление",
    "vibration": "Вибрация",
}

PAGE_STYLES = """
:root[data-theme="dark"] {
    --pico-background-color: #12181f;
    --pico-color: #dfe6ec;
    --pico-muted-color: #8a95a3;
    --pico-muted-border-color: #232d38;
    --pico-primary: #2fb0c7;
    --pico-primary-background: #1f8fa3;
    --pico-primary-border: var(--pico-primary-background);
    --pico-primary-underline: rgba(47, 176, 199, 0.5);
    --pico-primary-hover: #58c3d6;
    --pico-primary-hover-background: #2596ab;
    --pico-primary-hover-border: var(--pico-primary-hover-background);
    --pico-primary-focus: rgba(47, 176, 199, 0.375);
    --pico-primary-inverse: #04141a;
}

td {
    font-family: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", monospace;
    font-variant-numeric: tabular-nums;
}

@media (max-width: 480px) {
    td, th {
        padding: 0.4rem 0.5rem;
        font-size: 0.8rem;
    }
}

.tables-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
}

@media (min-width: 900px) {
    .tables-grid {
        grid-template-columns: 1fr 1fr;
    }
}

nav {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: rgba(18, 24, 31, 0.85);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--pico-muted-border-color);
}

h2 {
    padding-left: 0.85rem;
    border-left: 3px solid var(--pico-primary);
}

.state-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.9rem;
    border-radius: 999px;
    border: 1px solid currentColor;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.state-badge .dot {
    width: 0.5em;
    height: 0.5em;
    border-radius: 50%;
    background: currentColor;
    display: inline-block;
    flex: none;
}

.table-card {
    background-color: #1b232c;
    border: 1px solid var(--pico-muted-border-color);
    border-radius: 0.5rem;
    overflow: auto;
}

.table-card table {
    margin-bottom: 0;
}

.table-card thead th {
    position: sticky;
    top: 0;
    background-color: #202a35;
}

.table-card tbody tr:nth-child(even) {
    background-color: rgba(255, 255, 255, 0.025);
}

.table-card tbody tr:hover {
    background-color: rgba(47, 176, 199, 0.08);
}

footer {
    margin-top: 2.5rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--pico-muted-border-color);
}
"""


def _nav_html():
    if session.get("logged_in"):
        links = [(url_for("admin"), "Админка"), (url_for("logout"), "Выйти")]
    else:
        links = [(url_for("login"), "Войти")]

    items_html = "".join(f'<li><a href="{href}">{label}</a></li>' for href, label in links)

    return f"""
    <nav>
        <ul><li><a href="{url_for('index')}"><strong>Пульт мониторинга</strong></a></li></ul>
        <ul>{items_html}</ul>
    </nav>
    """


def _flashed_messages_html():
    return "".join(f"<p>{message}</p>" for message in get_flashed_messages())


def _page(title, body_html):
    return f"""<!doctype html>
<html lang="ru" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.fluid.classless.min.css">
<style>{PAGE_STYLES}</style>
</head>
<body>
<header>
{_nav_html()}
</header>
<main>
{body_html}
</main>
<footer>
<p><small>Пет-проект «Пульт мониторинга технической системы»</small></p>
</footer>
</body>
</html>"""


def build_chart_datasets(readings):
    # readings приходят новые-сверху (как из db.get_latest_readings) — для графика
    # разворачиваем в хронологический порядок, слева направо
    chronological = list(reversed(readings))
    labels = [timestamp.split("T")[-1] for timestamp, _, _, _ in chronological]
    temperature = [t for _, t, _, _ in chronological]
    pressure = [p for _, _, p, _ in chronological]
    vibration = [v for _, _, _, v in chronological]

    return {
        "labels": labels,
        "raw": {"temperature": temperature, "pressure": pressure, "vibration": vibration},
        "normalized": {
            "temperature": normalize(temperature),
            "pressure": normalize(pressure),
            "vibration": normalize(vibration),
        },
        "standardized": {
            "temperature": standardize(temperature),
            "pressure": standardize(pressure),
            "vibration": standardize(vibration),
        },
    }


def build_stats_table(all_readings, thresholds):
    by_state = {"норма": {"temperature": [], "pressure": [], "vibration": []},
                "предупреждение": {"temperature": [], "pressure": [], "vibration": []},
                "неисправность": {"temperature": [], "pressure": [], "vibration": []}}

    for _, temperature, pressure, vibration in all_readings:
        state = classify_reading(temperature, pressure, vibration, thresholds)
        by_state[state]["temperature"].append(temperature)
        by_state[state]["pressure"].append(pressure)
        by_state[state]["vibration"].append(vibration)

    rows_html = ""
    for state in ("норма", "предупреждение", "неисправность"):
        cells = []
        for metric in ("temperature", "pressure", "vibration"):
            values = by_state[state][metric]
            if values:
                cells.append(f"{st.mean(values):.2f} ± {st.pstdev(values):.2f}")
            else:
                cells.append("—")
        rows_html += f"<tr><td>{state}</td><td>{cells[0]}</td><td>{cells[1]}</td><td>{cells[2]}</td></tr>"

    return rows_html


@app.route("/")
def index():
    thresholds = db.get_thresholds()
    latest = db.get_latest_readings(1)
    recent = db.get_latest_readings(50)
    all_readings = db.get_all_readings()

    if not latest:
        return _page(
            "Пульт мониторинга",
            "<p>Нет данных. Запустите simulator.py, чтобы получить первые показания.</p>",
        )

    _, temperature, pressure, vibration = latest[0]
    current_state = classify_reading(temperature, pressure, vibration, thresholds)
    color = STATE_COLOR[current_state]

    chart_data = build_chart_datasets(recent)
    stats_rows_html = build_stats_table(all_readings, thresholds)
    background = STATE_BACKGROUND[current_state]

    recent_rows_html = "".join(
        f"<tr><td>{timestamp.split('.')[0].replace('T', ' ')}</td>"
        f"<td>{temperature:.2f}</td><td>{pressure:.2f}</td><td>{vibration:.2f}</td></tr>"
        for timestamp, temperature, pressure, vibration in recent
    )

    body = f"""
    <hgroup>
        <h1>Пульт мониторинга технической системы</h1>
        <p>Текущее состояние:
            <strong id="current-state" class="state-badge" style="color: {color}; background: {background};">
                <span class="dot"></span>{current_state}
            </strong>
        </p>
    </hgroup>

    <article>
        <h2>График последних {len(recent)} показаний</h2>
        <label for="mode">
            Вид данных
            <select id="mode">
                <option value="raw">сырые</option>
                <option value="normalized">нормализованные</option>
                <option value="standardized">стандартизированные</option>
            </select>
        </label>
        <div style="height: 320px;">
            <canvas id="chart"></canvas>
        </div>
    </article>

    <div class="tables-grid">
        <article style="min-width: 0;">
            <h2>Среднее ± σ по состояниям</h2>
            <div class="table-card">
                <table>
                    <tr><th>Состояние</th><th>Температура</th><th>Давление</th><th>Вибрация</th></tr>
                    {stats_rows_html}
                </table>
            </div>
        </article>

        <article style="min-width: 0;">
            <h2>Последние {len(recent)} показаний</h2>
            <div class="table-card">
                <table>
                    <tr><th>Время</th><th>Температура</th><th>Давление</th><th>Вибрация</th></tr>
                    {recent_rows_html}
                </table>
            </div>
        </article>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <script>
        const chartData = {json.dumps(chart_data)};

        const ctx = document.getElementById("chart");
        const chart = new Chart(ctx, {{
            type: "line",
            data: {{
                labels: chartData.labels,
                datasets: [
                    {{ label: "Температура", data: chartData.raw.temperature, borderColor: "#d1483f", backgroundColor: "rgba(209, 72, 63, 0.08)", fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 }},
                    {{ label: "Давление", data: chartData.raw.pressure, borderColor: "#2fb0c7", backgroundColor: "rgba(47, 176, 199, 0.12)", fill: false, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 }},
                    {{ label: "Вибрация", data: chartData.raw.vibration, borderColor: "#d99b2b", backgroundColor: "rgba(217, 155, 43, 0.12)", fill: false, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{ mode: "index", intersect: false }},
                plugins: {{ legend: {{ labels: {{ color: "#dfe6ec" }} }} }},
                scales: {{
                    x: {{ ticks: {{ color: "#8a95a3" }}, grid: {{ color: "rgba(255, 255, 255, 0.05)" }} }},
                    y: {{ ticks: {{ color: "#8a95a3" }}, grid: {{ color: "rgba(255, 255, 255, 0.05)" }} }}
                }}
            }}
        }});

        document.getElementById("mode").addEventListener("change", function (event) {{
            const mode = event.target.value;
            chart.data.datasets[0].data = chartData[mode].temperature;
            chart.data.datasets[1].data = chartData[mode].pressure;
            chart.data.datasets[2].data = chartData[mode].vibration;
            chart.update();
        }});
    </script>
    """

    return _page("Пульт мониторинга", body)


def _valid_api_key():
    provided = request.headers.get("X-API-Key", "")
    return hmac.compare_digest(provided, API_KEY or "")


def _parse_reading_payload(payload):
    if payload is None:
        return None
    try:
        temperature = float(payload["temperature"])
        pressure = float(payload["pressure"])
        vibration = float(payload["vibration"])
    except (KeyError, TypeError, ValueError):
        return None
    if temperature < 0 or pressure < 0 or vibration < 0:
        return None
    return temperature, pressure, vibration


@app.route("/api/readings", methods=["POST"])
def create_reading():
    if not _valid_api_key():
        return jsonify({"error": "unauthorized"}), 401

    parsed = _parse_reading_payload(request.get_json(silent=True))
    if parsed is None:
        return jsonify({"error": "temperature, pressure and vibration must be non-negative numbers"}), 400

    temperature, pressure, vibration = parsed
    timestamp = datetime.now().isoformat()
    db.insert_reading(timestamp, temperature, pressure, vibration)

    return jsonify({
        "timestamp": timestamp,
        "temperature": temperature,
        "pressure": pressure,
        "vibration": vibration,
    }), 201


@app.route("/api/readings", methods=["GET"])
def list_readings():
    limit = request.args.get("limit", default=50, type=int)
    if not limit or limit <= 0:
        limit = 50

    rows = db.get_latest_readings(limit)
    return jsonify([
        {"timestamp": timestamp, "temperature": temperature, "pressure": pressure, "vibration": vibration}
        for timestamp, temperature, pressure, vibration in rows
    ])


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def _parse_thresholds_payload(form):
    thresholds = {}
    for metric in ("temperature", "pressure", "vibration"):
        try:
            warn = float(form[f"{metric}_warn"])
            fault = float(form[f"{metric}_fault"])
        except (KeyError, TypeError, ValueError):
            return None
        if warn < 0 or fault < 0 or warn >= fault:
            return None
        thresholds[metric] = (warn, fault)
    return thresholds


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        password_hash = db.get_user(username)
        if password_hash and check_password_hash(password_hash, password):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("admin"))
        flash("Неверный логин или пароль")

    messages_html = _flashed_messages_html()

    body = f"""
    <article style="max-width: 24rem; margin-inline: auto;">
        <h1>Вход</h1>
        {messages_html}
        <form method="post">
            <label for="username">
                Логин
                <input id="username" name="username" autocomplete="username">
            </label>
            <label for="password">
                Пароль
                <input id="password" name="password" type="password" autocomplete="current-password">
            </label>
            <button type="submit">Войти</button>
        </form>
    </article>
    """

    return _page("Вход", body)


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def admin():
    thresholds = db.get_thresholds()
    messages_html = _flashed_messages_html()

    threshold_rows_html = "".join(
        f"""<tr>
            <td>{METRIC_LABEL[metric]}</td>
            <td><input name="{metric}_warn" value="{warn}"></td>
            <td><input name="{metric}_fault" value="{fault}"></td>
        </tr>"""
        for metric, (warn, fault) in thresholds.items()
    )

    body = f"""
    <h1>Админка</h1>
    {messages_html}

    <div class="tables-grid">
        <article style="min-width: 0;">
            <h2>Ввести показание вручную</h2>
            <form method="post" action="{url_for('admin_create_reading')}">
                <label for="temperature">
                    Температура
                    <input id="temperature" name="temperature">
                </label>
                <label for="pressure">
                    Давление
                    <input id="pressure" name="pressure">
                </label>
                <label for="vibration">
                    Вибрация
                    <input id="vibration" name="vibration">
                </label>
                <button type="submit">Добавить</button>
            </form>
        </article>

        <article style="min-width: 0;">
            <h2>Пороги состояний</h2>
            <form method="post" action="{url_for('admin_update_thresholds')}">
                <div class="table-card">
                    <table>
                        <tr><th>Метрика</th><th>Предупреждение с</th><th>Неисправность с</th></tr>
                        {threshold_rows_html}
                    </table>
                </div>
                <button type="submit">Сохранить пороги</button>
            </form>
        </article>
    </div>
    """

    return _page("Админка", body)


@app.route("/admin/readings", methods=["POST"])
@login_required
def admin_create_reading():
    parsed = _parse_reading_payload(request.form)
    if parsed is None:
        flash("Показание не сохранено: значения должны быть неотрицательными числами")
        return redirect(url_for("admin"))

    temperature, pressure, vibration = parsed
    timestamp = datetime.now().isoformat()
    db.insert_reading(timestamp, temperature, pressure, vibration)
    flash("Показание добавлено")
    return redirect(url_for("admin"))


@app.route("/admin/thresholds", methods=["POST"])
@login_required
def admin_update_thresholds():
    parsed = _parse_thresholds_payload(request.form)
    if parsed is None:
        flash("Пороги не сохранены: нужны неотрицательные числа, нижняя граница меньше верхней")
        return redirect(url_for("admin"))

    for metric, (warn, fault) in parsed.items():
        db.update_threshold(metric, warn, fault)
    flash("Пороги обновлены")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
