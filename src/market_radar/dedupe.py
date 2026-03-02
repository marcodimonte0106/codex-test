from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from rapidfuzz import fuzz

from .ingest import Article


def _canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    clean_query = "&".join(
        q for q in parts.query.split("&") if q and not q.startswith("utm_")
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, clean_query, ""))


def dedupe_articles(articles: list[Article], title_similarity_threshold: int = 92) -> list[Article]:
    by_url: dict[str, Article] = {}
    for article in articles:
        key = _canonical_url(article.url)
        existing = by_url.get(key)
        if existing is None or article.published_at > existing.published_at:
            by_url[key] = article

    unique = list(by_url.values())
    unique.sort(key=lambda a: a.published_at, reverse=True)

    deduped: list[Article] = []
    seen_titles: list[str] = []
    for article in unique:
        norm_title = article.title.strip().lower()
        if not norm_title:
            continue
        is_near_duplicate = any(
            fuzz.token_set_ratio(norm_title, seen) >= title_similarity_threshold
            for seen in seen_titles
        )
        if not is_near_duplicate:
            deduped.append(article)
            seen_titles.append(norm_title)

    return deduped
