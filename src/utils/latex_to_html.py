#!/usr/bin/env python3
"""
Convert model output containing LaTeX into safe, readable HTML.

Two jobs, in this order:

1. Escape HTML. Model output regularly contains '<' inside math (e.g.
   'redshift \\(z < 10\\)'). Interpolated raw, the browser reads it as a tag and
   discards the rest of the paragraph.
2. Render common LaTeX as text. Email clients block JavaScript, so KaTeX and
   MathJax are unavailable; math becomes Unicode plus <sup>/<sub>, which every
   mail client renders.

Unrecognised commands lose their backslash and keep their name, so content is
never silently dropped.
"""

import html
import re

# Escaped literals are parked on sentinels so later passes cannot reinterpret
# them (an escaped underscore must not become a subscript).
_SENTINELS = {
    r"\_": "\x00us\x00",
    r"\$": "\x00dl\x00",
    r"\%": "\x00pc\x00",
    r"\#": "\x00hs\x00",
}
_RESTORE = {"\x00us\x00": "_", "\x00dl\x00": "$", "\x00pc\x00": "%", "\x00hs\x00": "#"}

_ACCENTS = {
    '"': {"a": "ä", "e": "ë", "i": "ï", "o": "ö", "u": "ü", "y": "ÿ",
          "A": "Ä", "E": "Ë", "I": "Ï", "O": "Ö", "U": "Ü"},
    "'": {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "y": "ý", "c": "ć", "n": "ń", "s": "ś",
          "A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú"},
    "`": {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù",
          "A": "À", "E": "È", "I": "Ì", "O": "Ò", "U": "Ù"},
    "^": {"a": "â", "e": "ê", "i": "î", "o": "ô", "u": "û",
          "A": "Â", "E": "Ê", "I": "Î", "O": "Ô", "U": "Û"},
    "~": {"n": "ñ", "a": "ã", "o": "õ", "N": "Ñ", "A": "Ã", "O": "Õ"},
    "c": {"c": "ç", "C": "Ç"},
    "v": {"c": "č", "s": "š", "z": "ž", "r": "ř", "C": "Č", "S": "Š", "Z": "Ž"},
}

# Commands replaced by a single character. Applied longest-first so that \le
# never shadows \lesssim.
_SYMBOLS = {
    # relations
    r"\lesssim": "≲", r"\gtrsim": "≳", r"\leqslant": "≤", r"\geqslant": "≥",
    r"\leq": "≤", r"\geq": "≥", r"\le": "≤", r"\ge": "≥",
    r"\ll": "≪", r"\gg": "≫", r"\neq": "≠", r"\ne": "≠",
    r"\approx": "≈", r"\simeq": "≃", r"\sim": "∼", r"\propto": "∝",
    r"\equiv": "≡", r"\pm": "±", r"\mp": "∓",
    # operators
    r"\times": "×", r"\cdot": "·", r"\cdots": "⋯", r"\ldots": "…", r"\dots": "…",
    r"\div": "÷", r"\odot": "⊙", r"\oplus": "⊕", r"\infty": "∞",
    r"\partial": "∂", r"\nabla": "∇", r"\int": "∫", r"\sum": "Σ", r"\prod": "Π",
    r"\sqrt": "√", r"\rightarrow": "→", r"\leftarrow": "←", r"\to": "→",
    r"\Rightarrow": "⇒", r"\degree": "°", r"\prime": "′",
    # greek (upper first is irrelevant; longest-first ordering handles overlap)
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\varepsilon": "ε", r"\zeta": "ζ", r"\eta": "η",
    r"\theta": "θ", r"\vartheta": "θ", r"\iota": "ι", r"\kappa": "κ",
    r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν", r"\xi": "ξ",
    r"\pi": "π", r"\rho": "ρ", r"\sigma": "σ", r"\tau": "τ",
    r"\upsilon": "υ", r"\phi": "φ", r"\varphi": "φ", r"\chi": "χ",
    r"\psi": "ψ", r"\omega": "ω",
    r"\Gamma": "Γ", r"\Delta": "Δ", r"\Theta": "Θ", r"\Lambda": "Λ",
    r"\Xi": "Ξ", r"\Pi": "Π", r"\Sigma": "Σ", r"\Upsilon": "Υ",
    r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
    # spacing
    r"\quad": " ", r"\qquad": "  ", r"\,": " ", r"\;": " ", r"\:": " ", r"\!": "",
    # font switches carry no meaning once rendered as text
    r"\rm": "", r"\bf": "", r"\it": "", r"\sf": "", r"\tt": "", r"\displaystyle": "",
}

# Wrappers whose braced content should survive and whose name should not.
_UNWRAP = (
    "mathrm", "mathbf", "mathit", "mathsf", "mathtt", "mathcal", "boldmath",
    "text", "textrm", "textbf", "textit", "texttt", "emph", "operatorname", "rm",
)

_SYMBOL_RE = re.compile(
    "|".join(re.escape(k) for k in sorted(_SYMBOLS, key=len, reverse=True))
    + r"(?![a-zA-Z])"
)


def _apply_accents(text: str) -> str:
    def replace(match: re.Match) -> str:
        accent, letter = match.group(1), match.group(2)
        return _ACCENTS.get(accent, {}).get(letter, letter)

    # \"u, \"{u}, \'e, \~n, \c{c} ...
    pattern = r'\\(["\'`^~cv])\{?([a-zA-Z])\}?'
    return re.sub(pattern, replace, text)


def _strip_delimiters(text: str) -> str:
    # Removing delimiter tokens rather than matching pairs keeps unbalanced
    # fragments readable, which matters because truncated model output is common.
    text = re.sub(r"\\[\(\)\[\]]", "", text)
    text = text.replace("$$", "").replace("$", "")
    return text


def _apply_scripts(text: str) -> str:
    text = re.sub(r"\^\{([^{}]*)\}", lambda m: f"<sup>{m.group(1).strip()}</sup>", text)
    text = re.sub(r"_\{([^{}]*)\}", lambda m: f"<sub>{m.group(1).strip()}</sub>", text)
    text = re.sub(r"\^([A-Za-z0-9+\-])", r"<sup>\1</sup>", text)
    text = re.sub(r"_([A-Za-z0-9+\-])", r"<sub>\1</sub>", text)
    return text


def _unwrap_commands(text: str) -> str:
    names = "|".join(_UNWRAP)
    for _ in range(3):  # a few passes handle shallow nesting
        new = re.sub(r"\\(?:" + names + r")\s*\{([^{}]*)\}", r"\1", text)
        if new == text:
            break
        text = new
    return text


def convert(text) -> str:
    """Escape HTML in `text`, then render its LaTeX as readable HTML."""
    if not text:
        return ""

    out = html.escape(str(text), quote=False)
    # html.escape turned '&' into '&amp;', so an escaped LaTeX ampersand is now
    # '\&amp;'; reduce it to the entity alone.
    out = out.replace(r"\&amp;", "&amp;")

    for literal, sentinel in _SENTINELS.items():
        out = out.replace(literal, sentinel)

    out = _apply_accents(out)
    out = _strip_delimiters(out)
    out = re.sub(r"\\\\", " ", out)  # LaTeX line break
    out = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"\1/\2", out)
    out = _SYMBOL_RE.sub(lambda m: _SYMBOLS[m.group(0)], out)
    out = _apply_scripts(out)
    out = _unwrap_commands(out)

    # Anything left: keep the word, drop the backslash and stray braces.
    out = re.sub(r"\\([a-zA-Z]+)", r"\1", out)
    out = out.replace("\\", "")
    out = out.replace("{", "").replace("}", "")

    for sentinel, literal in _RESTORE.items():
        out = out.replace(sentinel, literal)

    # Collapse runs of spaces introduced by removed commands, without touching
    # newlines (paragraph structure is the renderer's concern).
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out
