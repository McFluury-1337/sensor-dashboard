import hmac
import json
import statistics as st
from datetime import datetime
from functools import wraps

from flask import Flask, flash, get_flashed_messages, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash

import config
import db
import notifications
from preprocessing import normalize, standardize
from state import classify_metric, classify_reading

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
    --pico-background-color: #101214;
    --pico-color: #e7eaee;
    --pico-muted-color: #9aa1ab;
    --pico-muted-border-color: #2b2f35;
    --pico-primary: #2fb0c7;
    --pico-primary-background: #1f8fa3;
    --pico-primary-border: var(--pico-primary-background);
    --pico-primary-underline: rgba(47, 176, 199, 0.5);
    --pico-primary-hover: #58c3d6;
    --pico-primary-hover-background: #2596ab;
    --pico-primary-hover-border: var(--pico-primary-hover-background);
    --pico-primary-focus: rgba(47, 176, 199, 0.375);
    --pico-primary-inverse: #04141a;
    --pico-font-family-sans-serif: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
    --pico-font-family-monospace: "JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", monospace;
    --surface: #1a1d21;
    --surface-2: #23272c;
}

body {
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
    background-size: 32px 32px;
    background-attachment: fixed;
}

h1 {
    font-size: 1.85rem;
    line-height: 1.25;
    font-weight: 700;
    letter-spacing: -0.01em;
}

h2 {
    font-size: 1.15rem;
    line-height: 1.3;
    font-weight: 600;
    padding-left: 0.85rem;
    border-left: 3px solid var(--pico-primary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

article {
    background-color: var(--surface);
    border: 1px solid var(--pico-muted-border-color);
}

td, th {
    font-family: var(--pico-font-family-monospace);
    font-variant-numeric: tabular-nums;
}

th {
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--pico-muted-color);
    font-size: 0.8rem;
    text-transform: uppercase;
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
    background-color: rgba(16, 18, 20, 0.85);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--pico-muted-border-color);
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

.state-reason {
    margin-left: 0.6rem;
    color: var(--pico-muted-color);
    font-size: 0.85rem;
    font-family: var(--pico-font-family-monospace);
}

.table-card {
    background-color: var(--pico-background-color);
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
    background-color: var(--surface-2);
}

.table-card tbody tr:nth-child(even) {
    background-color: rgba(255, 255, 255, 0.025);
}

.table-card tbody tr:hover {
    background-color: rgba(47, 176, 199, 0.08);
}

#recent-table:not(.expanded) tbody tr:nth-child(n+6) {
    display: none;
}

.table-toggle {
    margin-top: 0.75rem;
    width: 100%;
    background: transparent;
    border: 1px solid var(--pico-muted-border-color);
    color: #e7eaee;
}

.table-toggle:hover,
.table-toggle:focus {
    background: var(--surface-2);
    border-color: var(--pico-muted-border-color);
    color: #e7eaee;
}

footer {
    margin-top: 2.5rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--pico-muted-border-color);
}

.gauges-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
}

@media (min-width: 700px) {
    .gauges-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

.gauge-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.5rem;
}

.gauge-label {
    color: var(--pico-muted-color);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.gauge-value {
    font-family: var(--pico-font-family-monospace);
    font-size: 1.3rem;
    font-weight: 600;
}

.gauge-track {
    position: relative;
    height: 10px;
    border-radius: 999px;
}

.gauge-marker {
    position: absolute;
    top: 50%;
    width: 4px;
    height: 22px;
    background: #eef3f7;
    border-radius: 2px;
    transform: translate(-50%, -50%);
    box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.4);
}

.gauge-scale {
    display: flex;
    justify-content: space-between;
    margin-top: 0.4rem;
    font-size: 0.75rem;
    color: var(--pico-muted-color);
    font-family: var(--pico-font-family-monospace);
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
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


def _format_scale(metric, value):
    return f"{value:.0f}" if metric == "temperature" else f"{value:.1f}"


def build_gauges_html(temperature, pressure, vibration, thresholds):
    values = {"temperature": temperature, "pressure": pressure, "vibration": vibration}
    gauges_html = ""
    for metric in ("temperature", "pressure", "vibration"):
        value = values[metric]
        warn, fault = thresholds[metric]
        zone = classify_metric(value, warn, fault)
        color = STATE_COLOR[zone]
        max_scale = max(fault * 1.4, value * 1.05, warn * 1.1)
        warn_pct = min(100.0, warn / max_scale * 100)
        fault_pct = min(100.0, fault / max_scale * 100)
        value_pct = min(100.0, max(0.0, value / max_scale * 100))

        gauges_html += f"""
        <div class="gauge">
            <div class="gauge-head">
                <span class="gauge-label">{METRIC_LABEL[metric]}</span>
                <span class="gauge-value" style="color: {color};">{value:.2f}</span>
            </div>
            <div class="gauge-track" style="background: linear-gradient(to right,
                #3fae59 0%, #3fae59 {warn_pct:.2f}%,
                #d99b2b {warn_pct:.2f}%, #d99b2b {fault_pct:.2f}%,
                #d1483f {fault_pct:.2f}%, #d1483f 100%);">
                <div class="gauge-marker" style="left: {value_pct:.2f}%;"></div>
            </div>
            <div class="gauge-scale">
                <span>0</span><span>{_format_scale(metric, max_scale)}</span>
            </div>
        </div>
        """
    return gauges_html


def build_state_reason(temperature, pressure, vibration, thresholds, current_state):
    if current_state == "норма":
        return ""

    values = {"temperature": temperature, "pressure": pressure, "vibration": vibration}
    parts = []
    for metric in ("temperature", "pressure", "vibration"):
        value = values[metric]
        warn, fault = thresholds[metric]
        zone = classify_metric(value, warn, fault)
        if zone == current_state:
            boundary = fault if current_state == "неисправность" else warn
            parts.append(f"{METRIC_LABEL[metric]} {value:.2f} ≥ {boundary:.2f}")

    return "Причина: " + "; ".join(parts)


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
    gauges_html = build_gauges_html(temperature, pressure, vibration, thresholds)
    stats_rows_html = build_stats_table(all_readings, thresholds)
    state_reason = build_state_reason(temperature, pressure, vibration, thresholds, current_state)
    background = STATE_BACKGROUND[current_state]
    thresholds_json = json.dumps({metric: list(bounds) for metric, bounds in thresholds.items()})

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
            {f'<span class="state-reason">{state_reason}</span>' if state_reason else ''}
        </p>
    </hgroup>

    <article>
        <h2>Показания сейчас</h2>
        <div class="gauges-grid">
            {gauges_html}
        </div>
    </article>

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
                    <thead><tr><th>Состояние</th><th>Температура</th><th>Давление</th><th>Вибрация</th></tr></thead>
                    <tbody>{stats_rows_html}</tbody>
                </table>
            </div>
        </article>

        <article style="min-width: 0;">
            <h2>Последние {len(recent)} показаний</h2>
            <div class="table-card" id="recent-table">
                <table>
                    <thead><tr><th>Время</th><th>Температура</th><th>Давление</th><th>Вибрация</th></tr></thead>
                    <tbody>{recent_rows_html}</tbody>
                </table>
            </div>
            {f'<button type="button" class="table-toggle" id="recent-toggle">Показать все {len(recent)}</button>' if len(recent) > 5 else ''}
        </article>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <script>
        const chartData = {json.dumps(chart_data)};
        const thresholds = {thresholds_json};
        const metricColors = {{ temperature: "#d1483f", pressure: "#2fb0c7", vibration: "#d99b2b" }};

        function buildThresholdDatasets() {{
            const datasets = [];
            for (const metric of ["temperature", "pressure", "vibration"]) {{
                const [warn, fault] = thresholds[metric];
                const color = metricColors[metric];
                datasets.push(
                    {{ label: metric + "-warn", data: chartData.labels.map(() => warn), borderColor: color, borderDash: [6, 4], borderWidth: 1, pointRadius: 0, fill: false, tension: 0, order: 10 }},
                    {{ label: metric + "-fault", data: chartData.labels.map(() => fault), borderColor: color, borderDash: [2, 3], borderWidth: 1, pointRadius: 0, fill: false, tension: 0, order: 10 }}
                );
            }}
            return datasets;
        }}

        Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, sans-serif";
        Chart.defaults.font.size = 12;

        const ctx = document.getElementById("chart");
        const chart = new Chart(ctx, {{
            type: "line",
            data: {{
                labels: chartData.labels,
                datasets: [
                    {{ label: "Температура", data: chartData.raw.temperature, borderColor: "#d1483f", backgroundColor: "rgba(209, 72, 63, 0.08)", pointBackgroundColor: "#d1483f", pointBorderColor: "#101214", pointHoverBackgroundColor: "#d1483f", pointHoverBorderColor: "#e7eaee", fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 }},
                    {{ label: "Давление", data: chartData.raw.pressure, borderColor: "#2fb0c7", backgroundColor: "rgba(47, 176, 199, 0.12)", pointBackgroundColor: "#2fb0c7", pointBorderColor: "#101214", pointHoverBackgroundColor: "#2fb0c7", pointHoverBorderColor: "#e7eaee", fill: false, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 }},
                    {{ label: "Вибрация", data: chartData.raw.vibration, borderColor: "#d99b2b", backgroundColor: "rgba(217, 155, 43, 0.12)", pointBackgroundColor: "#d99b2b", pointBorderColor: "#101214", pointHoverBackgroundColor: "#d99b2b", pointHoverBorderColor: "#e7eaee", fill: false, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 }},
                    ...buildThresholdDatasets()
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{ mode: "index", intersect: false }},
                plugins: {{
                    legend: {{
                        labels: {{
                            color: "#e7eaee",
                            usePointStyle: true,
                            filter: (item) => !item.text.endsWith("-warn") && !item.text.endsWith("-fault")
                        }}
                    }},
                    tooltip: {{
                        usePointStyle: true,
                        backgroundColor: "#1a1d21",
                        borderColor: "#2b2f35",
                        borderWidth: 1,
                        titleColor: "#e7eaee",
                        bodyColor: "#e7eaee",
                        padding: 10,
                        boxPadding: 4,
                        filter: (item) => !item.dataset.label.endsWith("-warn") && !item.dataset.label.endsWith("-fault")
                    }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: "#9aa1ab" }}, grid: {{ color: "rgba(255, 255, 255, 0.04)" }} }},
                    y: {{ ticks: {{ color: "#9aa1ab" }}, grid: {{ color: "rgba(255, 255, 255, 0.04)" }} }}
                }}
            }}
        }});

        const recentToggle = document.getElementById("recent-toggle");
        if (recentToggle) {{
            recentToggle.addEventListener("click", function () {{
                const table = document.getElementById("recent-table");
                const expanded = table.classList.toggle("expanded");
                recentToggle.textContent = expanded ? "Свернуть" : "Показать все {len(recent)}";
            }});
        }}

        document.getElementById("mode").addEventListener("change", function (event) {{
            const mode = event.target.value;
            chart.data.datasets[0].data = chartData[mode].temperature;
            chart.data.datasets[1].data = chartData[mode].pressure;
            chart.data.datasets[2].data = chartData[mode].vibration;
            for (let i = 3; i < chart.data.datasets.length; i++) {{
                chart.data.datasets[i].hidden = mode !== "raw";
            }}
            chart.update();
        }});
    </script>
    """

    return _page("Пульт мониторинга", body)


def _valid_api_key():
    provided = request.headers.get("X-API-Key", "")
    return hmac.compare_digest(provided, API_KEY or "")


def _record_reading(temperature, pressure, vibration):
    thresholds = db.get_thresholds()
    previous = db.get_latest_readings(1)
    previous_state = (
        classify_reading(previous[0][1], previous[0][2], previous[0][3], thresholds)
        if previous else None
    )

    timestamp = datetime.now().isoformat()
    db.insert_reading(timestamp, temperature, pressure, vibration)

    current_state = classify_reading(temperature, pressure, vibration, thresholds)
    if notifications.is_new_fault(previous_state, current_state):
        reason = build_state_reason(temperature, pressure, vibration, thresholds, current_state)
        notifications.send_telegram_alert(f"Пульт мониторинга: неисправность. {reason}")

    return timestamp


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
    timestamp = _record_reading(temperature, pressure, vibration)

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
                        <thead><tr><th>Метрика</th><th>Предупреждение с</th><th>Неисправность с</th></tr></thead>
                        <tbody>{threshold_rows_html}</tbody>
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
    _record_reading(temperature, pressure, vibration)
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
