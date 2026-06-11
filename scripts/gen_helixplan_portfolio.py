# Generates realistic quarterly net-sales history for the HelixPlan demo portfolio.
# Six products with different life cycles: growth, launch ramp, post-LOE decline,
# seasonal, mature cash cow, growing biologic. Deterministic (seeded) so the
# numbers are stable across runs. Output: a JS PRODUCTS array to paste into
# helixplan.html.
import json, math, random

random.seed(42)

def series(start_year, quarters, base, qtr_growth, seasonality, noise_pct,
           shocks=None, decay_from=None, decay_rate=0.0):
    """Build a quarterly series: trend * seasonality * noise, with optional
    one-off shocks {index: multiplier} and exponential decay from an index
    (post-LOE erosion already inside history)."""
    out = []
    level = base
    for i in range(quarters):
        level_i = base * ((1 + qtr_growth) ** i)
        if decay_from is not None and i >= decay_from:
            level_i *= math.exp(-decay_rate * (i - decay_from + 1))
        v = level_i * seasonality[i % 4]
        v *= 1 + random.uniform(-noise_pct, noise_pct)
        if shocks and i in shocks:
            v *= shocks[i]
        out.append(round(v, 1))
    return out

products = [
    {
        "id": "FLDX", "name": "Felodexa® 40 mg", "molecule": "felodastat · ATC C10AX",
        "segment": "Cardiometabolic · Retail + Hospital", "startYear": 2022,
        "loe": [2029, 2], "ero": 65, "vol": 8,
        "data": series(2022, 16, 38.0, 0.032, [0.97, 1.00, 0.99, 1.10], 0.015),
    },
    {
        "id": "ORV", "name": "Orvantis® 150 mg", "molecule": "orvatinib · ATC L01EX",
        "segment": "Oncology · Hospital · launched 2023", "startYear": 2023,
        "loe": [2036, 1], "ero": 50, "vol": 15,
        # steep launch ramp, growth decaying from 22%/qtr toward ~2%/qtr
        "data": [round(4.2 * math.prod(1 + 0.22 * (0.80 ** k) for k in range(i))
                       * [0.96, 1.0, 1.01, 1.05][i % 4]
                       * (1 + random.uniform(-0.03, 0.03)), 1) for i in range(12)],
    },
    {
        "id": "CRD", "name": "Cardiflex® 10 mg", "molecule": "cardisartan · ATC C09CA",
        "segment": "Cardiovascular · lost exclusivity 2023", "startYear": 2021,
        "loe": [2023, 2], "ero": 70, "vol": 0,
        # healthy until 2023Q2 (index 9), then generic erosion inside history
        "data": series(2021, 20, 78.0, 0.004, [0.99, 1.00, 0.98, 1.06], 0.02,
                       decay_from=9, decay_rate=0.11),
    },
    {
        "id": "RSP", "name": "Respivax®", "molecule": "tetravalent vaccine · ATC J07BB",
        "segment": "Vaccines · strongly seasonal", "startYear": 2021,
        "loe": [2033, 1], "ero": 40, "vol": 0,
        # heavy Q4/Q1 season, weak summers, slow growth, one bad season 2022/23
        "data": series(2021, 20, 21.0, 0.014, [1.22, 0.74, 0.70, 1.34], 0.05,
                       shocks={7: 0.82, 8: 0.85}),
    },
    {
        "id": "GST", "name": "Gastrenol® 20 mg", "molecule": "gastroprazol · ATC A02BC",
        "segment": "Gastro · mature cash cow", "startYear": 2021,
        "loe": [2028, 1], "ero": 75, "vol": 0,
        "data": series(2021, 20, 54.0, 0.005, [0.99, 1.01, 0.99, 1.04], 0.012),
    },
    {
        "id": "IMM", "name": "Immunara® SC", "molecule": "imelizumab · ATC L04AB",
        "segment": "Immunology · biologic", "startYear": 2021,
        "loe": [2030, 3], "ero": 35, "vol": 5,
        "data": series(2021, 20, 29.0, 0.024, [0.98, 1.00, 1.00, 1.06], 0.018),
    },
]

print("const PRODUCTS=" + json.dumps(products, ensure_ascii=False, separators=(",", ":")) + ";")
