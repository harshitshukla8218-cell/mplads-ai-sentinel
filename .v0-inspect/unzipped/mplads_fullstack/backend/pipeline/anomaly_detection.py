"""
anomaly_detection.py -- cost, delay, progress-mismatch and duplicate detection,
plus a DATA CONFIDENCE score (Unique Feature #1): if the fields a given anomaly
check depends on are missing/null for a project, we don't silently show "0 risk" --
we flag that the score for that signal has LOW CONFIDENCE, so investigators know
the difference between "verified normal" and "we don't actually know".
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_cost_anomaly(df, group_cols=("state", "sector")):
    df = df.copy()
    group_cols = [c for c in group_cols if c in df.columns]

    if not group_cols or "sanction_amount" not in df.columns:
        df["cost_anomaly_score"] = 0
        df["cost_confidence"] = 0.0
        df["peer_median_cost"] = np.nan
        return df

    peer_count = df.groupby(group_cols)["sanction_amount"].transform("count")
    peer_median = df.groupby(group_cols)["sanction_amount"].transform("median")

    df["peer_median_cost"] = peer_median
    ratio = df["sanction_amount"] / peer_median.replace(0, np.nan)
    ratio = ratio.fillna(1.0)
    df["cost_ratio_vs_peers"] = ratio

    score = ((ratio - 1.0) / (3.0 - 1.0)) * 100
    df["cost_anomaly_score"] = score.clip(0, 100).round(1)

    # Confidence: a peer group of 1-2 projects gives an unreliable median.
    df["cost_confidence"] = np.clip(peer_count / 5, 0.2, 1.0).round(2)
    return df


def compute_delay_anomaly(df, today=None):
    df = df.copy()
    if today is None:
        today = pd.Timestamp(datetime.now().date())

    if "expected_completion_date" in df.columns and "work_status" in df.columns:
        has_date = df["expected_completion_date"].notna()
        not_done = df["work_status"].astype(str).str.lower() != "completed"
        days_overdue = (today - df["expected_completion_date"]).dt.days
        days_overdue = days_overdue.where(not_done, 0)
        days_overdue = days_overdue.clip(lower=0).fillna(0)
        df["days_overdue"] = days_overdue

        delay_score = (days_overdue / 180) * 100
        df["delay_anomaly_score"] = delay_score.clip(0, 100).round(1)
        df["delay_confidence"] = np.where(has_date, 1.0, 0.0)
    else:
        df["days_overdue"] = 0
        df["delay_anomaly_score"] = 0
        df["delay_confidence"] = 0.0

    if "expenditure" in df.columns and "sanction_amount" in df.columns:
        df["expenditure_ratio"] = (df["expenditure"] / df["sanction_amount"].replace(0, np.nan)).fillna(0)
    else:
        df["expenditure_ratio"] = 0

    if "physical_progress_percent" in df.columns:
        has_progress = df["physical_progress_percent"].notna()
        mismatch = (df["expenditure_ratio"] * 100) - df["physical_progress_percent"].fillna(0)
        mismatch = mismatch.clip(lower=0)
        df["progress_mismatch_score"] = ((mismatch / 60) * 100).clip(0, 100).round(1)
        df["progress_confidence"] = np.where(has_progress, 1.0, 0.0)
    else:
        df["progress_mismatch_score"] = 0
        df["progress_confidence"] = 0.0

    return df


def compute_duplicate_scores(df, text_col="work_name", group_col="constituency",
                              similarity_threshold=0.85):
    df = df.copy()
    df["duplicate_score"] = 0.0
    df["most_similar_work_id"] = ""
    df["duplicate_confidence"] = 1.0 if text_col in df.columns else 0.0

    if text_col not in df.columns:
        return df

    group_col = group_col if group_col in df.columns else None
    if group_col:
        # Compare works in the same constituency and, when available, the same block.
        # This reduces false positives from legitimate repeated work templates.
        if "block" in df.columns:
            df["_dup_group"] = df[group_col].fillna("").astype(str) + "|" + df["block"].fillna("").astype(str) + "|" + df.get("village", pd.Series("", index=df.index)).fillna("").astype(str)
            df.loc[df["_dup_group"].str.endswith("||"), "_dup_group"] = df.loc[df["_dup_group"].str.endswith("||"), group_col].fillna("").astype(str)
            groups = df.groupby("_dup_group")
        else:
            groups = df.groupby(group_col)
    else:
        groups = [(None, df)]

    for _, group_df in groups:
        if len(group_df) < 2:
            continue
        idx = group_df.index
        texts = group_df[text_col].fillna("").tolist()

        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
        except ValueError:
            continue

        sim_matrix = cosine_similarity(tfidf_matrix)
        np.fill_diagonal(sim_matrix, 0)

        max_sim = sim_matrix.max(axis=1)
        max_sim_idx = sim_matrix.argmax(axis=1)

        for global_i, sim, other_local_i in zip(idx, max_sim, max_sim_idx):
            df.loc[global_i, "duplicate_score"] = round(float(sim) * 100, 1)
            other_global_i = idx[other_local_i]
            df.loc[global_i, "most_similar_work_id"] = df.loc[other_global_i, "work_id"] \
                if "work_id" in df.columns else str(other_global_i)

    df["is_possible_duplicate"] = df["duplicate_score"] >= (similarity_threshold * 100)
    return df


def compute_overall_confidence(df):
    """Unique Feature #1 continued: one overall confidence value (0-1) per
    project summarizing how much of the risk score should be trusted, based
    on how many of the underlying signals actually had usable data."""
    df = df.copy()
    conf_cols = [c for c in ["cost_confidence", "delay_confidence",
                              "progress_confidence", "duplicate_confidence"] if c in df.columns]
    if conf_cols:
        df["overall_confidence"] = df[conf_cols].mean(axis=1).round(2)
    else:
        df["overall_confidence"] = 0.5
    return df
