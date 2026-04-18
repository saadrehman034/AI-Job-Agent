"""
app/memory/vector_store.py
Memory Module — FAISS-based semantic memory for past applications.

Enables the system to:
- Retrieve similar past job applications as context for current run
- Learn which resume strategies worked (based on feedback signals)
- Avoid repeating mistakes on similar roles
"""
from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not installed — memory module will use stub mode")

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    logger.warning("sentence-transformers not installed — using keyword fallback")


class VectorMemoryStore:
    """
    Semantic vector store for application memory.

    Stores embeddings of past job descriptions + outcomes so the system
    can retrieve contextually similar past applications when processing a new one.
    """

    EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension

    def __init__(self):
        self.index_path = Path(os.getenv("FAISS_INDEX_PATH", "./data/faiss_index"))
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_path / "applications.index"
        self.meta_file = self.index_path / "applications_meta.pkl"

        self.index: Optional[object] = None
        self.metadata: list[dict] = []

        self._load_model()
        self._load_index()

    def _load_model(self):
        """Load embedding model (lazy — only if SBERT available)."""
        if SBERT_AVAILABLE:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("[Memory] Embedding model loaded: all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"[Memory] Could not load embedding model: {e}")
                self.model = None
        else:
            self.model = None

    def _load_index(self):
        """Load existing FAISS index from disk if available."""
        if not FAISS_AVAILABLE:
            return

        if self.index_file.exists() and self.meta_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.meta_file, "rb") as f:
                    self.metadata = pickle.load(f)
                logger.info(f"[Memory] Loaded index with {len(self.metadata)} entries")
            except Exception as e:
                logger.warning(f"[Memory] Failed to load index: {e} — starting fresh")
                self._init_index()
        else:
            self._init_index()

    def _init_index(self):
        """Initialize a new FAISS flat inner-product index."""
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(self.EMBEDDING_DIM)
            self.metadata = []
            logger.info("[Memory] Initialized new FAISS index")

    def _embed(self, text: str) -> Optional[np.ndarray]:
        """Convert text to embedding vector."""
        if self.model is None:
            return None
        try:
            vec = self.model.encode([text], normalize_embeddings=True)
            return vec.astype(np.float32)
        except Exception as e:
            logger.warning(f"[Memory] Embedding failed: {e}")
            return None

    def store_application(
        self,
        application_id: str,
        job_description: str,
        job_title: str,
        company: str,
        match_score: int,
        outcome: str = "pending",
        resume_strategy_notes: str = "",
    ) -> bool:
        """Store a new application in vector memory."""
        if not FAISS_AVAILABLE or self.index is None:
            logger.debug("[Memory] FAISS unavailable — skipping vector store")
            return False

        vec = self._embed(job_description)
        if vec is None:
            return False

        self.index.add(vec)
        self.metadata.append({
            "application_id": application_id,
            "job_title": job_title,
            "company": company,
            "match_score": match_score,
            "outcome": outcome,
            "resume_strategy_notes": resume_strategy_notes,
        })

        self._save_index()
        logger.info(f"[Memory] Stored application {application_id} ({job_title} @ {company})")
        return True

    def retrieve_similar(
        self,
        job_description: str,
        top_k: int = 3,
    ) -> list[dict]:
        """
        Retrieve top-k most similar past applications.
        Returns list of metadata dicts sorted by similarity.
        """
        if not FAISS_AVAILABLE or self.index is None or len(self.metadata) == 0:
            return []

        vec = self._embed(job_description)
        if vec is None:
            return []

        try:
            k = min(top_k, len(self.metadata))
            distances, indices = self.index.search(vec, k)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx >= 0 and idx < len(self.metadata):
                    entry = dict(self.metadata[idx])
                    entry["similarity"] = float(dist)
                    results.append(entry)
            return results
        except Exception as e:
            logger.warning(f"[Memory] Retrieval failed: {e}")
            return []

    def update_outcome(self, application_id: str, outcome: str) -> bool:
        """Update the outcome of a past application (for feedback loop)."""
        for entry in self.metadata:
            if entry["application_id"] == application_id:
                entry["outcome"] = outcome
                self._save_index()
                logger.info(f"[Memory] Updated outcome for {application_id}: {outcome}")
                return True
        return False

    def format_context_for_agent(self, similar_apps: list[dict]) -> str:
        """Format retrieved similar applications as context string for agents."""
        if not similar_apps:
            return ""
        lines = ["Similar past applications (for context):"]
        for app in similar_apps:
            outcome_str = f"Outcome: {app.get('outcome', 'pending')}"
            score_str = f"Match score: {app.get('match_score', '?')}%"
            lines.append(
                f"  • {app.get('job_title')} @ {app.get('company')} | "
                f"{score_str} | {outcome_str}"
            )
            if app.get("resume_strategy_notes"):
                lines.append(f"    Notes: {app['resume_strategy_notes']}")
        return "\n".join(lines)

    def _save_index(self):
        """Persist index and metadata to disk."""
        if FAISS_AVAILABLE and self.index is not None:
            try:
                faiss.write_index(self.index, str(self.index_file))
                with open(self.meta_file, "wb") as f:
                    pickle.dump(self.metadata, f)
            except Exception as e:
                logger.error(f"[Memory] Failed to save index: {e}")

    def get_stats(self) -> dict:
        """Return memory store statistics."""
        outcomes = {}
        for entry in self.metadata:
            o = entry.get("outcome", "pending")
            outcomes[o] = outcomes.get(o, 0) + 1
        return {
            "total_applications": len(self.metadata),
            "outcomes": outcomes,
            "faiss_available": FAISS_AVAILABLE,
            "sbert_available": SBERT_AVAILABLE,
        }
