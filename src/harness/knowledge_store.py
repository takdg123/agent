#!/usr/bin/env python3
"""
Accumulated knowledge from past reports.

Replaces MemoryManager, whose recall scored papers by overlap of a flat keyword
list — so nearly every GRB paper matched every other — and whose stored "expert
reviews" were the string "Error: HTTP 404" for all 53 papers.

Two layers:

1. Semantic recall. Every analysed paper is embedded into embeddings.jsonl, so a
   new paper retrieves genuinely similar past work rather than keyword twins.
2. Topic notes. After each run, a running note per topic is updated from that
   day's papers, giving the synthesis a view of how a sub-field is developing
   rather than only isolated neighbours.

This is why the models are not fine-tuned: ~10 papers a day is far too little
text to install facts by gradient descent, retrieval is same-day fresh, and a
recalled paper can be cited and checked.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from ..utils.embeddings import EMBED_MODEL, cosine, paper_text_for_embedding

RECALL_LIMIT = 3
RECALL_MIN_SIMILARITY = 0.6
TOPIC_NOTE_LIMIT = 2
MAX_NOTE_CHARS = 4000


def _slug(topic: str) -> str:
    """Filesystem-safe topic identifier."""
    return re.sub(r"[^a-z0-9]+", "-", str(topic).lower()).strip("-")[:48] or "misc"


class KnowledgeStore:
    """Persistent semantic memory over analysed papers and topics"""

    def __init__(self, data_dir: str = None, llm=None, embed_model: str = EMBED_MODEL):
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.root = self.data_dir / "knowledge"
        self.papers_file = self.root / "embeddings.jsonl"
        self.topics_dir = self.root / "topics"
        self.llm = llm
        self.embed_model = embed_model

        self.topics_dir.mkdir(parents=True, exist_ok=True)

    # -- persistence -----------------------------------------------------------

    def _load_papers(self) -> List[Dict]:
        if not self.papers_file.exists():
            return []
        records = []
        for line in self.papers_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue  # one bad line must not lose the whole store
        return records

    def _embed(self, text: str):
        if not self.llm or not text.strip():
            return None
        try:
            return self.llm.embed(text, model=self.embed_model)
        except Exception as exc:
            print(f"      ⚠️  could not embed for knowledge store ({exc})")
            return None

    # -- writing ---------------------------------------------------------------

    def record(self, paper: Dict, analysis: Dict) -> bool:
        """
        Store a paper's findings for future recall.

        Returns True if a record was written.
        """
        arxiv_id = paper.get("arxiv_id") or paper.get("title", "")[:40]
        if not arxiv_id:
            return False

        existing = self._load_papers()
        if any(r.get("arxiv_id") == arxiv_id for r in existing):
            return False  # already known

        vector = self._embed(paper_text_for_embedding(paper))
        record = {
            "arxiv_id": arxiv_id,
            "title": paper.get("title", ""),
            "date": datetime.now().isoformat(timespec="seconds"),
            "topic_tags": analysis.get("topic_tags") or [],
            "relevance_score": analysis.get("relevance_score"),
            "key_numbers": analysis.get("key_numbers") or [],
            "findings": (analysis.get("english") or "")[:1200],
            "vector": vector or [],
        }

        self.root.mkdir(parents=True, exist_ok=True)
        with self.papers_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True

    def update_topic_notes(self, entries: List[Dict], llm=None, model: str = None) -> List[str]:
        """
        Refresh the running note for each topic touched by this run.

        Notes are condensed by an LLM when available, and otherwise grown by
        append-and-trim, so the store still works if the model is down.
        """
        client = llm or self.llm
        by_topic: Dict[str, List[Dict]] = {}
        for entry in entries:
            analysis = entry.get("analysis", {})
            for tag in (analysis.get("topic_tags") or ["general"]):
                by_topic.setdefault(_slug(tag), []).append(entry)

        updated = []
        for slug, topic_entries in by_topic.items():
            note_file = self.topics_dir / f"{slug}.md"
            previous = note_file.read_text(encoding="utf-8") if note_file.exists() else ""

            today = datetime.now().strftime("%Y-%m-%d")
            additions = "\n".join(
                f"- {e.get('paper', {}).get('title', 'Untitled')} "
                f"({e.get('paper', {}).get('arxiv_id', 'n/a')}): "
                f"{(e.get('analysis', {}).get('english') or '')[:200].strip()}"
                for e in topic_entries
            )
            appended = f"{previous}\n\n## {today}\n{additions}".strip()

            note = self._condense(slug, appended, client, model) if client else appended
            note_file.write_text(note[:MAX_NOTE_CHARS], encoding="utf-8")
            updated.append(slug)
        return updated

    def _condense(self, slug: str, note: str, llm, model: str) -> str:
        """Ask the model to keep the note current and bounded."""
        if len(note) <= MAX_NOTE_CHARS // 2:
            return note
        prompt = (
            f"Below is a running research note on the topic '{slug}', built up from "
            f"daily paper summaries.\n\nRewrite it as a current state-of-the-field "
            f"note under 350 words. Keep concrete findings, numbers, and open "
            f"questions. Merge duplicates. Drop redundancy. Preserve arXiv IDs for "
            f"the papers you mention. Output only the note.\n\n{note[:8000]}"
        )
        try:
            return llm.generate(prompt, model=model)
        except Exception as exc:
            print(f"      ⚠️  could not condense topic note '{slug}' ({exc})")
            return note

    # -- reading ---------------------------------------------------------------

    def recall(self, paper: Dict) -> Dict[str, Any]:
        """
        Retrieve context for analysing a paper.

        Returns:
            {similar: [...], topic_notes: [...], has_history: bool}
        """
        vector = self._embed(paper_text_for_embedding(paper))
        similar = []

        if vector:
            scored = []
            for record in self._load_papers():
                if record.get("arxiv_id") == paper.get("arxiv_id"):
                    continue
                similarity = cosine(vector, record.get("vector") or [])
                if similarity >= RECALL_MIN_SIMILARITY:
                    scored.append((similarity, record))
            scored.sort(key=lambda pair: pair[0], reverse=True)
            similar = [
                {"title": r["title"], "arxiv_id": r.get("arxiv_id", ""),
                 "findings": r.get("findings", ""), "similarity": round(s, 3)}
                for s, r in scored[:RECALL_LIMIT]
            ]

        notes = []
        for tag in (paper.get("topic_tags") or [])[:TOPIC_NOTE_LIMIT]:
            note_file = self.topics_dir / f"{_slug(tag)}.md"
            if note_file.exists():
                notes.append({"topic": tag,
                              "note": note_file.read_text(encoding="utf-8")[:1500]})

        return {"similar": similar, "topic_notes": notes,
                "has_history": bool(similar or notes)}

    def as_context_lines(self, recalled: Dict[str, Any]) -> List[str]:
        """Render recall output as prompt lines for the expert agents."""
        lines = []
        for item in recalled.get("similar", []):
            lines.append(f"- Previously analysed ({item['arxiv_id']}, similarity "
                         f"{item['similarity']}): {item['title']} — "
                         f"{item['findings'][:200].strip()}")
        for note in recalled.get("topic_notes", []):
            lines.append(f"- Running note on {note['topic']}:\n{note['note']}")
        return lines

    # -- housekeeping ----------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        records = self._load_papers()
        return {
            "total_papers": len(records),
            "embedded_papers": sum(1 for r in records if r.get("vector")),
            "topics": len(list(self.topics_dir.glob("*.md"))),
            "newest": records[-1]["date"] if records else None,
        }

    def prune(self, days: int = 365) -> int:
        """Drop records older than `days`. Returns the number removed."""
        records = self._load_papers()
        cutoff = datetime.now() - timedelta(days=days)
        kept = []
        for record in records:
            try:
                if datetime.fromisoformat(record["date"]) >= cutoff:
                    kept.append(record)
            except (KeyError, ValueError):
                kept.append(record)  # keep anything we cannot date

        if len(kept) != len(records):
            self.papers_file.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept),
                encoding="utf-8",
            )
        return len(records) - len(kept)
