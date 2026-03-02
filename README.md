# market-radar

`market-radar` est un projet Python V1 pour construire un **radar mondial des news marchés** sans clé API:
- Ingestion via **GDELT 2.1** (public) + 5 flux RSS financiers.
- Normalisation des articles.
- Déduplication URL + quasi-duplicates par similarité de titres.
- Regroupement par thème via embeddings/clustering (avec fallback TF-IDF).
- Scoring d'importance (1 à 10) par thème.
- Export `themes.json` / `themes.csv` + stockage historique SQLite.

## 1) Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e .
```

> `sentence-transformers` et `hdbscan` sont utilisés si disponibles. Le pipeline bascule automatiquement sur TF-IDF + KMeans si nécessaire.

## 2) Exécution

Commande unique:

```bash
python -m market_radar --hours 24
```

Options utiles:
- `--hours 24` : fenêtre temporelle (UTC) en heures.
- `--db market_radar.db` : chemin base SQLite.
- `--out .` : répertoire de sortie de `themes.json` et `themes.csv`.
- `--verbose` : logs détaillés.

Exemple:

```bash
python -m market_radar --hours 12 --db data/market_radar.db --out output --verbose
```

## 3) Sorties

- Affichage console du **Top 10 thèmes** trié par importance.
- Export:
  - `themes.json`
  - `themes.csv`
- SQLite:
  - table `articles`
  - table `themes`

## 4) Structure

```text
src/market_radar/
  ingest.py
  dedupe.py
  themes.py
  scoring.py
  store.py
  cli.py
  __main__.py
```

## 5) Notes techniques

- Réseau: erreurs capturées et loggées côté ingestion (GDELT / RSS).
- Dates: normalisées en UTC.
- Déduplication:
  - URL canonique d'abord,
  - puis similarité titre (`rapidfuzz.token_set_ratio`).
- Clustering:
  - priorité embeddings `sentence-transformers`,
  - puis HDBSCAN si disponible,
  - sinon fallback TF-IDF + KMeans.
