from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from .ingest import Article

LOGGER = logging.getLogger(__name__)


@dataclass
class Theme:
    id: int
    title: str
    articles: list[Article]


def _topic_title(articles: list[Article]) -> str:
    vectorizer = TfidfVectorizer(stop_words="english", max_features=30, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([a.title for a in articles])
    scores = np.asarray(matrix.sum(axis=0)).ravel()
    terms = vectorizer.get_feature_names_out()
    best = [terms[i] for i in scores.argsort()[-3:][::-1] if scores[i] > 0]
    return " / ".join(best) if best else articles[0].title[:80]


def _embed_titles(titles: list[str]) -> np.ndarray | None:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    try:
        model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        embeddings = model.encode(titles, show_progress_bar=False, normalize_embeddings=True)
        LOGGER.info("Using sentence-transformers embeddings")
        return np.asarray(embeddings)
    except Exception as exc:
        LOGGER.warning("Embeddings failed, fallback to TF-IDF: %s", exc)
        return None


def build_themes(articles: list[Article], max_themes: int = 12) -> list[Theme]:
    if not articles:
        return []

    titles = [a.title for a in articles]
    vectors = _embed_titles(titles)

    if vectors is None:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=3000, ngram_range=(1, 2))
        vectors = vectorizer.fit_transform(titles)

    n_samples = len(articles)
    n_clusters = max(2, min(max_themes, int(math.sqrt(n_samples)) + 1)) if n_samples > 2 else 1

    labels = None
    if n_samples >= 5:
        try:
            import hdbscan

            clusterer = hdbscan.HDBSCAN(min_cluster_size=3, metric="euclidean")
            labels = clusterer.fit_predict(vectors if isinstance(vectors, np.ndarray) else vectors.toarray())
            LOGGER.info("Using HDBSCAN clustering")
        except Exception:
            labels = None

    if labels is None:
        clusterer = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = clusterer.fit_predict(vectors)
        LOGGER.info("Using KMeans clustering (%s clusters)", n_clusters)

    grouped: dict[int, list[Article]] = {}
    for label, article in zip(labels, articles, strict=False):
        group_key = int(label)
        if group_key < 0:
            group_key = max(labels) + 1
        grouped.setdefault(group_key, []).append(article)

    themes: list[Theme] = []
    for idx, (_, group_articles) in enumerate(
        sorted(grouped.items(), key=lambda kv: len(kv[1]), reverse=True),
        start=1,
    ):
        themes.append(Theme(id=idx, title=_topic_title(group_articles), articles=group_articles))

    return themes
