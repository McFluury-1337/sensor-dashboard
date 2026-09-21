import os

ENV_PATH = ".env"


def load_env_file(path=ENV_PATH):
    values = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return values


_file_values = load_env_file()


def get(key, default=None):
    return os.environ.get(key, _file_values.get(key, default))
