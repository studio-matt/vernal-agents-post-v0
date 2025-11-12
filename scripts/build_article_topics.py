#!/usr/bin/env python3
# scripts/build_article_topics.py
# LLM-free topic modeling for scraped pages (depth 1-2).
# If duplicate helpers exist in the repo, reuse them and remove these local versions.

import os
import sys
import re
import json
import datetime
from collections import defaultdict
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# Core NLP / ML
import spacy
from gensim.models import Phrases, Phraser
from gensim.models.coherencemodel import CoherenceModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

# Import project utilities
from database import SessionLocal
from models import SystemSettings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------- CONFIG (load from system_settings) ---------------
def get_config_from_db():
    """Load configuration from system_settings table"""
    db = SessionLocal()
    try:
        config = {}
        
        # Get all system model settings
        settings = db.query(SystemSettings).filter(
            SystemSettings.setting_key.like("system_model_%")
        ).all()
        
        for setting in settings:
            key = setting.setting_key.replace("system_model_", "")
            value = setting.setting_value
            
            if key == "k_grid":
                config["K_GRID"] = json.loads(value) if value else [10, 15, 20, 25]
            elif key in ["phrases_threshold", "tfidf_max_df"]:
                config[key.upper()] = float(value) if value else (15.0 if key == "phrases_threshold" else 0.7)
            else:
                config[key.upper()] = int(value) if value else {
                    "phrases_min_count": 5,
                    "tfidf_min_df": 3,
                    "top_words": 12,
                    "snippets_per_topic": 8,
                    "max_per_domain": 50,
                    "max_per_domain_in_snippets": 1,
                }.get(key, 0)
        
        # Set defaults if not found
        defaults = {
            "PHRASES_MIN_COUNT": 5,
            "PHRASES_THRESHOLD": 15.0,
            "TFIDF_MIN_DF": 3,
            "TFIDF_MAX_DF": 0.7,
            "K_GRID": [10, 15, 20, 25],
            "TOP_WORDS": 12,
            "SNIPPETS_PER_TOPIC": 8,
            "MAX_PER_DOMAIN": 50,
            "MAX_PER_DOMAIN_IN_SNIPPETS": 1,
        }
        
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
        
        return config
    except Exception as e:
        logger.error(f"Error loading config from DB: {e}")
        # Return defaults
        return {
            "PHRASES_MIN_COUNT": 5,
            "PHRASES_THRESHOLD": 15.0,
            "TFIDF_MIN_DF": 3,
            "TFIDF_MAX_DF": 0.7,
            "K_GRID": [10, 15, 20, 25],
            "TOP_WORDS": 12,
            "SNIPPETS_PER_TOPIC": 8,
            "MAX_PER_DOMAIN": 50,
            "MAX_PER_DOMAIN_IN_SNIPPETS": 1,
        }
    finally:
        db.close()

CONFIG = get_config_from_db()

# Database and input settings
DB_URL = os.getenv("DB_URL", os.getenv("DATABASE_URL", ""))
INPUT_TABLE = "scrape_pages"
LANG_FILTER = {"en"}
MIN_DOC_LEN_CHARS = 400
MAX_PER_DOMAIN = CONFIG.get("MAX_PER_DOMAIN", 50)
MAX_PER_DOMAIN_IN_SNIPPETS = CONFIG.get("MAX_PER_DOMAIN_IN_SNIPPETS", 1)

PHRASES_MIN_COUNT = CONFIG.get("PHRASES_MIN_COUNT", 5)
PHRASES_THRESHOLD = CONFIG.get("PHRASES_THRESHOLD", 15.0)
TFIDF_MIN_DF = CONFIG.get("TFIDF_MIN_DF", 3)
TFIDF_MAX_DF = CONFIG.get("TFIDF_MAX_DF", 0.7)
K_GRID = CONFIG.get("K_GRID", [10, 15, 20, 25])
TOP_WORDS = CONFIG.get("TOP_WORDS", 12)
SNIPPETS_PER_TOPIC = CONFIG.get("SNIPPETS_PER_TOPIC", 8)

# --------- Helpers (reuse project ones if present) ---------
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")

def sentence_split(text: str):
    """Cheap & cheerful splitter; replace with existing utility if available"""
    sents = [s.strip() for s in SENT_SPLIT.split(text or "") if s and len(s.strip()) > 20]
    return sents[:200]

def normalize_domain(u: str) -> str:
    try:
        d = urlparse(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except:
        return ""

def spacy_pipeline():
    """If you have a shared spaCy nlp singleton, reuse it"""
    try:
        nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "textcat"])
        nlp.enable_pipe("lemmatizer")
        return nlp
    except OSError:
        logger.error("spaCy model 'en_core_web_sm' not found. Please install it: python -m spacy download en_core_web_sm")
        raise

def tokenize_docs(nlp, texts):
    out_tokens, out_sentences = [], []
    for t in texts:
        t = t or ""
        doc = nlp(t)
        toks = []
        for tok in doc:
            if tok.is_punct or tok.is_space or tok.like_num:
                continue
            lemma = tok.lemma_.lower().strip()
            if not lemma or len(lemma) < 2:
                continue
            if tok.pos_ in ("NOUN", "PROPN", "VERB", "ADJ", "ADV"):
                toks.append(lemma)
        out_tokens.append(toks)
        out_sentences.append(sentence_split(t))
    return out_tokens, out_sentences
# -----------------------------------------------------------

def coherence_from_H(H, terms, tokens_phrased, topn=TOP_WORDS):
    topic_terms = [[terms[i] for i in comp.argsort()[-topn:]] for comp in H]
    cm = CoherenceModel(topics=topic_terms, texts=tokens_phrased, coherence="c_v")
    return cm.get_coherence(), topic_terms

def label_topics(H, terms, idf, topm=TOP_WORDS):
    labels = []
    vocab = terms.tolist()
    idf_lookup = {t: idf[i] for i, t in enumerate(vocab)}
    for row in H:
        idx = row.argsort()[-topm:][::-1]
        cand = [(terms[i], row[i]) for i in idx]
        scored = []
        for t, w in cand:
            bonus = 1.3 if "_" in t else 1.0
            scored.append((t, w * idf_lookup.get(t, 1.0) * bonus))
        scored.sort(key=lambda x: x[1], reverse=True)
        title = " / ".join([t for t, _ in scored[:2]]) or (cand[0][0] if cand else "topic")
        labels.append(title[:35])
    return labels

def pick_snippets(W, topic_idx, docs_df, topic_top_terms, sentences, k=SNIPPETS_PER_TOPIC, max_per_domain=MAX_PER_DOMAIN_IN_SNIPPETS):
    termset = set(topic_top_terms)
    scores = [(i, float(W[i, topic_idx])) for i in range(W.shape[0])]
    scores.sort(key=lambda x: x[1], reverse=True)
    picks, seen = [], defaultdict(int)
    for i, s in scores:
        if s <= 0:
            break
        dom = docs_df.loc[i, "domain"]
        if max_per_domain is not None and seen[dom] >= max_per_domain:
            continue
        # choose the sentence with the most term overlap
        best_sent, best_overlap = "", -1
        for sent in sentences[i]:
            overlap = sum(1 for w in re.findall(r"[a-zA-Z0-9_]+", sent.lower()) if w in termset)
            if overlap > best_overlap:
                best_overlap, best_sent = overlap, sent
        if best_overlap <= 0:
            continue
        picks.append({
            "url": docs_df.loc[i, "url"],
            "title": docs_df.loc[i, "title"],
            "domain": dom,
            "snippet": best_sent.strip(),
            "score": s
        })
        seen[dom] += 1
        if len(picks) >= k:
            break
    return picks

def main():
    if not DB_URL:
        logger.error("DB_URL or DATABASE_URL environment variable not set")
        return
    
    # DB
    engine = create_engine(DB_URL)
    with engine.begin() as cxn:
        df = pd.read_sql(text(f"""
            SELECT id, url, domain, title, cleaned_text, lang, created_at
            FROM {INPUT_TABLE}
            WHERE cleaned_text IS NOT NULL AND cleaned_text <> ''
        """), cxn)

    # Normalization / filters
    if "domain" not in df.columns or df["domain"].isna().any():
        df["domain"] = df["url"].apply(normalize_domain)

    if LANG_FILTER:
        df = df[df["lang"].isin(LANG_FILTER)]

    df = df[df["cleaned_text"].str.len() >= MIN_DOC_LEN_CHARS].reset_index(drop=True)

    if MAX_PER_DOMAIN:
        df = (df.groupby("domain", group_keys=False)
                .apply(lambda g: g.nlargest(MAX_PER_DOMAIN, "created_at"))
                .reset_index(drop=True))

    if df.empty:
        logger.warning("No documents after filtering; aborting.")
        return

    logger.info(f"Processing {len(df)} documents")

    # Tokenize
    nlp = spacy_pipeline()
    tokens, sentences = tokenize_docs(nlp, df["cleaned_text"].tolist())

    # Phrase mining
    bigram = Phrases(tokens, min_count=PHRASES_MIN_COUNT, threshold=PHRASES_THRESHOLD, delimiter=b"_")
    trigram = Phrases(bigram[tokens], min_count=PHRASES_MIN_COUNT, threshold=PHRASES_THRESHOLD, delimiter=b"_")
    bigr = Phraser(bigram)
    trgr = Phraser(trigram)
    tokens_phrased = [trgr[bigr[tok]] for tok in tokens]
    docs_str = [" ".join(t) for t in tokens_phrased]

    # Vectorize
    tfidf = TfidfVectorizer(min_df=TFIDF_MIN_DF, max_df=TFIDF_MAX_DF, strip_accents="unicode")
    X = tfidf.fit_transform(docs_str)
    terms = tfidf.get_feature_names_out()
    idf = tfidf.idf_

    # K sweep (pick by coherence)
    best = None
    best_topic_terms = None
    for K in K_GRID:
        logger.info(f"Testing K={K}")
        nmf = NMF(n_components=K, init="nndsvd", random_state=42, max_iter=500)
        W = nmf.fit_transform(X)
        H = nmf.components_
        coh, topic_terms = coherence_from_H(H, terms, tokens_phrased, topn=TOP_WORDS)
        logger.info(f"K={K}, coherence={coh:.3f}")
        if (best is None) or (coh > best[0]):
            best = (coh, K, nmf, W, H)
            best_topic_terms = topic_terms

    coherence, K, nmf, W, H = best
    labels = label_topics(H, terms, idf, topm=TOP_WORDS)

    # Topic ordering, coverage
    topic_strength = W.sum(axis=0)
    if hasattr(topic_strength, "A1"):
        topic_strength = topic_strength.A1
    order = np.argsort(-topic_strength)
    coverage = topic_strength / (topic_strength.sum() + 1e-9)

    # Snippets (domain diverse)
    topic_snips = {}
    for t_idx in order:
        top_terms = best_topic_terms[int(t_idx)]
        snips = pick_snippets(W, int(t_idx), df, top_terms, sentences,
                              k=SNIPPETS_PER_TOPIC, max_per_domain=MAX_PER_DOMAIN_IN_SNIPPETS)
        topic_snips[int(t_idx)] = snips

    # Persist to DB
    now = datetime.datetime.utcnow()
    model_row = {
        "created_at": now,
        "algo": "nmf_tfidf",
        "tfidf_min_df": TFIDF_MIN_DF,
        "tfidf_max_df": TFIDF_MAX_DF,
        "phrases_min_count": PHRASES_MIN_COUNT,
        "phrases_threshold": PHRASES_THRESHOLD,
        "k": int(K),
        "coherence": float(coherence),
    }

    with engine.begin() as cxn:
        cxn.execute(text("""
            INSERT INTO topic_models (created_at, algo, tfidf_min_df, tfidf_max_df, phrases_min_count, phrases_threshold, k, coherence)
            VALUES (:created_at, :algo, :tfidf_min_df, :tfidf_max_df, :phrases_min_count, :phrases_threshold, :k, :coherence)
        """), model_row)
        model_id = cxn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        # Insert topics in ranked order
        topic_rows = []
        for rank, t_idx in enumerate(order, start=1):
            topic_rows.append({
                "model_id": model_id,
                "label": labels[int(t_idx)],
                "top_terms": json.dumps(best_topic_terms[int(t_idx)]),
                "coverage": float(coverage[int(t_idx)]),
                "rank": int(rank),
            })
        cxn.execute(text("""
            INSERT INTO topics (model_id, label, top_terms, coverage, rank)
            VALUES (:model_id, :label, :top_terms, :coverage, :rank)
        """), topic_rows)

        # Map rank → topic_id
        topic_ids = pd.read_sql(
            text("SELECT topic_id, rank FROM topics WHERE model_id = :m ORDER BY rank ASC"),
            cxn, params={"m": model_id}
        )
        rank_to_topic_id = {int(r): int(tid) for tid, r in zip(topic_ids["topic_id"], topic_ids["rank"])}

        # topic_docs: top 3 topics per document
        td_rows = []
        for i in range(W.shape[0]):
            top3 = np.argsort(-W[i])[:3]
            for t_idx in top3:
                rank_pos = int(np.where(order == t_idx)[0][0]) + 1
                td_rows.append({
                    "model_id": model_id,
                    "doc_id": int(df.loc[i, "id"]),
                    "topic_id": rank_to_topic_id[rank_pos],
                    "weight": float(W[i, t_idx]),
                })
        if td_rows:
            cxn.execute(text("""
                INSERT INTO topic_docs (model_id, doc_id, topic_id, weight)
                VALUES (:model_id, :doc_id, :topic_id, :weight)
            """), td_rows)

        # topic_snippets
        snip_rows = []
        for pos, t_idx in enumerate(order, start=1):
            t_id = rank_to_topic_id[pos]
            for s in topic_snips[int(t_idx)]:
                s["model_id"] = model_id
                s["topic_id"] = t_id
                snip_rows.append(s)
        if snip_rows:
            cxn.execute(text("""
                INSERT INTO topic_snippets (model_id, topic_id, url, domain, title, snippet, score)
                VALUES (:model_id, :topic_id, :url, :domain, :title, :snippet, :score)
            """), snip_rows)

    logger.info(f"✔ topics built: model_id={model_id}, K={K}, coherence={coherence:.3f}, docs={len(df)}")
    return model_id

if __name__ == "__main__":
    main()

