import hmac
import json
import statistics as st
from datetime import datetime

from flask import Flask, jsonify, request

import config
import db
from preprocessing import normalize, standardize
from state import classify_reading

app = Flask(__name__)

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
    if not isinstance(payload, dict):
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


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
