#!/usr/bin/env python3
"""
Pull the headline quantitative results out of a paper.

These sit at the top of each report card so a paper can be judged without
reading the prose. Extraction is deliberately a separate, narrow call rather than
part of the synthesis: asking one model call to both write an essay and emit
structured data degrades both.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .paper_text import as_prompt_context
from .prompt_loader import PromptLoader

MAX_ENTRIES = 5
MAX_ENTRY_CHARS = 80


def _extract_json(text: str) -> Optional[Dict]:
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


def extract(llm, paper: Dict, model: str = None,
            prompt_dir: Path = None) -> List[str]:
    """
    Extract 0-5 key quantitative results for a paper.

    Returns an empty list on any failure: missing numbers degrade the card,
    whereas invented numbers would make the report untrustworthy.
    """
    contents = paper.get("contents")
    body = as_prompt_context(contents) if contents else (paper.get("abstract") or "")
    if not body.strip():
        return []

    prompts = PromptLoader(
        Path(prompt_dir) if prompt_dir else Path(__file__).parent.parent.parent / "prompts"
    )
    prompt = prompts._load("key_numbers.txt").format(
        title=paper.get("title", "Unknown"),
        contents=body[:8000],
    )

    try:
        raw = llm.generate(prompt, model=model, format="json",
                           options={"temperature": 0.1})
    except Exception as exc:
        print(f"      ⚠️  key numbers unavailable ({exc})")
        return []

    parsed = _extract_json(raw)
    if not parsed:
        return []

    entries = []
    for item in parsed.get("key_numbers") or []:
        text = str(item).strip()
        # A "number" with no digit in it is prose the model slipped in.
        if text and any(ch.isdigit() for ch in text):
            entries.append(text[:MAX_ENTRY_CHARS])
        if len(entries) >= MAX_ENTRIES:
            break
    return entries
