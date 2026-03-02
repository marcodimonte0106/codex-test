from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .ingest import Article
from .scoring import ScoredTheme


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = _connect(db_path)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                language TEXT,
                summary TEXT,
                ingested_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL,
                theme_rank INTEGER NOT NULL,
                theme_title TEXT NOT NULL,
                score REAL NOT NULL,
                article_count INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
    conn.close()


def persist_articles(db_path: str, articles: list[Article]) -> None:
    conn = _connect(db_path)
    now = datetime.utcnow().isoformat()
    with conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO articles (title, url, source, published_at, language, summary, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    a.title,
                    a.url,
                    a.source,
                    a.published_at.isoformat(),
                    a.language,
                    a.summary,
                    now,
                )
                for a in articles
            ],
        )
    conn.close()


def persist_themes(db_path: str, scored_themes: list[ScoredTheme]) -> None:
    conn = _connect(db_path)
    run_at = datetime.utcnow().isoformat()
    with conn:
        conn.executemany(
            """
            INSERT INTO themes (run_at, theme_rank, theme_title, score, article_count, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_at,
                    rank,
                    scored.theme.title,
                    scored.score,
                    len(scored.theme.articles),
                    json.dumps({"headlines": [a.to_dict() for a in scored.theme.articles[:5]]}, ensure_ascii=False),
                )
                for rank, scored in enumerate(scored_themes, start=1)
            ],
        )
    conn.close()


def export_themes(scored_themes: list[ScoredTheme], out_dir: str = ".") -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "themes.json"
    csv_path = out / "themes.csv"

    data = []
    for rank, scored in enumerate(scored_themes, start=1):
        data.append(
            {
                "rank": rank,
                "score": scored.score,
                "title": scored.theme.title,
                "article_count": len(scored.theme.articles),
                "headlines": [
                    {"title": a.title, "url": a.url, "source": a.source}
                    for a in scored.theme.articles[:5]
                ],
            }
        )

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "rank",
            "score",
            "title",
            "article_count",
            "headline_1",
            "headline_2",
            "headline_3",
            "headline_4",
            "headline_5",
        ])
        for row in data:
            heads = [h["title"] for h in row["headlines"]]
            heads = heads + [""] * (5 - len(heads))
            writer.writerow([row["rank"], row["score"], row["title"], row["article_count"], *heads])

    return json_path, csv_path
