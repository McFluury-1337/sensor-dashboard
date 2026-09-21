from flask import Flask

import db

app = Flask(__name__)


@app.route("/")
def index():
    readings = db.get_latest_readings(50)

    rows_html = "".join(
        f"<tr><td>{timestamp}</td><td>{temperature:.2f}</td><td>{pressure:.2f}</td><td>{vibration:.2f}</td></tr>"
        for timestamp, temperature, pressure, vibration in readings
    )

    return f"""
    <table border="1">
        <tr>
            <th>Время</th>
            <th>Температура</th>
            <th>Давление</th>
            <th>Вибрация</th>
        </tr>
        {rows_html}
    </table>
    """


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
