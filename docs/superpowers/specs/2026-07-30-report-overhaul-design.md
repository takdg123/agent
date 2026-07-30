# TORRI Report Overhaul — Design

**Date:** 2026-07-30
**Status:** Approved
**Branch:** `report-overhaul`

## Problem

The daily digest has five user-reported defects:

1. The report is hard to read.
2. It is not usable on a phone.
3. Content is often not relevant to the reader's expertise.
4. The abstract is missing, and the English and Korean summaries say different
   things. Neither is built from the paper's contents.
5. The system does not accumulate knowledge from recent reports.

## Root causes found in the code

These were verified against `data/reports/`, `data/memory/`, and
`logs/daily_report_20260730_090001.log`, not inferred.

### The two astronomy experts have never run

`.env` sets `ASTRO_EXPERT_MODEL=astrosage:70b-q4_K_M`. The installed Ollama
model is `hf.co/mradermacher/AstroSage-70B-i1-GGUF:Q4_K_M`. Ollama returns
`{"error":"model 'astrosage:70b-q4_K_M' not found"}`.

`LLMClient.generate()` returns the *string* `"Error: HTTP 404"` on failure
(`src/utils/llm_client.py:55`). `GRBExpertAgent.execute()` and
`KilonovaExpertAgent.execute()` treat any returned string as a successful
review and report `success=True`. The log shows these tasks "completing
successfully in 0.00s". All 53 paper files in `data/memory/` contain exactly
two occurrences of `Error: HTTP 404` — the GRB and kilonova expert reviews.

Consequence: the "6-expert" pipeline is Qwen-32B paraphrasing a truncated
abstract, with no domain expertise in the loop. This is the primary cause of
defect 3, and a large part of defect 1.

### Unescaped model output silently truncates the report

No component escapes model output before interpolating it into HTML
(`html_report_generator.py:70,75`). Today's report contains the raw text
`redshift \(z < 10\) and luminosity ...`. The browser parses `< 10\) and ...`
as a tag and discards it. The rendered paper ends mid-sentence at "with
redshift \(z". LaTeX is also never converted, so `$8.0 \times 10^{-5}$`
renders literally.

### Relevance filtering is a three-valued keyword match

`PaperFilter.calculate_relevance()` returns only 2.0, 1.0, or 0.0. Any paper
containing the substring "grb" scores maximal. There is no ordering within a
tier and no representation of the reader's interests. Recent reports therefore
included AGN unification models, a PKS 0805−07 blazar QPO, an NRSur7dq4 BBH
waveform surrogate, and warm-dark-matter cosmology bounds.

### English and Korean are generated independently, in the wrong order

Current order in `expert_harness.analyze_paper_multi_expert()`:
synthesis → Korean translation → critic → writer polishes both.

The writer rewrites the English *after* the Korean was already derived from the
pre-polish draft, so the two texts have different parents. The Korean prompt
(`prompts/language_expert.txt`) also asks for an independent 150-200 character
summary rather than a translation, and the writer's output is recovered with a
brittle regex (`expert_harness.py:224`). Observed results: `(194자)` and
`(195자)` leaking into the report body, and "black hole" rendered as 흑점
(sunspot) and 흑홀.

Both languages see at most `abstract[:1500]`. The abstract itself is never
shown in the report.

### Memory is keyword-based and stores failures

`MemoryManager.get_similar_papers()` scores by overlap of the same flat keyword
list, so nearly every GRB paper matches every other. `previous_analysis` is
passed as a Python list into a prompt expecting a string
(`expert_harness.py:90`). The stored "expert reviews" are the 404 strings.

## Decisions

Confirmed with the user on 2026-07-30:

| Question | Decision |
|---|---|
| Relevance mechanism | Prose interest profile → embedding similarity → LLM triage gate |
| Analysis depth | Abstract + introduction + results + conclusions, extracted from the PDF |
| EN/KO parity | Write English, then strict-translate to Korean |
| Layout | Verdict-first card, details collapsed |
| Knowledge update | Topic notes + embedding recall (retrieval, not fine-tuning) |
| Existing memory | Archive and rebuild |

### Why not fine-tune AstroSage

The user asked whether the model itself could be updated instead. It cannot,
practically:

- The installed model is a Q4_K_M GGUF — an inference-only format. Training
  requires the bf16 base (~140 GB), then requantization.
- QLoRA on a 70B places ~35-40 GB of 4-bit weights on the GPU before
  activations, gradients, and optimizer state. A single 48 GB A6000 is marginal
  at best, and the GPU is needed for the daily run.
- ~10 papers/day is ~3,600/year. That is far too little text to install facts
  by gradient descent; it shifts style and risks eroding the astronomy
  knowledge that makes AstroSage useful. Recency is a retrieval problem.

Retrieval also stays auditable: the report can show which past papers informed
an analysis.

## Architecture

New and rewritten units, each with one responsibility:

```
config/interests.yml          (new)      reader's profile + exclusions
src/utils/embeddings.py       (new)      nomic-embed-text client + cosine
src/utils/relevance.py        (new)      profile match → LLM triage → score
src/utils/paper_text.py       (new)      PDF fetch → section extraction
src/utils/latex_to_html.py    (new)      LaTeX → Unicode/HTML, email-safe
src/utils/html_report_generator.py (rewrite)  mobile-first verdict-first cards
src/harness/knowledge_store.py (new)     embeddings.jsonl + topic notes
src/harness/memory_manager.py (replaced by knowledge_store)
src/utils/llm_client.py       (modify)   raise on error; honor config.ollama_url
src/harness/expert_agents.py  (modify)   real failures; full-text input
src/harness/expert_harness.py (modify)   reordered pipeline; JSON contracts
src/utils/paper_filter.py     (retained) cheap pre-filter only
```

`PaperFilter` keeps its current keyword logic but its role narrows: it drops
papers with no plausible connection at all before anything is embedded. Its
score is no longer used for ordering or inclusion — `relevance.py` owns both.
`min_score` drops to 0.0 so the embedding ranker, not the keyword list, decides
what is worth triaging.

### Data flow

```
arXiv RSS
  → PaperFilter          cheap keyword pre-filter (unchanged, widened)
  → relevance.py         embed vs profile → top ~15 → LLM triage → score/tags/why
  → paper_text.py        PDF → {abstract, introduction, results, conclusions}
  → knowledge_store      retrieve top-k similar past papers + topic notes
  → GRB + Kilonova experts (AstroSage-70B, real full text)
  → astrophysicist       JSON: why_it_matters, key_numbers[], analysis_en
  → critic               quality score
  → writer               polishes English only
  → language expert      strict translation of the final English
  → html_report_generator escape → latex convert → verdict-first card
  → email + knowledge_store.record()
```

The single most important structural change is that translation is now the
**last** step and takes the final English as its only source. English and
Korean cannot diverge because one is derived from the other after all editing
is finished.

### Interface contracts

`relevance.score(paper, profile) -> {score: float, topic_tags: [str], why_it_matters: str}`

`paper_text.extract(paper) -> {abstract: str, introduction: str, results: str, conclusions: str, source: "pdf"|"abstract"}`

`knowledge_store.recall(paper) -> {similar: [{title, arxiv_id, findings}], topic_notes: [{topic, note}]}`

`knowledge_store.record(paper, analysis) -> None`

`latex_to_html.convert(text) -> str` — escapes HTML first, then converts math.

Each is independently testable with no LLM or network access except
`relevance.score` (embedding + one LLM call) and `paper_text.extract` (HTTP).

## Component detail

### config/interests.yml

Prose profile plus explicit exclusions. Drafted from `config/sources.yml`, the
expert prompts, and the 61 titles in `data/memory/index.json`; the user
accepted the draft without changes.

```yaml
profile: >
  Observational and theoretical high-energy astrophysics centered on
  gamma-ray bursts and neutron star mergers.
core:
  - GRB prompt emission, spectral evolution, central engine
  - GRB jet structure, magnetization, polarization
  - GRB afterglows; GRB-supernova connections
  - Kilonovae, ejecta properties, r-process nucleosynthesis
  - NS-NS / NS-BH mergers and their EM counterparts
  - Multi-messenger follow-up (GW + gamma-ray), TDAMM
exclude:
  - AGN / blazar variability and unification models
  - BBH waveform modeling, surrogates, PE methodology
  - Primordial black holes, dark matter constraints
  - Binary population synthesis / common envelope
  - Cosmology using transients as standard candles
threshold: 6.0
max_triage: 15
```

`threshold` and `max_triage` are configurable because the right values depend
on daily arXiv volume and can only be tuned by observation.

### Relevance

The embedding stage is a cheap ranker, not a gate — it decides which papers are
worth an LLM call. The LLM triage is the gate. It receives the profile
including exclusions and returns JSON. A paper matching an exclusion is scored
low with the exclusion named in `why_it_matters`, so a wrong rejection is
visible in the report rather than silent.

The profile embedding is cached in `data/knowledge/profile.json`, keyed by a
hash of the profile text, and recomputed when the profile changes.

### Paper text extraction

PDFs are cached in the existing `data/pdfs/` by arXiv ID. Section detection
uses regex on common heading forms (numbered and unnumbered, upper and title
case). When headings cannot be found, fall back to the first 6k and last 6k
characters, which in practice covers introduction and conclusions. Total
extracted text is capped (default 12k chars) to bound prompt size on a local
32B model. Any failure degrades to abstract-only with `source: "abstract"`,
recorded so the report can indicate reduced depth.

Papers are fetched only after passing relevance, so at most ~6-10 PDFs per day.

### Report

Mobile-first, single fluid column. No fixed 40px padding, no
`text-align: justify`, 16px minimum body text. Per-paper card order:

1. Score badge + topic tags
2. Title, authors, arXiv link
3. WHY THIS MATTERS — one line
4. KEY NUMBERS — short list
5. `<details>` Abstract
6. `<details>` Analysis (English)
7. `<details>` 한국어 분석

Email clients block JavaScript, so KaTeX and MathJax are not options.
`latex_to_html.convert()` escapes HTML entities first, then maps common LaTeX
to Unicode: `\times` → ×, `\lesssim` → ≲, `10^{52}` → 10⁵², Greek commands,
and `$...$` / `\(...\)` delimiter stripping. Unrecognized commands are left as
readable text rather than dropped.

Critical layout properties are inlined on elements in addition to the `<style>`
block, because Gmail's handling of embedded stylesheets is inconsistent.

### Knowledge store

`data/knowledge/embeddings.jsonl` — one record per analyzed paper: arXiv ID,
title, vector, extracted findings, date.

`data/knowledge/topics/<slug>.md` — a running note per topic. After each run an
agent updates the notes touched by that day's papers, summarizing the current
state of that sub-field and what changed. Notes are append-then-condense so
they do not grow without bound.

Recall injects the 3 most semantically similar past papers (cosine ≥ 0.6, to
avoid padding the prompt with weak matches) and up to 2 matching topic notes
into the synthesis prompt.

`data/memory/` is moved to `data/memory.archive-20260730/`. Generated reports
in `data/reports/` are not touched.

## Delivery plan

Three reviewable chunks, in order. Each leaves the daily cron working.

**Chunk 1 — Fixes + readable mobile report.** Model-name resolution with loud
startup failure, `LLMClient` raising on error, agents reporting real failures,
HTML escaping, LaTeX conversion, mobile-first verdict-first template, abstract
included. Produces a visibly better report immediately and removes the silent
truncation. Lowest risk.

**Chunk 2 — Relevance + contents.** `interests.yml`, `embeddings.py`,
`relevance.py`, `paper_text.py`, wired into the run script.

**Chunk 3 — EN/KO parity + knowledge.** Pipeline reorder, JSON contracts,
strict-translation prompt with glossary, `knowledge_store.py`, memory archive.

## Verification

Unit tests, no network or LLM required:

- `latex_to_html`: `\(z < 10\)` survives round-trip and renders as `z < 10`;
  the exact string from today's broken report is a regression case.
- `latex_to_html`: `$8.0 \times 10^{-5}$` → `8.0 × 10⁻⁵`.
- `paper_text`: section splitting on a fixture with headings, and the
  headings-absent fallback path.
- `relevance`: with a stubbed embedder and stubbed triage, an excluded-topic
  paper scores below threshold and an on-topic paper above.
- `llm_client`: a non-200 response raises rather than returning a string.
- `expert_agents`: an LLM failure yields `success=False`.
- EN/KO parity: given a stubbed translator, the rendered card has the same
  section count and the same extracted numbers in both languages.

Integration: one real end-to-end run, emailed, checked on a phone.

Success criteria: no paper text is lost to escaping; every card shows abstract,
English, and Korean derived from the same source; every included paper carries
a score and a reason; no excluded-topic paper appears above threshold; the two
astronomy experts produce real reviews.
