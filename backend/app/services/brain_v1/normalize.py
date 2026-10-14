"""Normalización robusta del texto (cerebro v1 + taxonomía v2; solo corre con BRAIN_V1_ENABLED).

Para correos con faltas de ortografía, homoglifos, caracteres raros o idiomas mezclados:
  1. quita caracteres invisibles o de control (ancho cero, BOM, bidi, escapes ANSI) y pliega acentos;
  2. convierte homoglifos (cirílico/griego parecidos al latino) y "leet" dentro de palabras (c0ntrase5a);
  3. corrige palabras clave mal escritas por coincidencia aproximada contra el VOCABULARIO de las propias
     reglas del cerebro (letras duplicadas, una letra de menos/de más/cambiada; dos en palabras largas).
Nunca inventa contenido: solo reemplaza una palabra por una palabra clave cuando el candidato es único.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from app.services.brain_v1.protected import fold

_HOMO = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s", "к": "k",
    "м": "m", "т": "t", "н": "h", "в": "b", "ԁ": "d", "ɡ": "g", "ⅼ": "l", "ı": "i",
    "α": "a", "ο": "o", "ε": "e", "ρ": "p", "ν": "v", "τ": "t", "ι": "i", "κ": "k", "χ": "x", "υ": "u",
})
_LEET = str.maketrans({"0": "o", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s", "1": "i", "7": "t"})
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_TOKEN_RE = re.compile(r"[a-z0-9@$]+")
_SQUEEZE_RE = re.compile(r"([a-z])\1+")
_SPACES_RE = re.compile(r"[ \t\u00a0]{2,}")


def clean(text: str | None) -> str:
    """Quita invisibles/control y homoglifos; pliega a minúsculas sin acentos."""
    raw = _ANSI_RE.sub(" ", text or "")
    out = []
    for ch in raw:
        if ch in "\n\t":
            out.append(ch)
            continue
        cat = unicodedata.category(ch)
        if cat in {"Cf", "Cc", "Co", "Cs"}:
            continue
        out.append(ch)
    return fold("".join(out).translate(_HOMO).lower()).translate(_HOMO)


def _squeeze(word: str) -> str:
    return _SQUEEZE_RE.sub(r"\1", word)


def _deletes(word: str, depth: int) -> set[str]:
    level = {word}
    out: set[str] = set()
    for _ in range(depth):
        level = {w[:i] + w[i + 1:] for w in level for i in range(len(w))}
        out |= level
    return out


@lru_cache(maxsize=1)
def _vocab() -> tuple[frozenset[str], dict[str, str], dict[str, set[str]]]:
    from app.services.brain_v1 import analyzer, dates, phishing_v2, protected, taxonomy_v2

    words: set[str] = set(dates.MONTHS) | set(dates.WEEKDAYS)
    for module in (analyzer, dates, phishing_v2, protected, taxonomy_v2):
        for value in vars(module).values():
            pats = []
            if isinstance(value, re.Pattern):
                pats = [value]
            elif isinstance(value, (list, tuple)):
                pats = [x for x in value if isinstance(x, re.Pattern)]
                pats += [y for x in value if isinstance(x, tuple) for y in x if isinstance(y, re.Pattern)]
            elif isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, list):
                        pats += [y for x in v if isinstance(x, tuple) for y in x if isinstance(y, re.Pattern)]
            for p in pats:
                words |= set(re.findall(r"(?<![\\a-z])[a-z]{4,}", p.pattern.replace("\\b", " ").replace("\\s", " ")))
    words |= {"contrasena", "seguimiento", "verificacion", "reconocido", "modificada", "comercio", "asistencia",
              "confirmation", "booking", "departs", "october", "reunion", "proyecto", "contrato", "revision", "dispositivo",
              "estado", "cuenta", "tarjeta", "sesion", "inicio", "nuevo", "codigo", "compartas", "cambio", "correctamente"}
    vocab = frozenset(words)
    squeezed: dict[str, str] = {}
    for w in vocab:
        squeezed.setdefault(_squeeze(w), w)
    index: dict[str, set[str]] = {}
    for w in vocab:
        if len(w) < 5:
            continue
        s = _squeeze(w)
        for d in _deletes(s, 2 if len(s) >= 8 else 1) | {s}:
            index.setdefault(d, set()).add(w)
    return vocab, squeezed, index


def _correct(token: str) -> str:
    vocab, squeezed, index = _vocab()
    if len(token) < 4 or token in vocab or token.isdigit():
        return token
    if any(c.isdigit() or c in "@$" for c in token) and sum(c.isalpha() for c in token) >= 2:
        leet = token.translate(_LEET)
        if leet in vocab:
            return leet
        if "@" in token:
            return token  # L7reg1 (4): una dirección (ana@correo) nunca se "corrige"; solo F@ctura → factura si es palabra clave
        token = leet if not any(c.isdigit() for c in token[:1]) else token
    s = _squeeze(token)
    if s in squeezed:
        return squeezed[s]
    if len(s) < 5 or not s.isalpha():
        return token
    cands: set[str] = set(index.get(s, set()))
    if not cands:
        for d in _deletes(s, 2 if len(s) >= 8 else 1):
            cands |= {w for w in index.get(d, set()) if abs(len(_squeeze(w)) - len(s)) <= (2 if len(s) >= 8 else 1)}
    if len(cands) == 1:
        return next(iter(cands))
    return token


def normalize(text: str | None) -> str:
    """Texto limpio + palabras clave corregidas. Mantiene puntuación, números y saltos de línea."""
    base = _SPACES_RE.sub(" ", clean(text))  # L7reg1 (4): espacios repetidos/tabuladores → uno (no toca saltos de línea)
    return _TOKEN_RE.sub(lambda m: _correct(m[0]), base)
