"""Generic phonetic/spelling similarity for universal target resolution.

This module is deliberately application-agnostic. It does not contain
application, file, folder, or product names. It only compares user-entered
text with runtime-discovered candidate names.
"""

import difflib
import os
import re


def _normalize(value):
    value = str(value or "").strip().lower()
    value = value.replace("\\", "/")
    value = re.sub(r"[^a-z0-9/._-]+", " ", value)
    return " ".join(value.split())


def _candidate_variants(value):
    """Return generic text/path/name variants without domain knowledge."""
    normalized = _normalize(value)
    if not normalized:
        return []

    variants = [normalized]

    # A runtime candidate can be a full filesystem path. Compare its basename
    # as well, because a spoken command normally names the object, not its
    # parent directories.
    basename = normalized.rsplit("/", 1)[-1].strip()
    if basename and basename not in variants:
        variants.append(basename)

    # Compare a filename stem as well. This is intentionally generic: the
    # suffix is discovered from the candidate itself rather than from a fixed
    # application/file-extension list.
    stem, suffix = os.path.splitext(basename)
    if stem and suffix and re.fullmatch(r"\.[a-z0-9]{1,12}", suffix):
        stem = stem.strip(" ._-")
        if stem and stem not in variants:
            variants.append(stem)

    return variants


def _phonetic_key(value):
    value = _normalize(value)
    value = re.sub(r"[^a-z0-9]", "", value)
    replacements = (
        ("ksh", "x"), ("ks", "x"), ("chh", "c"), ("ch", "c"),
        ("sh", "s"), ("ph", "f"), ("bh", "b"), ("dh", "d"),
        ("th", "t"), ("kh", "h"), ("gh", "g"), ("aa", "a"),
        ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"),
        ("ai", "e"), ("au", "o"),
        # Voice recognition can interchange /v/ and /w/ in Romanized
        # Hindi/Hinglish. Treat them as the same phonetic class while
        # keeping the matcher generic and application-agnostic.
        ("v", "w"),
    )
    for source, replacement in replacements:
        value = value.replace(source, replacement)
    return "".join(ch for ch in value if ch not in "aeiou")


def _pair_score(query, candidate):
    raw = difflib.SequenceMatcher(None, query, candidate).ratio()
    qp = _phonetic_key(query)
    cp = _phonetic_key(candidate)
    phonetic = (
        difflib.SequenceMatcher(None, qp, cp).ratio()
        if qp and cp else 0.0
    )
    return max(raw, phonetic)


def score_candidate(query, candidate):
    """Return a generic 0..1 similarity score."""
    query_variants = _candidate_variants(query)
    candidate_variants = _candidate_variants(candidate)
    if not query_variants or not candidate_variants:
        return 0.0

    best = 0.0
    for q in query_variants:
        for c in candidate_variants:
            if q == c:
                return 1.0
            if q in c or c in q:
                best = max(best, 0.90)
                continue
            best = max(best, _pair_score(q, c))
    return best


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
