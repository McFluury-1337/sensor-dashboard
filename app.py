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
    "норма": "green",
    "предупреждение": "orange",
    "неисправность": "red",
}


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
        return "<p>Нет данных. Запустите simulator.py, чтобы получить первые показания.</p>"

    _, temperature, pressure, vibration = latest[0]
    current_state = classify_reading(temperature, pressure, vibration, thresholds)
    color = STATE_COLOR[current_state]

    chart_data = build_chart_datasets(recent)
    stats_rows_html = build_stats_table(all_readings, thresholds)

    recent_rows_html = "".join(
        f"<tr><td>{timestamp}</td><td>{t:.2f}</td><td>{p:.2f}</td><td>{v:.2f}</td></tr>"
        for timestamp, t, p, v in recent
    )

    return f"""
    <h1>Пульт мониторинга технической системы</h1>

    <p>Текущее состояние: <strong style="color: {color};">{current_state}</strong></p>

    <h2>График последних {len(recent)} показаний</h2>
    <label for="mode">Вид данных:</label>
    <select id="mode">
        <option value="raw">сырые</option>
        <option value="normalized">нормализованные</option>
        <option value="standardized">стандартизированные</option>
    </select>
    <canvas id="chart" width="800" height="300"></canvas>

    <h2>Среднее ± σ по состояниям</h2>
    <table border="1">
        <tr><th>Состояние</th><th>Температура</th><th>Давление</th><th>Вибрация</th></tr>
        {stats_rows_html}
    </table>

    <h2>Последние {len(recent)} показаний</h2>
    <table border="1">
        <tr><th>Время</th><th>Температура</th><th>Давление</th><th>Вибрация</th></tr>
        {recent_rows_html}
    </table>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <script>
        const chartData = {json.dumps(chart_data)};

        const ctx = document.getElementById("chart");
        const chart = new Chart(ctx, {{
            type: "line",
            data: {{
                labels: chartData.labels,
                datasets: [
                    {{ label: "Температура", data: chartData.raw.temperature, borderColor: "red", fill: false }},
                    {{ label: "Давление", data: chartData.raw.pressure, borderColor: "blue", fill: false }},
                    {{ label: "Вибрация", data: chartData.raw.vibration, borderColor: "green", fill: false }}
                ]
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
        {"timestamp": timestamp, "temperature": t, "pressure": p, "vibration": v}
        for timestamp, t, p, v in rows
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

    messages_html = "".join(f"<p>{message}</p>" for message in get_flashed_messages())

    return f"""
    <h1>Вход</h1>
    {messages_html}
    <form method="post">
        <label>Логин: <input name="username"></label><br>
        <label>Пароль: <input name="password" type="password"></label><br>
        <button type="submit">Войти</button>
    </form>
    """


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def admin():
    thresholds = db.get_thresholds()
    messages_html = "".join(f"<p>{message}</p>" for message in get_flashed_messages())

    threshold_rows_html = "".join(
        f"""
        <tr>
            <td>{metric}</td>
            <td><input name="{metric}_warn" value="{warn}"></td>
            <td><input name="{metric}_fault" value="{fault}"></td>
        </tr>
        """
        for metric, (warn, fault) in thresholds.items()
    )

    return f"""
    <h1>Админка</h1>
    <p><a href="{url_for('logout')}">Выйти</a> · <a href="{url_for('index')}">На главную</a></p>
    {messages_html}

    <h2>Ввести показание вручную</h2>
    <form method="post" action="{url_for('admin_create_reading')}">
        <label>Температура: <input name="temperature"></label><br>
        <label>Давление: <input name="pressure"></label><br>
        <label>Вибрация: <input name="vibration"></label><br>
        <button type="submit">Добавить</button>
    </form>

    <h2>Пороги состояний</h2>
    <form method="post" action="{url_for('admin_update_thresholds')}">
        <table border="1">
            <tr><th>Метрика</th><th>Предупреждение с</th><th>Неисправность с</th></tr>
            {threshold_rows_html}
        </table>
        <button type="submit">Сохранить пороги</button>
    </form>
    """


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
