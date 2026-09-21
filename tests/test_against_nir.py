import csv
import statistics as st

FIXTURE_PATH = "tests/fixtures/data_raw.csv"

# Таблица 1 из НИР_Зеленин_v5.docx (собственная научно-исследовательская работа автора
# проекта, источник исходного генератора показаний в simulator.py), раздел 3.2 —
# среднее ± стандартное отклонение по состояниям на исходных 300 записях
TABLE_1 = {
    "норма": {"temperature": (69.69, 2.72), "pressure": (5.01, 0.29), "vibration": (0.51, 0.11)},
    "предупреждение": {"temperature": (78.43, 3.54), "pressure": (5.78, 0.43), "vibration": (0.88, 0.14)},
    "неисправность": {"temperature": (88.12, 5.34), "pressure": (6.70, 0.49), "vibration": (1.56, 0.23)},
}


def load_fixture_rows():
    with open(FIXTURE_PATH) as f:
        return list(csv.DictReader(f))


def test_fixture_has_300_records_from_nir():
    rows = load_fixture_rows()
    assert len(rows) == 300


def test_mean_and_std_by_true_state_match_table_1():
    rows = load_fixture_rows()
    by_state = {state: {"temperature": [], "pressure": [], "vibration": []} for state in TABLE_1}

    for row in rows:
        state = row["state"]
        by_state[state]["temperature"].append(float(row["temperature"]))
        by_state[state]["pressure"].append(float(row["pressure"]))
        by_state[state]["vibration"].append(float(row["vibration"]))

    for state, metrics in TABLE_1.items():
        for metric, (ref_mean, ref_sd) in metrics.items():
            values = by_state[state][metric]
            mean = st.mean(values)
            sd = st.pstdev(values)
            assert abs(mean - ref_mean) < 0.1, f"{state}/{metric}: среднее {mean:.2f} vs Таблица 1 {ref_mean}"
            assert abs(sd - ref_sd) < 0.1, f"{state}/{metric}: σ {sd:.2f} vs Таблица 1 {ref_sd}"
