"""Generic phonetic/spelling similarity for universal target resolution.

This module is deliberately application-agnostic. It does not contain
application, file, folder, or product names. It only compares user-entered
text with runtime-discovered candidate names.
"""

import difflib
import re


def _normalize(value):
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _phonetic_key(value):
    value = _normalize(value)
    replacements = (
        ("ksh", "x"), ("ks", "x"), ("chh", "c"), ("ch", "c"),
        ("sh", "s"), ("ph", "f"), ("bh", "b"), ("dh", "d"),
        ("th", "t"), ("kh", "h"), ("gh", "g"), ("aa", "a"),
        ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"),
        ("ai", "e"), ("au", "o"),
    )
    for source, replacement in replacements:
        value = value.replace(source, replacement)
    value = re.sub(r"[^a-z0-9]", "", value)
    return "".join(ch for ch in value if ch not in "aeiou")


def score_candidate(query, candidate):
    """Return a generic 0..1 similarity score."""
    q = _normalize(query)
    c = _normalize(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    if q in c or c in q:
        return 0.90

    raw = difflib.SequenceMatcher(None, q, c).ratio()
    qp = _phonetic_key(q)
    cp = _phonetic_key(c)
    phonetic = (
        difflib.SequenceMatcher(None, qp, cp).ratio()
        if qp and cp else 0.0
    )
    return max(raw, phonetic)


def rank_candidates(query, candidates, threshold=0.72, limit=8):
    """Rank runtime-discovered candidates without knowing their domain."""
    scored = []
    for candidate in candidates or ():
        name = str(candidate or "").strip()
        if not name:
            continue
        score = score_candidate(query, name)
        if score >= threshold:
            scored.append((score, name))

    scored.sort(key=lambda item: (-item[0], item[1].lower()))
    return scored[:max(0, int(limit))]


__all__ = ["score_candidate", "rank_candidates"]
