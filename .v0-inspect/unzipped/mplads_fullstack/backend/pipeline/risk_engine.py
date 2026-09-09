import pandas as pd

DEFAULT_WEIGHTS = {
    "cost_anomaly_score": 0.40,
    "delay_anomaly_score": 0.20,
    "duplicate_score": 0.25,
    "progress_mismatch_score": 0.15,
}


def compute_risk_score(df, weights=None):
    df = df.copy()
    weights = weights or DEFAULT_WEIGHTS
    # Renormalise across signals that actually have evidence. Missing-data
    # signals must never silently count as a zero-risk observation.
    score = pd.Series(0.0, index=df.index)
    denom = pd.Series(0.0, index=df.index)
    confidence_map = {
        "cost_anomaly_score": "cost_confidence",
        "delay_anomaly_score": "delay_confidence",
        "duplicate_score": "duplicate_confidence",
        "progress_mismatch_score": "progress_confidence",
    }
    for col, w in weights.items():
        if col in df.columns:
            conf = df.get(confidence_map.get(col), pd.Series(1.0, index=df.index)).fillna(0).clip(0, 1)
            available = conf > 0
            score += df[col].fillna(0) * w * available
            denom += w * available
    df["risk_score"] = (score / denom.replace(0, pd.NA)).fillna(0).round(1)
    return df


def generate_reasons(row):
    reasons = []
    if row.get("cost_anomaly_score", 0) >= 40:
        ratio = row.get("cost_ratio_vs_peers", 1.0)
        note = " (limited peer confidence)" if row.get("cost_confidence", 1) < 0.6 else ""
        reasons.append(f"Allocation is {ratio:.1f}x the median of comparable works in the same state/sector{note}")
    if row.get("delay_confidence", 0) > 0 and row.get("delay_anomaly_score", 0) >= 40:
        reasons.append(f"Project is {int(row.get('days_overdue', 0))} days overdue compared with its expected completion date")
    if row.get("duplicate_score", 0) >= 60:
        other = row.get("most_similar_work_id", "another project")
        reasons.append(f"Work description is {row.get('duplicate_score', 0):.0f}% similar to {other} within the same constituency")
    if row.get("progress_confidence", 0) > 0 and row.get("progress_mismatch_score", 0) >= 40:
        reasons.append(f"{row.get('expenditure_ratio', 0)*100:.0f}% of funds spent but only {row.get('physical_progress_percent', 0):.0f}% physical progress reported")
    if not reasons:
        reasons.append("No significant anomaly signals detected in the available source fields")
    return reasons


def risk_level(score):
    if score >= 60: return "High"
    if score >= 30: return "Medium"
    return "Low"


def build_final_table(df, weights=None):
    df = compute_risk_score(df, weights=weights)
    df["reasons"] = df.apply(generate_reasons, axis=1)
    df["reasons_text"] = df["reasons"].apply(lambda r: " | ".join(r))
    df["risk_level"] = df["risk_score"].apply(risk_level)
    df["data_coverage"] = df.apply(lambda r: round(sum(float(r.get(c,0) or 0)>0 for c in ["cost_confidence","delay_confidence","progress_confidence","duplicate_confidence"])/4*100,1), axis=1)
    return df.sort_values("risk_score", ascending=False).reset_index(drop=True)
