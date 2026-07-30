#!/usr/bin/env python3
"""
Mobile-first HTML report generator.

Design constraints, in order of priority:

1. Never emit unescaped model output. All text goes through latex_to_html.convert,
   which escapes HTML before rendering math. Raw '<' inside LaTeX previously made
   the browser discard the rest of a paragraph.
2. Readable on a phone. Single fluid column, no fixed wide padding, no justified
   text, 16px minimum body size.
3. Survive an email client. No JavaScript, no external resources. Critical layout
   properties are inlined as well as declared in <style>, because some clients
   drop embedded stylesheets. <details> degrades to always-expanded where the
   toggle is unsupported, which is acceptable - content stays visible.

Card order is verdict-first: score, why it matters, key numbers, then the long
text collapsed underneath, so a paper can be judged without reading it.
"""

from datetime import datetime
from typing import Any, Dict, List

from .latex_to_html import convert

# Palette. Kept muted so the report reads as a document, not a dashboard.
INK = "#1f2933"
MUTED = "#6b7280"
LINE = "#e5e7eb"
ACCENT = "#3457a6"
WASH = "#f7f8fa"

BODY_FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', "
             "'Apple SD Gothic Neo', 'Malgun Gothic', Roboto, sans-serif")

# Inline fallbacks for clients that strip <style>.
_S = {
    "card": f"border:1px solid {LINE};border-radius:10px;padding:16px;margin:0 0 20px 0;background:#fff;",
    "title": f"font-size:18px;line-height:1.35;font-weight:600;color:{INK};margin:0 0 6px 0;",
    "meta": f"font-size:14px;color:{MUTED};margin:0 0 14px 0;line-height:1.5;",
    "label": f"font-size:12px;font-weight:700;letter-spacing:.06em;color:{MUTED};margin:0 0 4px 0;",
    "why": f"font-size:16px;line-height:1.5;color:{INK};margin:0 0 14px 0;",
    "panel": f"background:{WASH};border-radius:8px;padding:12px 14px;margin:0 0 14px 0;",
    "prose": f"font-size:16px;line-height:1.7;color:{INK};",
    "summary": f"font-size:15px;font-weight:600;color:{ACCENT};cursor:pointer;padding:10px 0;",
    "badge": "display:inline-block;font-size:13px;font-weight:700;padding:3px 9px;border-radius:20px;",
    "tag": f"display:inline-block;font-size:12px;color:{MUTED};border:1px solid {LINE};border-radius:20px;padding:2px 8px;margin:0 4px 4px 0;",
}

CSS = f"""
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:0; background:{WASH}; color:{INK};
         font-family:{BODY_FONT}; font-size:16px; line-height:1.6;
         -webkit-text-size-adjust:100%; }}
  .wrap {{ max-width:680px; margin:0 auto; padding:12px; }}
  .head {{ background:{ACCENT}; color:#fff; border-radius:10px; padding:20px 16px; margin-bottom:16px; }}
  .head h1 {{ margin:0 0 6px 0; font-size:21px; font-weight:600; }}
  .head p {{ margin:0; font-size:14px; opacity:.92; }}
  .card {{ {_S['card']} }}
  .t {{ {_S['title']} }}
  .meta {{ {_S['meta']} }}
  .meta a {{ color:{ACCENT}; }}
  .lbl {{ {_S['label']} }}
  .why {{ {_S['why']} }}
  .panel {{ {_S['panel']} }}
  .prose {{ {_S['prose']} }}
  .prose p {{ margin:0 0 12px 0; }}
  .prose ul {{ margin:0 0 12px 0; padding-left:22px; }}
  .prose li {{ margin:0 0 6px 0; }}
  .nums {{ margin:0; padding-left:20px; font-size:15px; line-height:1.7; }}
  details {{ border-top:1px solid {LINE}; }}
  summary {{ {_S['summary']} }}
  .foot {{ color:{MUTED}; font-size:13px; text-align:center; padding:16px 8px 24px; }}
  /* Wider screens get more breathing room; narrow is the default. */
  @media (min-width:560px) {{
    .wrap {{ padding:24px; }}
    .card {{ padding:22px; }}
    .head {{ padding:28px 24px; }}
    .head h1 {{ font-size:25px; }}
  }}
"""


def _prose(text: Any) -> str:
    """Render model text: escape + convert math, then light markdown."""
    body = convert(text)
    if not body.strip():
        return ""

    html = []
    for block in [b for b in body.split("\n\n") if b.strip()]:
        lines = [ln.strip() for ln in block.strip().split("\n") if ln.strip()]
        if lines and all(ln.startswith(("- ", "* ", "• ")) for ln in lines):
            items = "".join(f"<li>{_emphasis(ln[2:].strip())}</li>" for ln in lines)
            html.append(f"<ul>{items}</ul>")
        else:
            html.append(f"<p>{_emphasis(' '.join(lines))}</p>")
    return "".join(html)


def _emphasis(text: str) -> str:
    """**bold** -> <strong>. Applied after escaping, so it cannot inject markup."""
    parts = text.split("**")
    if len(parts) < 3:
        return text
    out = []
    for i, part in enumerate(parts):
        out.append(f"<strong>{part}</strong>" if i % 2 else part)
    return "".join(out)


def _authors(paper: Dict) -> str:
    names = paper.get("authors") or []
    if not names:
        return "Unknown authors"
    shown = ", ".join(convert(n) for n in names[:4])
    return f"{shown} <em>et al.</em>" if len(names) > 4 else shown


class HTMLReportGenerator:
    """Generates the daily digest as self-contained, email-safe HTML"""

    @staticmethod
    def _score_badge(analysis: Dict) -> str:
        """Relevance if scored, else the critic's quality score, else nothing."""
        score = analysis.get("relevance_score")
        if score is not None:
            bg, fg = ("#e7f3ea", "#1d6b38") if score >= 8 else \
                     ("#fdf3e0", "#8a5a12") if score >= 6 else ("#fbe9e9", "#8c2f2f")
            return (f'<span class="badge" style="{_S["badge"]}background:{bg};color:{fg};">'
                    f'{score:.1f} relevance</span>')

        quality = analysis.get("quality_score")
        if quality is not None:
            return (f'<span class="badge" style="{_S["badge"]}background:{WASH};color:{MUTED};">'
                    f'quality {quality:.1f}/10</span>')
        return ""

    @classmethod
    def generate_paper_section(cls, index: int, paper: Dict, analysis: Dict,
                               show_expert_reviews: bool = False) -> str:
        """Generate one verdict-first paper card"""
        parts = [f'<div class="card" style="{_S["card"]}">']

        badge = cls._score_badge(analysis)
        tags = "".join(
            f'<span class="tag" style="{_S["tag"]}">{convert(t)}</span>'
            for t in (analysis.get("topic_tags") or [])
        )
        if badge or tags:
            parts.append(f'<div style="margin:0 0 10px 0;">{badge} {tags}</div>')

        parts.append(f'<div class="t" style="{_S["title"]}">{index}. {convert(paper.get("title", "Untitled"))}</div>')

        arxiv_id = paper.get("arxiv_id", "")
        link = (f' &middot; <a href="https://arxiv.org/abs/{arxiv_id}" '
                f'style="color:{ACCENT};">arXiv:{arxiv_id}</a>') if arxiv_id else ""
        parts.append(f'<div class="meta" style="{_S["meta"]}">{_authors(paper)}{link}</div>')

        why = analysis.get("why_it_matters")
        if why:
            parts.append(f'<div class="lbl" style="{_S["label"]}">WHY THIS MATTERS</div>')
            parts.append(f'<div class="why" style="{_S["why"]}">{convert(why)}</div>')

        numbers = analysis.get("key_numbers") or []
        if numbers:
            items = "".join(f"<li>{convert(n)}</li>" for n in numbers)
            parts.append(f'<div class="panel" style="{_S["panel"]}">'
                         f'<div class="lbl" style="{_S["label"]}">KEY NUMBERS</div>'
                         f'<ul class="nums">{items}</ul></div>')

        for label, text in (
            ("Abstract", paper.get("abstract")),
            ("Analysis (English)", analysis.get("english")),
            ("한국어 분석", analysis.get("korean")),
        ):
            rendered = _prose(text)
            if rendered:
                parts.append(
                    f"<details><summary style=\"{_S['summary']}\">{label}</summary>"
                    f"<div class=\"prose\" style=\"{_S['prose']}\">{rendered}</div></details>"
                )

        parts.append("</div>")
        return "".join(parts)

    @classmethod
    def generate_header(cls, title: str, subtitle: str, date: datetime,
                        paper_count: int, expert_count: int = 0) -> str:
        """Generate report header"""
        noun = "paper" if paper_count == 1 else "papers"
        return (f'<div class="head">'
                f"<h1>{convert(title)}</h1>"
                f"<p>{convert(subtitle)}</p>"
                f'<p style="margin-top:6px;">{date.strftime("%A, %d %B %Y")} '
                f"&middot; {paper_count} {noun}</p></div>")

    @classmethod
    def generate_footer(cls, metadata: Dict[str, Any]) -> str:
        """Generate report footer"""
        note = convert(metadata.get("description", "AI-assisted research digest"))
        return (f'<div class="foot"><p style="margin:0 0 4px 0;">TORRI &middot; {note}</p>'
                f'<p style="margin:0;">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} KST</p></div>')

    @classmethod
    def generate_full_report(cls, papers_analysis: List[Dict],
                             title: str = "TORRI Research Digest",
                             subtitle: str = "High-Energy Astrophysics",
                             expert_count: int = 0,
                             metadata: Dict = None) -> str:
        """
        Generate the complete HTML report.

        Args:
            papers_analysis: List of {paper: Dict, analysis: Dict}. Optional
                analysis keys (relevance_score, topic_tags, why_it_matters,
                key_numbers) render only when present.

        Returns:
            Complete, self-contained HTML string
        """
        today = datetime.now()
        cards = "".join(
            cls.generate_paper_section(i, entry.get("paper", {}), entry.get("analysis", {}))
            for i, entry in enumerate(papers_analysis, 1)
        )
        if not cards:
            cards = (f'<div class="card" style="{_S["card"]}">'
                     f'<div class="prose" style="{_S["prose"]}">'
                     f"<p>No relevant papers today.</p></div></div>")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{convert(title)} - {today.strftime('%Y-%m-%d')}</title>
<style>{CSS}</style>
</head>
<body style="margin:0;padding:0;background:{WASH};color:{INK};font-family:{BODY_FONT};font-size:16px;line-height:1.6;">
<div class="wrap" style="max-width:680px;margin:0 auto;padding:12px;">
{cls.generate_header(title, subtitle, today, len(papers_analysis), expert_count)}
{cards}
{cls.generate_footer(metadata or {})}
</div>
</body>
</html>
"""
