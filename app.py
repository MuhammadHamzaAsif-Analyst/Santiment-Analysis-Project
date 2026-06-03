from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, render_template, request

from db_mysql import connect, fetch_columns, fetch_rows, get_db_config, get_table_name
from dsa import filter_sort_paginate


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load .env from the project directory (reliable even if the app is started elsewhere)
# Override existing environment vars so edits in .env take effect immediately
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

app = Flask(__name__)

CANON_COLUMNS = [
    "post_id",
    "timestamp",
    "day_of_week",
    "platform",
    "user_id",
    "location",
    "language",
    "text_content",
    "hashtags",
    "mentions",
    "keywords",
    "topic_category",
    "sentiment_score",
    "sentiment_label",
    "emotion_type",
    "toxicity_score",
    "likes_count",
    "shares_count",
    "comments_count",
    "impressions",
    "engagement_rate",
    "brand_name",
    "product_name",
    "campaign_name",
    "campaign_phase",
    "user_past_sentiment_avg",
    "user_engagement_growth",
    "buzz_change_rate",
]

NUMERIC_COLS = {
    "sentiment_score",
    "toxicity_score",
    "likes_count",
    "shares_count",
    "comments_count",
    "impressions",
    "engagement_rate",
    "user_past_sentiment_avg",
    "user_engagement_growth",
    "buzz_change_rate",
}


def _to_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _split_tokens(v):
    if v is None:
        return []
    s = str(v).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.replace("|", ",").split(",")]
    return [p for p in parts if p]


def _top_counts(rows, col, limit=8):
    counts = {}
    for r in rows:
        k = r.get(col)
        if k is None or str(k).strip() == "":
            continue
        k = str(k).strip()
        counts[k] = counts.get(k, 0) + 1
    items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return items[:limit]


def _top_token_counts(rows, col, limit=10):
    counts = {}
    for r in rows:
        for t in _split_tokens(r.get(col)):
            counts[t] = counts.get(t, 0) + 1
    items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return items[:limit]


def compute_insights(rows):
    n = len(rows)
    avg_sent = []
    avg_eng = []
    avg_tox = []
    for r in rows:
        s = _to_float(r.get("sentiment_score"))
        if s is not None:
            avg_sent.append(s)
        e = _to_float(r.get("engagement_rate"))
        if e is not None:
            avg_eng.append(e)
        t = _to_float(r.get("toxicity_score"))
        if t is not None:
            avg_tox.append(t)

    def mean(xs):
        return (sum(xs) / len(xs)) if xs else None

    return {
        "row_count": n,
        "avg_sentiment_score": mean(avg_sent),
        "avg_engagement_rate": mean(avg_eng),
        "avg_toxicity_score": mean(avg_tox),
        "by_platform": _top_counts(rows, "platform", limit=10),
        "by_day_of_week": _top_counts(rows, "day_of_week", limit=10),
        "by_topic": _top_counts(rows, "topic_category", limit=10),
        "by_sentiment": _top_counts(rows, "sentiment_label", limit=10),
        "by_emotion": _top_counts(rows, "emotion_type", limit=10),
        "top_hashtags": _top_token_counts(rows, "hashtags", limit=12),
        "top_keywords": _top_token_counts(rows, "keywords", limit=12),
        "top_mentions": _top_token_counts(rows, "mentions", limit=12),
    }


@app.get("/")
def index():
    cfg = get_db_config()
    safe_cfg = {
        "DB_HOST": cfg.get("host"),
        "DB_PORT": cfg.get("port"),
        "DB_USER": cfg.get("user"),
        "DB_NAME": cfg.get("database"),
        "DB_TABLE": os.getenv("DB_TABLE"),
        "DB_PASSWORD_SET": bool(cfg.get("password")),
    }
    try:
        table = get_table_name()
    except RuntimeError as e:
        missing = str(e)
        return render_template(
            "setup.html",
            error=missing,
            env_example_path=".env.example",
            required_vars=["DB_NAME", "DB_TABLE", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"],
            safe_cfg=safe_cfg,
        )
    max_rows = int(os.getenv("MAX_ROWS", "2000"))

    search_q = request.args.get("q", "")
    search_col = request.args.get("search_col") or None
    filter_col = request.args.get("filter_col") or None
    filter_val = request.args.get("filter_val", "")
    sort_col = request.args.get("sort_col") or None
    sort_dir = request.args.get("sort_dir", "asc")
    page = int(request.args.get("page", "1"))
    page_size = int(request.args.get("page_size", "25"))

    try:
        with connect() as conn:
            existing_columns = fetch_columns(conn, table)
            preferred = [c for c in CANON_COLUMNS if c in existing_columns]
            extras = [c for c in existing_columns if c not in set(CANON_COLUMNS)]
            columns = preferred + extras
            rows = fetch_rows(conn, table, columns=columns, limit=max_rows)
    except Exception as e:
        return render_template(
            "setup.html",
            error=f"Database connection failed: {e}",
            env_example_path=".env.example",
            required_vars=["DB_NAME", "DB_TABLE", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"],
            safe_cfg=safe_cfg,
        )

    insights = compute_insights(rows)

    shown_rows, total, plan = filter_sort_paginate(
        rows,
        search_q=search_q,
        search_col=search_col,
        filter_col=filter_col,
        filter_val=filter_val,
        sort_col=sort_col,
        sort_dir=sort_dir,
        numeric_cols=NUMERIC_COLS,
        page=page,
        page_size=page_size,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    return render_template(
        "index.html",
        table=table,
        columns=columns,
        rows=shown_rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        q=search_q,
        search_col=search_col,
        filter_col=filter_col,
        filter_val=filter_val,
        sort_col=sort_col,
        sort_dir=sort_dir,
        plan=plan,
        max_rows=max_rows,
        insights=insights,
    )


if __name__ == "__main__":
    app.run(host=os.getenv("FLASK_HOST", "127.0.0.1"), port=int(os.getenv("FLASK_PORT", "5000")), debug=True)

