import random
from datetime import datetime

import db

STATES = {
    "normal": {
        "temperature": (70, 3),
        "pressure": (5.0, 0.3),
        "vibration": (0.5, 0.10),
    },
    "warning": {
        "temperature": (78, 4),
        "pressure": (5.8, 0.4),
        "vibration": (0.9, 0.15),
    },
    "fault": {
        "temperature": (88, 5),
        "pressure": (6.7, 0.5),
        "vibration": (1.5, 0.25),
    },
}


def generate_reading():
    state = random.choice(list(STATES.keys()))
    params = STATES[state]

    temperature = random.normalvariate(*params["temperature"])
    pressure = random.normalvariate(*params["pressure"])
    vibration = random.normalvariate(*params["vibration"])

    return temperature, pressure, vibration


def main():
    db.init_db()

    temperature, pressure, vibration = generate_reading()
    timestamp = datetime.now().isoformat()

    db.insert_reading(timestamp, temperature, pressure, vibration)
    print(f"{timestamp} temp={temperature:.2f} pressure={pressure:.2f} vibration={vibration:.2f}")


if __name__ == "__main__":
    main()
