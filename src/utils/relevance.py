#!/usr/bin/env python3
"""
Score papers against the reader's interest profile.

Two stages, because they have different costs:

1. Embedding rank - cheap. Orders every candidate by similarity to the profile
   and keeps the top `max_triage`. This decides who gets an LLM call; it is not
   the gate.
2. LLM triage - one call per survivor. This is the gate. It sees the profile,
   the core topics, and the exclusions, and returns a score with a stated reason.

The reason is carried into the report so a wrong rejection is visible rather than
silent. A paper that cannot be scored is kept, not dropped: failing to score is
not evidence of irrelevance.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .embeddings import CachedProfileEmbedding, cosine, paper_text_for_embedding
from .parallel import map_bounded
from .prompt_loader import PromptLoader

DEFAULT_THRESHOLD = 6.0
DEFAULT_MAX_TRIAGE = 15

# Embeddings are small and fast, so more of them can be in flight. Triage runs on
# a 32B model, which degrades if flooded.
EMBED_WORKERS = 8
TRIAGE_WORKERS = 3


def load_profile(path: Path) -> Dict:
    """Load and normalise config/interests.yml."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"interest profile not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not (raw.get("profile") or "").strip():
        raise ValueError(f"{path} has no 'profile' text to match papers against")

    return {
        "profile": raw["profile"].strip(),
        "core": list(raw.get("core") or []),
        "exclude": list(raw.get("exclude") or []),
        "threshold": float(raw.get("threshold", DEFAULT_THRESHOLD)),
        "max_triage": int(raw.get("max_triage", DEFAULT_MAX_TRIAGE)),
    }


def _extract_json(text: str) -> Optional[Dict]:
    """Recover a JSON object from a model response that may include prose."""
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


class RelevanceScorer:
    """Ranks and gates papers against an interest profile"""

    def __init__(self, llm, profile: Dict, cache_dir: Path = None,
                 prompt_dir: Path = None, model: str = None):
        self.llm = llm
        self.profile = profile
        self.model = model
        self.profile_embedding = CachedProfileEmbedding(
            llm, Path(cache_dir) if cache_dir else Path("data/knowledge")
        )
        self.prompts = PromptLoader(
            Path(prompt_dir) if prompt_dir else Path(__file__).parent.parent.parent / "prompts"
        )

    # -- stage 1: cheap ranking -------------------------------------------------

    def rank(self, papers: List[Dict]) -> List[Dict]:
        """
        Order papers by similarity to the profile and keep the top max_triage.

        If embeddings are unavailable the original list is returned untouched, so
        a broken embedder degrades cost, not coverage.
        """
        limit = self.profile["max_triage"]
        if not papers:
            return []

        profile_vector = self.profile_embedding.get(self.profile["profile"])
        if not profile_vector:
            print("   ⚠️  ranking without embeddings; triaging in feed order")
            return papers[:limit]

        # Embedding is cheap per call but there are ~40 of them; sequential
        # round-trips dominated the stage.
        outcomes = map_bounded(
            lambda paper: self.llm.embed(paper_text_for_embedding(paper)),
            papers, workers=EMBED_WORKERS, label="embed",
        )

        scored = []
        for paper, outcome in outcomes:
            if isinstance(outcome, Exception):
                print(f"   ⚠️  could not embed '{paper.get('title', '')[:40]}' ({outcome})")
                similarity = 0.0
            else:
                similarity = cosine(profile_vector, outcome)
            paper["profile_similarity"] = round(similarity, 4)
            scored.append(paper)

        scored.sort(key=lambda p: p["profile_similarity"], reverse=True)
        return scored[:limit]

    # -- stage 2: the actual gate ----------------------------------------------

    def triage(self, paper: Dict) -> Dict:
        """
        Ask the model to score one paper against the profile.

        Returns:
            {score: float|None, topic_tags: [str], why_it_matters: str}
            score is None when the model's answer could not be parsed.
        """
        prompt = self.prompts._load("relevance_triage.txt").format(
            profile=self.profile["profile"],
            core="\n".join(f"- {t}" for t in self.profile["core"]) or "- (none given)",
            exclude="\n".join(f"- {t}" for t in self.profile["exclude"]) or "- (none given)",
            title=paper.get("title", "Unknown"),
            authors=", ".join(paper.get("authors", [])[:5]),
            abstract=(paper.get("abstract") or "")[:2500],
        )

        unscored = {"score": None, "topic_tags": [], "why_it_matters": ""}
        try:
            raw = self.llm.generate(prompt, model=self.model, format="json",
                                    options={"temperature": 0.1})
        except Exception as exc:
            print(f"   ⚠️  triage failed for '{paper.get('title', '')[:40]}' ({exc})")
            return {**unscored, "why_it_matters": "relevance could not be assessed"}

        verdict = _extract_json(raw)
        if not verdict or verdict.get("score") is None:
            print(f"   ⚠️  unparseable triage verdict for '{paper.get('title', '')[:40]}'")
            return {**unscored, "why_it_matters": "relevance could not be assessed"}

        try:
            score = max(0.0, min(10.0, float(verdict["score"])))
        except (TypeError, ValueError):
            return {**unscored, "why_it_matters": "relevance could not be assessed"}

        tags = [str(t) for t in (verdict.get("topic_tags") or [])][:3]
        return {"score": score, "topic_tags": tags,
                "why_it_matters": str(verdict.get("why_it_matters") or "").strip()}

    # -- combined ---------------------------------------------------------------

    def select(self, papers: List[Dict]) -> List[Dict]:
        """
        Rank, triage, and keep papers at or above the threshold.

        Returns papers sorted by descending relevance, each carrying
        relevance_score, topic_tags, and why_it_matters.
        """
        threshold = self.profile["threshold"]
        candidates = self.rank(papers)
        print(f"   🎯 triaging {len(candidates)} of {len(papers)} papers "
              f"(threshold {threshold})")

        outcomes = map_bounded(self.triage, candidates,
                               workers=TRIAGE_WORKERS, label="triage")

        kept, rejected = [], []
        for paper, verdict in outcomes:
            if isinstance(verdict, Exception):
                print(f"   ⚠️  triage error for '{paper.get('title', '')[:40]}' ({verdict})")
                verdict = {"score": None, "topic_tags": [],
                           "why_it_matters": "relevance could not be assessed"}
            paper["relevance_score"] = verdict["score"]
            paper["topic_tags"] = verdict["topic_tags"]
            paper["why_it_matters"] = verdict["why_it_matters"]

            # An unscoreable paper is kept: failure to assess is not a rejection.
            if verdict["score"] is None or verdict["score"] >= threshold:
                kept.append(paper)
            else:
                rejected.append(paper)

        for paper in rejected:
            print(f"      ✗ {paper['relevance_score']:.1f}  {paper.get('title', '')[:60]}"
                  f"\n            {paper['why_it_matters'][:90]}")

        kept.sort(key=lambda p: (p["relevance_score"] is not None,
                                 p["relevance_score"] or 0.0), reverse=True)
        print(f"   ✅ {len(kept)} relevant, {len(rejected)} rejected")
        return kept
