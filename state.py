SEVERITY = ["норма", "предупреждение", "неисправность"]


def classify_metric(value, warn_boundary, fault_boundary):
    if value < warn_boundary:
        return "норма"
    if value < fault_boundary:
        return "предупреждение"
    return "неисправность"


def classify_reading(temperature, pressure, vibration, thresholds):
    states = [
        classify_metric(temperature, *thresholds["temperature"]),
        classify_metric(pressure, *thresholds["pressure"]),
        classify_metric(vibration, *thresholds["vibration"]),
    ]
    return max(states, key=SEVERITY.index)
