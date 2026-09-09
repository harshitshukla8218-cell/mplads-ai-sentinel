"""
generate_sample_data.py -- see MVP version for full comments.
Generates realistic synthetic MPLADS data with 50 labelled planted anomalies,
so the system works end-to-end before real government data is loaded.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

N_PROJECTS = 600

STATES_DISTRICTS = [
    ("Uttarakhand", "Nainital"), ("Uttarakhand", "Udham Singh Nagar"),
    ("Uttar Pradesh", "Lucknow"), ("Uttar Pradesh", "Kanpur"),
    ("Maharashtra", "Pune"), ("Maharashtra", "Nagpur"),
    ("Rajasthan", "Jaipur"), ("Rajasthan", "Jodhpur"),
    ("Tamil Nadu", "Chennai"), ("Tamil Nadu", "Coimbatore"),
    ("West Bengal", "Kolkata"), ("West Bengal", "Howrah"),
]

SECTORS = {
    "Drinking Water": (500000, 1500000, ["Installation of hand pump", "Sinking of tubewell",
                                          "Construction of overhead water tank"]),
    "Roads": (800000, 3000000, ["Construction of concrete road", "Repair of village road",
                                 "Construction of culvert"]),
    "Education": (300000, 1200000, ["Construction of classroom", "Repair of school building",
                                     "Construction of boundary wall for school"]),
    "Health": (400000, 2000000, ["Construction of community health sub-centre",
                                  "Provision of medical equipment for PHC"]),
    "Community Assets": (200000, 900000, ["Construction of community hall",
                                           "Construction of cremation ground shed"]),
    "Sanitation": (150000, 700000, ["Construction of public toilet complex",
                                     "Installation of solid waste management unit"]),
}

MP_NAMES = ["A. Sharma", "R. Verma", "S. Iyer", "M. Khan", "P. Reddy", "N. Singh",
            "K. Das", "T. Nair", "V. Patel", "J. Rao"]

AGENCIES = ["Block Development Office", "Public Works Department", "Zila Parishad",
            "Municipal Corporation", "Rural Engineering Services"]

STATUS_OPTIONS = ["Completed", "In Progress", "Not Started"]


def random_date(start_year=2022, end_year=2024):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def make_row(work_id):
    state, district = random.choice(STATES_DISTRICTS)
    sector = random.choice(list(SECTORS.keys()))
    low, high, descriptions = SECTORS[sector]
    base_desc = random.choice(descriptions)

    approval_date = random_date(2022, 2023)
    expected_days = random.randint(120, 270)
    expected_completion = approval_date + timedelta(days=expected_days)

    sanction_amount = int(np.random.normal((low + high) / 2, (high - low) / 6))
    sanction_amount = max(sanction_amount, int(low * 0.8))

    status = random.choices(STATUS_OPTIONS, weights=[0.5, 0.35, 0.15])[0]
    mp_name = random.choice(MP_NAMES)
    agency = random.choice(AGENCIES)

    if status == "Completed":
        expenditure_ratio = np.random.uniform(0.92, 1.0)
        physical_progress = 100
        actual_completion = expected_completion + timedelta(days=random.randint(-20, 30))
    elif status == "In Progress":
        expenditure_ratio = np.random.uniform(0.3, 0.85)
        physical_progress = int(expenditure_ratio * 100 * np.random.uniform(0.8, 1.05))
        physical_progress = min(physical_progress, 95)
        actual_completion = None
    else:
        expenditure_ratio = np.random.uniform(0.0, 0.15)
        physical_progress = 0
        actual_completion = None

    expenditure = int(sanction_amount * expenditure_ratio)

    lat_base = {"Uttarakhand": 29.4, "Uttar Pradesh": 26.8, "Maharashtra": 19.7,
                "Rajasthan": 26.9, "Tamil Nadu": 11.0, "West Bengal": 22.5}[state]
    lon_base = {"Uttarakhand": 79.5, "Uttar Pradesh": 80.9, "Maharashtra": 75.3,
                "Rajasthan": 73.8, "Tamil Nadu": 78.6, "West Bengal": 88.3}[state]
    latitude = round(lat_base + np.random.uniform(-0.3, 0.3), 5)
    longitude = round(lon_base + np.random.uniform(-0.3, 0.3), 5)

    return {
        "work_id": f"WS/{district[:3].upper()}/{work_id:05d}",
        "state": state,
        "district": district,
        "constituency": f"{district} Constituency",
        "mp_name": mp_name,
        "sector": sector,
        "work_name": f"{base_desc} at village {random.randint(1,40)}, {district}",
        "sanction_amount": sanction_amount,
        "expenditure": expenditure,
        "date_of_administrative_approval": approval_date.strftime("%Y-%m-%d"),
        "expected_completion_date": expected_completion.strftime("%Y-%m-%d"),
        "actual_completion_date": actual_completion.strftime("%Y-%m-%d") if actual_completion else "",
        "work_status": status,
        "physical_progress_percent": physical_progress,
        "implementing_agency_name": agency,
        "latitude": latitude,
        "longitude": longitude,
        "is_planted_anomaly": False,
        "planted_anomaly_type": "",
    }


def plant_anomalies(df):
    df = df.copy()
    n = len(df)

    cost_idx = np.random.choice(n, 15, replace=False)
    for i in cost_idx:
        df.loc[i, "sanction_amount"] = int(df.loc[i, "sanction_amount"] * np.random.uniform(2.5, 4.0))
        df.loc[i, "expenditure"] = int(df.loc[i, "sanction_amount"] * np.random.uniform(0.7, 1.0))
        df.loc[i, "is_planted_anomaly"] = True
        df.loc[i, "planted_anomaly_type"] = "cost_anomaly"

    remaining = list(set(range(n)) - set(cost_idx))
    delay_idx = np.random.choice(remaining, 15, replace=False)
    for i in delay_idx:
        df.loc[i, "work_status"] = "In Progress"
        exp_date = pd.to_datetime(df.loc[i, "date_of_administrative_approval"]) + timedelta(days=60)
        df.loc[i, "expected_completion_date"] = exp_date.strftime("%Y-%m-%d")
        df.loc[i, "actual_completion_date"] = ""
        df.loc[i, "is_planted_anomaly"] = True
        df.loc[i, "planted_anomaly_type"] = "delay_anomaly"

    # Make a handful of these delayed projects share the SAME MP/agency, to power
    # the "repeat offender" entity view with a realistic pattern to find.
    repeat_mp = MP_NAMES[0]
    repeat_agency = AGENCIES[0]
    for i in list(delay_idx)[:6]:
        df.loc[i, "mp_name"] = repeat_mp
        df.loc[i, "implementing_agency_name"] = repeat_agency

    remaining2 = list(set(remaining) - set(delay_idx))
    dup_sources = np.random.choice(remaining2, 10, replace=False)
    for src in dup_sources:
        target = np.random.choice(remaining2)
        while target == src:
            target = np.random.choice(remaining2)
        df.loc[target, "work_name"] = df.loc[src, "work_name"]
        df.loc[target, "district"] = df.loc[src, "district"]
        df.loc[target, "latitude"] = df.loc[src, "latitude"] + np.random.uniform(-0.01, 0.01)
        df.loc[target, "longitude"] = df.loc[src, "longitude"] + np.random.uniform(-0.01, 0.01)
        df.loc[target, "is_planted_anomaly"] = True
        df.loc[target, "planted_anomaly_type"] = "duplicate_anomaly"

    remaining3 = list(set(remaining2) - set(dup_sources))
    mismatch_idx = np.random.choice(remaining3, 10, replace=False)
    for i in mismatch_idx:
        df.loc[i, "expenditure"] = int(df.loc[i, "sanction_amount"] * np.random.uniform(0.85, 0.98))
        df.loc[i, "physical_progress_percent"] = np.random.randint(0, 15)
        df.loc[i, "work_status"] = "In Progress"
        df.loc[i, "is_planted_anomaly"] = True
        df.loc[i, "planted_anomaly_type"] = "progress_mismatch"

    return df


def run(output_dir="data"):
    os.makedirs(output_dir, exist_ok=True)
    rows = [make_row(i) for i in range(1, N_PROJECTS + 1)]
    df = pd.DataFrame(rows)
    df = plant_anomalies(df)
    out_path = os.path.join(output_dir, "raw_mplads_sample.csv")
    df.to_csv(out_path, index=False)
    return out_path, len(df)


if __name__ == "__main__":
    path, n = run()
    print(f"Generated {n} rows -> {path}")
