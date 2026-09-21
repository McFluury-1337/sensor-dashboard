def normalize(values):
    low = min(values)
    high = max(values)
    span = high - low
    if span == 0:
        return [0 for _ in values]
    return [(v - low) / span for v in values]


def standardize(values):
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    sd = variance ** 0.5
    if sd == 0:
        return [0 for _ in values]
    return [(v - mean) / sd for v in values]
