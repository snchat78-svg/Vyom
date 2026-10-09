"""Generic voice-command normalization and confidence scoring.

The normalizer corrects noisy command language at the voice boundary while
protecting runtime targets. Application, file, folder and user names are not
stored here and are not fuzzy-corrected as command words.
"""

import re
from typing import Dict, List, Tuple


class VoiceCommandNormalizer:
    """Application-agnostic correction of spoken command syntax."""

    COMMAND_ALIASES = {
        "open": ("opan", "opn", "oppen", "opain"),
        "close": ("cloz", "kloj", "cloze", "clouse"),
        "search": ("serch", "sarch", "seach", "surch"),
        "find": ("fand", "phind", "fin"),
        "type": ("taip", "tiep", "typ", "taipe"),
        "write": ("rait", "rite", "wrait"),
        "press": ("pres", "presh"),
        "click": ("clik", "clikc", "klik"),
        "select": ("selec", "silect", "salect"),
        "delete": ("delet", "delit", "dilit"),
        "save": ("saiv", "sive", "seiv"),
        "launch": ("lanch", "laun", "lonch"),
        "start": ("stert", "stat"),
        "stop": ("stap", "stopp"),
        "number": ("nanbar", "nambar", "numbar"),
        "cancel": ("cansal", "cancle", "cansel"),
        "copy": ("copi", "coopy"),
        "paste": ("paist", "pest"),
        "cut": ("kat", "katt"),
        "undo": ("ando", "undu"),
        "redo": ("rido",),
        "scroll": ("scrol", "skrol"),
        "back": ("bak", "bake"),
        "forward": ("forword", "foward", "forwad"),
        "refresh": ("refres", "refrech"),
    }

    HINDI_ACTIONS = {
        "khol": "open", "kholo": "open", "kholna": "open", "kholiye": "open",
        "kholen": "open", "khol do": "open", "kholdo": "open",
        "band": "close", "band karo": "close", "band kar": "close",
        "band kar do": "close", "rok": "stop", "rok do": "stop",
        "likho": "type", "likhen": "type", "likhna": "type",
        "taip karo": "type", "type karo": "type",
        "dabao": "press", "dabaye": "press",
        "click karo": "click", "save karo": "save",
        "dhundo": "search", "dhoondo": "search", "khojo": "search",
    }

    COMMAND_HELPERS = {
        "karo", "kar", "karen", "kariye", "karie", "do", "dena",
        "please", "pls", "now",
    }

    CONNECTORS = {
        "and", "then", "after", "afterthat", "aur", "phir",
        "uske", "baad", "fir",
    }

    def __init__(self, min_similarity: float = 0.74):
        self.min_similarity = float(min_similarity)
        self._alias_to_canonical = {}
        for canonical, aliases in self.COMMAND_ALIASES.items():
            self._alias_to_canonical[canonical] = canonical
            for alias in aliases:
                self._alias_to_canonical[alias] = canonical

    @staticmethod
    def _clean_word(value: str) -> str:
        return re.sub(r"[^a-z0-9_-]", "", str(value or "").strip().lower())

    @staticmethod
    def _clean_text(value: str) -> str:
        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9_\s-]", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _edit_similarity(left: str, right: str) -> float:
        """Normalized edit similarity; reject substring false positives."""
        left, right = str(left or ""), str(right or "")
        if not left or not right:
            return 0.0
        previous = list(range(len(right) + 1))
        for i, left_char in enumerate(left, start=1):
            current = [i]
            for j, right_char in enumerate(right, start=1):
                current.append(min(
                    current[j - 1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (left_char != right_char),
                ))
            previous = current
        return 1.0 - previous[-1] / max(len(left), len(right))

    def _best_word(self, word: str) -> Tuple[str, float]:
        normalized = self._clean_word(word)
        if not normalized:
            return "", 0.0

        exact = self._alias_to_canonical.get(normalized)
        if exact:
            return exact, 1.0

        best_name = normalized
        best_score = 0.0
        for alias, canonical in self._alias_to_canonical.items():
            score = self._edit_similarity(normalized, alias)
            if score > best_score:
                best_score = score
                best_name = canonical

        if best_score >= self.min_similarity:
            return best_name, best_score
        return normalized, best_score

    def _replace_at(self, tokens: List[str], index: int, canonical: str, score: float, corrections):
        original = tokens[index]
        tokens[index] = canonical
        corrections.append({
            "from": original,
            "to": canonical,
            "score": round(float(score), 4),
            "position": index,
        })

    def normalize(self, text: str) -> Dict[str, object]:
        original = str(text or "").strip()
        if not original:
            return {
                "text": "",
                "changed": False,
                "confidence": 0.0,
                "corrections": [],
            }

        tokens = original.lower().split()
        corrections: List[Dict[str, object]] = []
        scores: List[float] = []

        # Exact multi-word Hinglish/Hindi command phrases are safe to correct
        # wherever they occur because they contain explicit action syntax.
        i = 0
        while i < len(tokens):
            matched = False
            for width in (3, 2, 1):
                if i + width <= len(tokens):
                    phrase = " ".join(tokens[i:i + width])
                    canonical = self.HINDI_ACTIONS.get(phrase)
                    if canonical:
                        tokens[i:i + width] = [canonical]
                        corrections.append({
                            "from": phrase,
                            "to": canonical,
                            "score": 1.0,
                            "position": i,
                        })
                        scores.append(1.0)
                        matched = True
                        break
            if matched:
                continue
            i += 1

        # Correct a fuzzy English/Roman command only in command position:
        # start of utterance, or after an explicit multi-step connector.
        # Runtime targets are therefore protected from fuzzy command rewriting.
        command_positions = {0}
        for index, token in enumerate(tokens):
            if token in self.CONNECTORS and index + 1 < len(tokens):
                command_positions.add(index + 1)

        # A trailing command before a helper (e.g. "notepad kloj karo") is
        # also command context, but the helper itself is never fuzzy-corrected.
        for index in range(len(tokens) - 1):
            if tokens[index + 1] in self.COMMAND_HELPERS:
                command_positions.add(index)

        for index in sorted(command_positions):
            if index >= len(tokens):
                continue
            token = tokens[index]
            if token in self.COMMAND_HELPERS or token in self.CONNECTORS:
                continue
            canonical, score = self._best_word(token)
            if canonical != token and score >= self.min_similarity:
                self._replace_at(tokens, index, canonical, score, corrections)
                scores.append(score)

        normalized = " ".join(tokens).strip()

        command_hits = sum(
            1 for token in tokens
            if token in self.COMMAND_ALIASES
        )
        confidence = (
            min(scores)
            if scores
            else (1.0 if command_hits else 0.0)
        )

        return {
            "text": normalized,
            "changed": normalized != original.lower(),
            "confidence": round(float(confidence), 4),
            "corrections": corrections,
        }

    def normalize_text(self, text: str) -> str:
        return str(self.normalize(text).get("text") or "")


__all__ = ["VoiceCommandNormalizer"]
