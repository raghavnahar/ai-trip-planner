import logging
import re
import time
from typing import List, Tuple

import numpy as np
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex


logger = logging.getLogger(__name__)


def ddg_search(query: str, max_results: int = 8) -> List[dict]:
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        logger.warning("DDG search failed: %s", e)
        return []


def fetch_page_text(url: str, max_chars: int = 4000) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(" ")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
        return ""


def chunk_text(text: str, chunk_words: int = 220, overlap_words: int = 40) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    step = max(1, chunk_words - overlap_words)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_words])
        if chunk:
            chunks.append(chunk)
    return chunks


def gather_corpus(query: str, top_sources: int = 3) -> List[Tuple[str, str]]:
    """Return list of (chunk_text, source_url)."""
    results = ddg_search(query, max_results=10)
    corpus: List[Tuple[str, str]] = []
    used = 0
    for res in results:
        if used >= top_sources:
            break
        url = res.get("href") or res.get("link") or ""
        if not url:
            continue
        body = fetch_page_text(url)
        if not body:
            continue
        for c in chunk_text(body):
            corpus.append((c, url))
        used += 1
        time.sleep(0.35)
    return corpus


class InMemoryVectorStore:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index: AnnoyIndex | None = None
        self.chunks: List[str] = []
        self.sources: List[str] = []

    def build(self, corpus: List[Tuple[str, str]]):
        if not corpus:
            return
        self.chunks = [c for c, _ in corpus]
        self.sources = [u for _, u in corpus]
        embeds = self._embed(self.chunks)
        self.index = AnnoyIndex(self.dimension, "angular")
        for i, vec in enumerate(embeds):
            self.index.add_item(i, vec.astype(np.float32))
        self.index.build(10)
        logger.info("Annoy index built with %d chunks", len(self.chunks))

    def _embed(self, texts: List[str]) -> np.ndarray:
        em = self.model.encode(texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
        return em

    def search(self, query: str, k: int = 6) -> List[Tuple[str, str, float]]:
        if not self.index or not self.chunks:
            return []
        qv = self._embed([query])[0].astype(np.float32)
        idxs, distances = self.index.get_nns_by_vector(qv, k, include_distances=True)
        sims = [1 - (d ** 2) / 2 for d in distances]
        results: List[Tuple[str, str, float]] = []
        for i, idx in enumerate(idxs):
            if 0 <= idx < len(self.chunks):
                results.append((self.chunks[idx], self.sources[idx], float(sims[i])))
        return results


def build_context_with_retrieval(query: str, k: int = 6) -> str:
    corpus = gather_corpus(query, top_sources=3)
    if not corpus:
        return ""
    store = InMemoryVectorStore()
    store.build(corpus)
    hits = store.search(query, k=k)
    if not hits:
        return ""
    lines: List[str] = []
    for i, (chunk, url, score) in enumerate(hits, start=1):
        lines.append(f"---\nSource {i}: {url}\nScore: {score:.3f}\nExtract: {chunk}\n")
    return "\n".join(lines)


