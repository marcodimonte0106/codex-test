from __future__ import annotations

import re
from dataclasses import dataclass

from .themes import Theme

SOURCE_WEIGHTS = {
    "Reuters": 1.0,
    "The Wall Street Journal": 0.95,
    "Financial Times": 0.95,
    "The Economist": 0.9,
    "MarketWatch": 0.8,
    "Investing.com": 0.7,
}

SENSITIVE_KEYWORDS = {
    "rates",
    "inflation",
    "war",
    "oil",
    "sanctions",
    "bankruptcy",
    "earnings",
    "tariff",
    "recession",
    "default",
    "gdp",
    "federal reserve",
    "ecb",
    "boj",
}

NUMBER_PATTERN = re.compile(r"(\b\d+(?:\.\d+)?%\b)|(\$\s?\d+[\d,.]*(?:bn|m|k)?)", re.IGNORECASE)


@dataclass
class ScoredTheme:
    theme: Theme
    score: float


def _source_score(theme: Theme) -> float:
    if not theme.articles:
        return 0
    weights = []
    for article in theme.articles:
        matched = 0.5
        for source, weight in SOURCE_WEIGHTS.items():
            if source.lower() in article.source.lower():
                matched = weight
                break
        weights.append(matched)
    return sum(weights) / len(weights)


def _keyword_score(text: str) -> float:
    text_lower = text.lower()
    hits = sum(1 for kw in SENSITIVE_KEYWORDS if kw in text_lower)
    return min(hits / 4, 1.0)


def _numbers_score(text: str) -> float:
    return 1.0 if NUMBER_PATTERN.search(text) else 0.0


def score_themes(themes: list[Theme]) -> list[ScoredTheme]:
    if not themes:
        return []

    max_volume = max(len(t.articles) for t in themes)
    scored: list[ScoredTheme] = []
    for theme in themes:
        combined_text = " ".join(f"{a.title} {a.summary or ''}" for a in theme.articles)

        volume_component = len(theme.articles) / max_volume
        source_component = _source_score(theme)
        keyword_component = _keyword_score(combined_text)
        numbers_component = _numbers_score(combined_text)

        raw = (
            0.4 * volume_component
            + 0.25 * source_component
            + 0.25 * keyword_component
            + 0.10 * numbers_component
        )
        score = round(1 + raw * 9, 2)
        scored.append(ScoredTheme(theme=theme, score=score))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored
