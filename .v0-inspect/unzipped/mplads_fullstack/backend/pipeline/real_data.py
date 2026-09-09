import hashlib
import pandas as pd

COLUMN_MAP = {
    "MP NAME": "mp_name",
    "WORK": "work_name",
    "CATEGORY": "sector",
    "STATE": "state",
    "CONSTITUENCY": "constituency",
    "IDA": "implementing_agency_name",
    "CITY": "city",
    "WARD": "ward",
    "BLOCK": "block",
    "VILLAGE": "village",
    "RECOMMENDED DATE": "date_of_administrative_approval",
    "ALLOCATION AMOUNT": "sanction_amount",
    "IDA APPROVAL": "ida_approval",
    "STATUS": "work_status",
    "HOUSE": "house",
}


def stable_work_id(row):
    raw = "|".join(str(row.get(c, "")) for c in [
        "mp_name", "work_name", "state", "constituency", "block", "village",
        "date_of_administrative_approval", "sanction_amount", "house"
    ])
    return "MPLADS-" + hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:14].upper()


def load(path):
    df = pd.read_csv(path, sep=";", quotechar='"', dtype=str, encoding="utf-8-sig")
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    for col in ["mp_name", "work_name", "state", "constituency", "implementing_agency_name", "block", "village", "work_status"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    df["sanction_amount"] = pd.to_numeric(df.get("sanction_amount"), errors="coerce")
    df["date_of_administrative_approval"] = pd.to_datetime(df.get("date_of_administrative_approval"), errors="coerce")
    df["work_id"] = df.apply(stable_work_id, axis=1)
    # This source does not publish expenditure/progress/completion coordinates.
    df["expenditure"] = pd.NA
    df["expected_completion_date"] = pd.NaT
    df["actual_completion_date"] = pd.NaT
    df["physical_progress_percent"] = pd.NA
    df["latitude"] = pd.NA
    df["longitude"] = pd.NA
    # Keep district nullable rather than pretending constituency is a district.
    df["district"] = ""
    df["is_planted_anomaly"] = False
    df["planted_anomaly_type"] = ""
    df = df[df["work_name"].str.len() > 3]
    df = df[df["sanction_amount"].notna() & (df["sanction_amount"] > 0)]
    df = df.drop_duplicates(subset=["work_id"], keep="last")
    return df.reset_index(drop=True)
