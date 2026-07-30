#!/usr/bin/env python3
"""
Extract the parts of a paper that carry its findings.

Analyses were previously built from abstract[:1500], which is why summaries
described what a paper was about rather than what it found. This module fetches
the PDF and pulls introduction, results, and conclusions.

Everything degrades rather than raising: a paper with an unreadable PDF still
gets analysed from its abstract, flagged via the 'source' field.
"""

import re
from pathlib import Path
from typing import Dict, Optional

import httpx

USER_AGENT = "torri/1.0 (research digest; takdg123@gmail.com)"

# Ordered because a paper's real structure follows this order; the splitter uses
# the position of the *next* heading to bound each section.
_HEADING_PATTERNS = {
    "introduction": r"introduction|motivation",
    "methods": r"observations?|data\s+reduction|methods?|methodology|simulations?|"
               r"numerical\s+set-?up|sample\s+selection",
    "results": r"results?|analysis|light\s+curves?|spectral\s+analysis|measurements?",
    "discussion": r"discussion|interpretation|implications?",
    "conclusions": r"conclusions?|summary|summary\s+and\s+conclusions?|concluding\s+remarks",
}

# Everything from here on is not content we want in a prompt.
_TAIL_KEYWORDS = (r"acknowledge?ments?|acknowledgments?|references|bibliography|"
                  r"appendix|appendices|data\s+availability|supplementary")

# A tail heading must *begin* with the keyword. Matching it anywhere let a table
# note reading "References. (1) This work; (2) ..." truncate a whole paper,
# silently discarding its results and conclusions.
_TAIL_START = re.compile(rf"^(?:{_TAIL_KEYWORDS})\b", re.I)

# Back-matter never starts in the opening third of a paper; this guards against
# any remaining false positive doing catastrophic damage.
_TAIL_MIN_FRACTION = 0.3

# Real headings are rarely a bare keyword ("Observations and Data Reduction",
# "Summary and Conclusions"), so a candidate line is recognised by shape - short,
# few words, no terminating period - and then classified by keyword.
# A Roman-numeral prefix must carry punctuation, otherwise the leading letters of
# INTRODUCTION and CONCLUSIONS are stripped as numerals.
_NUM_PREFIX = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?|[IVXLC]+[.)])\s*")
_MAX_HEADING_CHARS = 60
_MAX_HEADING_WORDS = 6

# Discussion is merged into conclusions: both carry takeaways. Methods stays
# separate because the synthesis prompt asks about instruments and approach.
_MERGE_INTO = {"discussion": "conclusions"}

_BODY_SECTIONS = ("introduction", "methods", "results", "conclusions")

DEFAULT_MAX_CHARS = 12000


def _is_heading_shaped(stripped: str) -> bool:
    """A heading is short, few-worded, and not a sentence."""
    if not stripped or len(stripped) > _MAX_HEADING_CHARS or stripped.endswith("."):
        return False
    core = _NUM_PREFIX.sub("", stripped).strip().rstrip(":").strip()
    return len(core) >= 3 and len(core.split()) <= _MAX_HEADING_WORDS


def _truncate_tail(text: str) -> str:
    """Drop acknowledgements, references, and appendices."""
    floor = int(len(text) * _TAIL_MIN_FRACTION)
    position = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if (position >= floor and _is_heading_shaped(stripped)
                and _TAIL_START.match(_NUM_PREFIX.sub("", stripped))):
            return text[:position]
        position += len(line)
    return text


def _classify_heading(line: str) -> Optional[str]:
    """Return the canonical section name for a heading line, or None."""
    stripped = line.strip()
    if not _is_heading_shaped(stripped):
        return None

    core = _NUM_PREFIX.sub("", stripped).strip().rstrip(":").strip()

    # A heading naming two sections ("Results and Discussion") belongs to
    # whichever keyword appears first.
    best = None
    for name, alternatives in _HEADING_PATTERNS.items():
        match = re.search(rf"\b(?:{alternatives})\b", core, re.I)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), name)
    return best[1] if best else None


def _find_headings(text: str):
    """Locate section headings as (line_start, content_start, canonical_name)."""
    found = []
    position = 0
    for line in text.splitlines(keepends=True):
        name = _classify_heading(line)
        if name:
            found.append((position, position + len(line), name))
        position += len(line)
    return found


def split_sections(text: str) -> Dict[str, str]:
    """
    Split paper text into introduction, methods, results, and conclusions.

    Falls back to head and tail slices when no headings can be identified, which
    in practice still captures motivation and takeaways.
    """
    empty = {name: "" for name in _BODY_SECTIONS}
    if not text or not text.strip():
        return empty

    body = _truncate_tail(text)
    headings = _find_headings(body)

    sections = dict(empty)
    if headings:
        for index, (_, content_start, name) in enumerate(headings):
            content_end = headings[index + 1][0] if index + 1 < len(headings) else len(body)
            chunk = body[content_start:content_end].strip()
            if not chunk:
                continue
            target = _MERGE_INTO.get(name, name)
            sections[target] = f"{sections[target]}\n\n{chunk}".strip() if sections[target] else chunk

    if any(sections.values()):
        return sections

    # No usable headings: take the opening and the closing of the paper.
    slice_size = 6000
    stripped = body.strip()
    if len(stripped) <= slice_size:
        return {**empty, "introduction": stripped}
    return {**empty,
            "introduction": stripped[:slice_size].strip(),
            "conclusions": stripped[-slice_size:].strip()}


def _pdf_to_text(data: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    import fitz

    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def _fetch_pdf(paper: Dict, cache_dir: Path) -> bytes:
    """Return PDF bytes, using the on-disk cache when present."""
    arxiv_id = paper.get("arxiv_id", "")
    cached = cache_dir / f"{arxiv_id.replace('/', '_')}.pdf" if arxiv_id else None
    if cached and cached.exists() and cached.stat().st_size > 1000:
        return cached.read_bytes()

    url = paper.get("pdf_url") or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "")
    if not url:
        raise OSError("no PDF url for paper")

    response = httpx.get(url, timeout=60, follow_redirects=True,
                         headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    data = response.content
    if not data.startswith(b"%PDF"):
        raise OSError(f"response from {url} is not a PDF")

    if cached:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    return data


# Findings matter more than framing when the context budget binds.
_SECTION_WEIGHTS = {"conclusions": 3, "results": 3, "introduction": 2, "methods": 1}


def _cap(sections: Dict[str, str], max_chars: int) -> Dict[str, str]:
    """
    Bound total prompt size, weighted towards findings.

    A local 32B model slows sharply with context length, so this is a real
    constraint rather than a formality. Sections needing less than their share
    release the remainder to the others, so the budget is not left unused when a
    paper lacks a section.
    """
    lengths = {name: len(sections.get(name) or "") for name in _BODY_SECTIONS}
    allocation = {name: 0 for name in _BODY_SECTIONS}
    pending = [name for name in _BODY_SECTIONS if lengths[name]]

    for _ in range(len(_BODY_SECTIONS)):
        budget = max_chars - sum(allocation.values())
        if not pending or budget <= 0:
            break
        total_weight = sum(_SECTION_WEIGHTS[name] for name in pending)
        satisfied = []
        for name in pending:
            share = budget * _SECTION_WEIGHTS[name] // total_weight
            allocation[name] += min(lengths[name] - allocation[name], share)
            if allocation[name] >= lengths[name]:
                satisfied.append(name)
        if not satisfied:
            break  # every section is truncated; no remainder to redistribute
        pending = [name for name in pending if name not in satisfied]

    return {name: (sections.get(name) or "")[: allocation[name]].strip()
            for name in _BODY_SECTIONS}


def extract(paper: Dict, cache_dir: Optional[Path] = None,
            max_chars: int = DEFAULT_MAX_CHARS) -> Dict[str, str]:
    """
    Extract the analysable contents of a paper.

    Returns:
        {abstract, introduction, results, conclusions, source} where source is
        'pdf' on success or 'abstract' when the PDF could not be used.
    """
    cache_dir = Path(cache_dir) if cache_dir else Path("data/pdfs")
    abstract = (paper.get("abstract") or "").strip()
    degraded = {"abstract": abstract, "source": "abstract",
                **{name: "" for name in _BODY_SECTIONS}}

    try:
        data = _fetch_pdf(paper, cache_dir)
        text = _pdf_to_text(data)
    except Exception as exc:  # network, parse, or missing dependency
        print(f"      ⚠️  full text unavailable ({exc}); using abstract only")
        return degraded

    if not text or not text.strip():
        print("      ⚠️  PDF yielded no text; using abstract only")
        return degraded

    sections = _cap(split_sections(text), max_chars)
    if not any(sections.values()):
        return degraded

    return {"abstract": abstract, "source": "pdf", **sections}


def as_prompt_context(extracted: Dict[str, str]) -> str:
    """Render extracted sections as labelled prompt text, skipping empty ones."""
    labels = [("Abstract", "abstract"), ("Introduction", "introduction"),
              ("Methods", "methods"), ("Results", "results"),
              ("Conclusions", "conclusions")]
    parts = [f"{label}:\n{extracted[key].strip()}"
             for label, key in labels if (extracted.get(key) or "").strip()]
    return "\n\n".join(parts)
