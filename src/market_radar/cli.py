from __future__ import annotations

import argparse
import logging

from .dedupe import dedupe_articles
from .ingest import fetch_all
from .scoring import score_themes
from .store import export_themes, init_db, persist_articles, persist_themes
from .themes import build_themes


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Market Radar - radar mondial des news marchés")
    parser.add_argument("--hours", type=int, default=24, help="Fenêtre temporelle en heures (défaut: 24)")
    parser.add_argument("--db", default="market_radar.db", help="Chemin SQLite")
    parser.add_argument("--out", default=".", help="Répertoire de sortie pour themes.json/csv")
    parser.add_argument("--verbose", action="store_true", help="Activer logs debug")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Starting market radar with --hours=%s", args.hours)
    init_db(args.db)

    articles = fetch_all(hours=args.hours)
    deduped = dedupe_articles(articles)
    logger.info("Articles after dedupe: %s", len(deduped))

    persist_articles(args.db, deduped)

    themes = build_themes(deduped)
    scored_themes = score_themes(themes)[:10]

    persist_themes(args.db, scored_themes)
    json_path, csv_path = export_themes(scored_themes, out_dir=args.out)

    print("\nTop 10 thèmes marché (importance):")
    for rank, item in enumerate(scored_themes, start=1):
        print(
            f"{rank:02d}. [Score {item.score:>4}] {item.theme.title} "
            f"({len(item.theme.articles)} articles)"
        )
        for article in item.theme.articles[:5]:
            print(f"    - {article.title} | {article.url}")

    print(f"\nExports: {json_path} / {csv_path}")
    print(f"SQLite DB: {args.db}")

    return 0
