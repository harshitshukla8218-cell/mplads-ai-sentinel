"""
database.py -- SQLite persistence layer.

Why SQLite (not just CSV files): a real "ready to use" app needs data that
survives restarts, supports concurrent reads while the API is running, and
can be queried with filters/pagination efficiently. SQLite gives us all of
that with zero setup (single file, no server to install) -- perfect for an
MVP that a small team can still demo confidently, and it's a straightforward
upgrade path to Postgres later (same SQL, just swap the connection).
"""

import sqlite3
import json
import os
import pandas as pd
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "mplads.db")


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                work_id TEXT PRIMARY KEY,
                state TEXT, district TEXT, constituency TEXT, mp_name TEXT,
                sector TEXT, work_name TEXT,
                sanction_amount REAL, expenditure REAL,
                date_of_administrative_approval TEXT,
                expected_completion_date TEXT, actual_completion_date TEXT,
                work_status TEXT, physical_progress_percent REAL,
                implementing_agency_name TEXT,
                latitude REAL, longitude REAL,
                cost_anomaly_score REAL, cost_confidence REAL, cost_ratio_vs_peers REAL,
                delay_anomaly_score REAL, delay_confidence REAL, days_overdue REAL,
                progress_mismatch_score REAL, progress_confidence REAL, expenditure_ratio REAL,
                duplicate_score REAL, duplicate_confidence REAL, most_similar_work_id TEXT,
                overall_confidence REAL,
                risk_score REAL, risk_level TEXT, reasons_json TEXT,
                is_planted_anomaly INTEGER, planted_anomaly_type TEXT, data_coverage REAL,
                source_name TEXT, source_snapshot TEXT, review_status TEXT DEFAULT 'New', investigator_note TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id TEXT, verdict TEXT, signal_scores_json TEXT, created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weights (
                signal TEXT PRIMARY KEY, weight REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT, source_name TEXT, snapshot_time TEXT,
                source_max_date TEXT, record_count INTEGER, changed_count INTEGER, new_count INTEGER,
                missing_fields_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT, work_id TEXT, snapshot_time TEXT,
                work_status TEXT, sanction_amount REAL, expenditure REAL, physical_progress_percent REAL,
                expected_completion_date TEXT, source_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, work_id TEXT, detected_at TEXT,
                field_name TEXT, previous_value TEXT, current_value TEXT, source_name TEXT
            )
        """)


def is_empty():
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as n FROM projects").fetchone()
        return row["n"] == 0


def bulk_insert_projects(df):
    cols = [
        "work_id", "state", "district", "constituency", "mp_name", "sector", "work_name",
        "sanction_amount", "expenditure", "date_of_administrative_approval",
        "expected_completion_date", "actual_completion_date", "work_status",
        "physical_progress_percent", "implementing_agency_name", "latitude", "longitude",
        "cost_anomaly_score", "cost_confidence", "cost_ratio_vs_peers",
        "delay_anomaly_score", "delay_confidence", "days_overdue",
        "progress_mismatch_score", "progress_confidence", "expenditure_ratio",
        "duplicate_score", "duplicate_confidence", "most_similar_work_id",
        "overall_confidence", "risk_score", "risk_level", "reasons_json",
        "is_planted_anomaly", "planted_anomaly_type", "data_coverage", "source_name", "source_snapshot", "review_status", "investigator_note",
    ]
    placeholders = ",".join(["?"] * len(cols))
    with get_conn() as conn:
        conn.execute("DELETE FROM projects")
        for _, row in df.iterrows():
            values = []
            for c in cols:
                v = row.get(c)
                try:
                    if pd.isna(v):
                        v = None
                except (TypeError, ValueError):
                    pass
                if c == "reasons_json":
                    v = json.dumps(row.get("reasons", []))
                elif c == "is_planted_anomaly":
                    v = int(bool(row.get("is_planted_anomaly", False)))
                elif hasattr(v, "isoformat"):
                    v = v.isoformat()
                values.append(v)
            conn.execute(f"INSERT INTO projects ({','.join(cols)}) VALUES ({placeholders})", values)


def query_projects(state=None, district=None, sector=None, min_score=0, search=None,
                    sort_by="risk_score", sort_dir="desc", limit=100, offset=0):
    where = ["risk_score >= ?"]
    params = [min_score]
    if state:
        where.append("state = ?"); params.append(state)
    if district:
        where.append("district = ?"); params.append(district)
    if sector:
        where.append("sector = ?"); params.append(sector)
    if search:
        where.append("(work_name LIKE ? OR work_id LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    sort_by = sort_by if sort_by in ("risk_score", "sanction_amount", "days_overdue") else "risk_score"
    sort_dir = "ASC" if sort_dir.lower() == "asc" else "DESC"

    sql = f"""
        SELECT * FROM projects
        WHERE {' AND '.join(where)}
        ORDER BY {sort_by} {sort_dir}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        count_sql = f"SELECT COUNT(*) as n FROM projects WHERE {' AND '.join(where)}"
        total = conn.execute(count_sql, params[:-2]).fetchone()["n"]
    return [dict(r) for r in rows], total


def get_project(work_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM projects WHERE work_id = ?", (work_id,)).fetchone()
        return dict(row) if row else None


def update_project_score(work_id, risk_score, risk_level, reasons):
    with get_conn() as conn:
        conn.execute(
            "UPDATE projects SET risk_score = ?, risk_level = ?, reasons_json = ? WHERE work_id = ?",
            (risk_score, risk_level, json.dumps(reasons), work_id),
        )


def get_filter_options():
    with get_conn() as conn:
        states = [r["state"] for r in conn.execute("SELECT DISTINCT state FROM projects ORDER BY state")]
        districts = [r["district"] for r in conn.execute("SELECT DISTINCT district FROM projects ORDER BY district")]
        sectors = [r["sector"] for r in conn.execute("SELECT DISTINCT sector FROM projects ORDER BY sector")]
    return {"states": states, "districts": districts, "sectors": sectors}


def get_stats():
    with get_conn() as conn:
        row = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) as high,
                   SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) as medium,
                   SUM(CASE WHEN risk_level='Low' THEN 1 ELSE 0 END) as low,
                   AVG(risk_score) as avg_score,
                   SUM(sanction_amount) as total_sanctioned
            FROM projects
        """).fetchone()
    return dict(row)


def entity_leaderboard(entity_col, min_works=2, limit=15):
    assert entity_col in ("mp_name", "implementing_agency_name")
    with get_conn() as conn:
        rows = conn.execute(f"""
            SELECT {entity_col} as entity_name,
                   COUNT(*) as total_works,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) as high_risk_works,
                   AVG(risk_score) as avg_risk_score,
                   SUM(sanction_amount) as total_sanctioned
            FROM projects
            WHERE {entity_col} IS NOT NULL AND {entity_col} != ''
            GROUP BY {entity_col}
            HAVING COUNT(*) >= ?
            ORDER BY high_risk_works DESC, avg_risk_score DESC
            LIMIT ?
        """, (min_works, limit)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["high_risk_rate"] = round((d["high_risk_works"] / d["total_works"]) * 100, 1) if d["total_works"] else 0
        d["avg_risk_score"] = round(d["avg_risk_score"], 1) if d["avg_risk_score"] else 0
        result.append(d)
    return result


def get_all_projects_df():
    """Load the whole table back into a DataFrame -- used when recomputing
    risk scores after feedback changes the weights."""
    import pandas as pd
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM projects", conn)
    df["reasons"] = df["reasons_json"].apply(lambda s: json.loads(s) if s else [])
    return df


def record_ingestion(source_name, snapshot_time, source_max_date, record_count, changed_count, new_count, missing_fields):
    with get_conn() as conn:
        conn.execute("INSERT INTO ingestion_snapshots(source_name,snapshot_time,source_max_date,record_count,changed_count,new_count,missing_fields_json) VALUES (?,?,?,?,?,?,?)", (source_name,snapshot_time,source_max_date,record_count,changed_count,new_count,json.dumps(missing_fields)))


def latest_ingestion():
    with get_conn() as conn:
        row=conn.execute("SELECT * FROM ingestion_snapshots ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def record_project_snapshots(df, snapshot_time, source_name):
    fields=["work_id","work_status","sanction_amount","expenditure","physical_progress_percent","expected_completion_date"]
    with get_conn() as conn:
        for _, r in df.iterrows():
            vals=[]
            for c in fields[1:]:
                v=r.get(c)
                if pd.isna(v): v=None
                elif hasattr(v,'isoformat'): v=v.isoformat()
                vals.append(v)
            conn.execute("INSERT INTO project_snapshots(work_id,snapshot_time,work_status,sanction_amount,expenditure,physical_progress_percent,expected_completion_date,source_name) VALUES (?,?,?,?,?,?,?,?)", (r.get("work_id"),snapshot_time,*vals,source_name))


def detect_changes(df, snapshot_time, source_name):
    changes=[]; new_count=0
    comparable=["work_status","sanction_amount","expenditure","physical_progress_percent","expected_completion_date"]
    with get_conn() as conn:
        for _, r in df.iterrows():
            old=conn.execute("SELECT work_status,sanction_amount,expenditure,physical_progress_percent,expected_completion_date FROM projects WHERE work_id=?",(r.get("work_id"),)).fetchone()
            if not old:
                new_count+=1; continue
            oldd=dict(old)
            for c in comparable:
                nv=r.get(c); ov=oldd.get(c)
                if pd.isna(nv): nv=None
                if hasattr(nv,'isoformat'): nv=nv.isoformat()
                if str(nv) != str(ov):
                    changes.append((r.get("work_id"),snapshot_time,c,str(ov),str(nv),source_name))
        conn.executemany("INSERT INTO project_changes(work_id,detected_at,field_name,previous_value,current_value,source_name) VALUES (?,?,?,?,?,?)", changes)
    return changes,new_count


def recent_changes(limit=100):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM project_changes ORDER BY id DESC LIMIT ?",(limit,)).fetchall()]


def update_review(work_id, status=None, note=None):
    with get_conn() as conn:
        conn.execute("UPDATE projects SET review_status=COALESCE(?,review_status), investigator_note=COALESCE(?,investigator_note) WHERE work_id=?",(status,note,work_id))


def bulk_update_scores(df):
    with get_conn() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "UPDATE projects SET risk_score = ?, risk_level = ?, reasons_json = ? WHERE work_id = ?",
                (row["risk_score"], row["risk_level"], json.dumps(row["reasons"]), row["work_id"]),
            )
