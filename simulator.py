import json
import random
import urllib.error
import urllib.request

import config

API_URL = config.get("API_URL", "http://127.0.0.1:5000")
API_KEY = config.get("API_KEY")

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


def send_reading(temperature, pressure, vibration):
    payload = json.dumps({
        "temperature": temperature,
        "pressure": pressure,
        "vibration": vibration,
    }).encode()

    request = urllib.request.Request(
        f"{API_URL}/api/readings",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY or ""},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read())


def main():
    temperature, pressure, vibration = generate_reading()
    try:
        status, body = send_reading(temperature, pressure, vibration)
        print(status, body)
    except urllib.error.HTTPError as error:
        print(error.code, error.read().decode())


if __name__ == "__main__":
    main()
