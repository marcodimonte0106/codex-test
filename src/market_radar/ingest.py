from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

import feedparser
import requests

LOGGER = logging.getLogger(__name__)

DEFAULT_RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "https://www.investing.com/rss/news_25.rss",
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://www.marketwatch.com/rss/topstories",
]

GDELT_ARTLIST_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: datetime
    language: str | None = None
    summary: str | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["published_at"] = self.published_at.isoformat()
        return payload


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def fetch_gdelt(hours: int, max_records: int = 200) -> list[Article]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    params = {
        "query": "(economy OR markets OR inflation OR rates OR oil OR earnings)",
        "mode": "ArtList",
        "format": "json",
        "sort": "datedesc",
        "maxrecords": str(max_records),
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": now.strftime("%Y%m%d%H%M%S"),
    }

    try:
        response = requests.get(GDELT_ARTLIST_URL, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        LOGGER.exception("GDELT request failed: %s", exc)
        return []
    except ValueError as exc:
        LOGGER.exception("GDELT JSON parsing failed: %s", exc)
        return []

    articles: list[Article] = []
    for item in payload.get("articles", []):
        published = _parse_dt(item.get("seendate")) or now
        article = Article(
            title=(item.get("title") or "").strip(),
            url=(item.get("url") or "").strip(),
            source=(item.get("domain") or "GDELT").strip(),
            published_at=published,
            language=item.get("language") or item.get("sourceCountry"),
            summary=(item.get("socialimage") or "").strip() or None,
        )
        if article.title and article.url:
            articles.append(article)

    LOGGER.info("Fetched %s articles from GDELT", len(articles))
    return articles


def fetch_rss(feeds: Iterable[str], hours: int) -> list[Article]:
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[Article] = []

    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:  # feedparser can raise broad exceptions
            LOGGER.exception("RSS parsing failed for %s: %s", feed_url, exc)
            continue

        source = parsed.feed.get("title") or feed_url
        for entry in parsed.entries:
            published = _parse_dt(entry.get("published") or entry.get("updated"))
            if not published:
                published = datetime.now(timezone.utc)
            if published < window_start:
                continue

            article = Article(
                title=(entry.get("title") or "").strip(),
                url=(entry.get("link") or "").strip(),
                source=source,
                published_at=published,
                language=entry.get("language"),
                summary=(entry.get("summary") or entry.get("description") or "").strip() or None,
            )
            if article.title and article.url:
                out.append(article)

    LOGGER.info("Fetched %s articles from RSS feeds", len(out))
    return out


def fetch_all(hours: int, rss_feeds: Iterable[str] | None = None) -> list[Article]:
    feeds = list(rss_feeds) if rss_feeds is not None else DEFAULT_RSS_FEEDS
    articles = fetch_gdelt(hours=hours)
    articles.extend(fetch_rss(feeds=feeds, hours=hours))
    LOGGER.info("Total fetched before dedupe: %s", len(articles))
    return articles
