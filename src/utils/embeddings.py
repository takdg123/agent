#!/usr/bin/env python3
"""
Vector helpers for semantic ranking and recall.

Uses the locally installed nomic-embed-text through Ollama, so this adds no
Python dependency.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

EMBED_MODEL = "nomic-embed-text"


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity, 0.0 when either vector is empty or zero-length."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def paper_text_for_embedding(paper: Dict) -> str:
    """The text used to represent a paper as a vector."""
    return f"{paper.get('title', '')}\n\n{paper.get('abstract', '')}".strip()


class CachedProfileEmbedding:
    """
    Caches the interest-profile vector, keyed by a hash of the profile text.

    The profile changes rarely but is compared against every paper, so
    re-embedding it daily is pure waste. Editing the profile changes the hash and
    invalidates the cache automatically.
    """

    def __init__(self, llm, cache_dir: Path, model: str = EMBED_MODEL):
        self.llm = llm
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "profile_embedding.json"

    def get(self, profile_text: str) -> Optional[List[float]]:
        """Return the profile vector, or None if embedding is unavailable."""
        digest = hashlib.sha256(profile_text.encode("utf-8")).hexdigest()[:16]

        if self.cache_file.exists():
            try:
                cached = json.loads(self.cache_file.read_text())
                if cached.get("hash") == digest and cached.get("vector"):
                    return cached["vector"]
            except (ValueError, OSError):
                pass  # a corrupt cache is not worth failing over

        try:
            vector = self.llm.embed(profile_text, model=self.model)
        except Exception as exc:
            print(f"   ⚠️  could not embed interest profile ({exc})")
            return None

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps({"hash": digest, "vector": vector}))
        except OSError as exc:
            print(f"   ⚠️  could not cache profile embedding ({exc})")
        return vector
