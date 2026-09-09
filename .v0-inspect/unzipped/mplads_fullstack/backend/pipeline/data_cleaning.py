"""
data_cleaning.py -- cleans raw MPLADS-style data into a standardized DataFrame.

To use REAL government data instead of the synthetic sample: fill in COLUMN_MAP
below with real_column_name -> standard_name, and point RAW_DATA_PATH (in main.py)
at your real CSV.
"""

import pandas as pd
import numpy as np

COLUMN_MAP = {
    # Example mapping for the dataful.in / mplads.gov.in work-level export:
    # "unique_work_number": "work_id",
    # "nodal_district": "district",
}

REQUIRED_COLUMNS = [
    "work_id", "state", "district", "sector", "work_name",
    "sanction_amount", "expenditure", "date_of_administrative_approval",
    "expected_completion_date", "work_status", "physical_progress_percent",
]

OPTIONAL_COLUMNS = [
    "constituency", "mp_name", "implementing_agency_name",
    "latitude", "longitude", "actual_completion_date",
]


def load_raw(path):
    df = pd.read_csv(path)
    if COLUMN_MAP:
        df = df.rename(columns=COLUMN_MAP)
    return df


def field_availability(df):
    present_required = [c for c in REQUIRED_COLUMNS if c in df.columns]
    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    present_optional = [c for c in OPTIONAL_COLUMNS if c in df.columns]
    missing_optional = [c for c in OPTIONAL_COLUMNS if c not in df.columns]
    return {
        "present_required": present_required,
        "missing_required": missing_required,
        "present_optional": present_optional,
        "missing_optional": missing_optional,
    }


def clean(df):
    df = df.copy()

    for col in ["state", "district", "sector", "work_status", "implementing_agency_name", "mp_name"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "work_name" in df.columns:
        df["work_name"] = df["work_name"].astype(str).str.strip()

    for col in ["sanction_amount", "expenditure", "physical_progress_percent"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] < 0, col] = np.nan

    if "physical_progress_percent" in df.columns:
        df["physical_progress_percent"] = df["physical_progress_percent"].clip(0, 100)

    for col in ["date_of_administrative_approval", "expected_completion_date",
                "actual_completion_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "work_name" in df.columns:
        df = df[df["work_name"].notna() & (df["work_name"].str.len() > 3)]
    if "sanction_amount" in df.columns:
        df = df[df["sanction_amount"].notna() & (df["sanction_amount"] > 0)]

    if "expenditure" in df.columns:
        df["expenditure"] = df["expenditure"].fillna(0)

    df = df.reset_index(drop=True)
    return df
