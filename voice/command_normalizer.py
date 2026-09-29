"""Generic voice-command normalization and confidence scoring.

This layer sits between STT romanization and the existing IntentEngine.
It corrects only language-level command words. Runtime targets such as
applications, files, folders, URLs, and user names are deliberately left
untouched so the existing universal resolver can handle them.
"""

import difflib
import re
from typing import Dict, List, Tuple


class VoiceCommandNormalizer:
    """Application-agnostic correction of noisy spoken command language."""

    # Canonical command vocabulary only. No application/file names belong here.
    COMMAND_ALIASES = {
        "open": ("opan", "opn", "oppen", "opain", "opan"),
        "close": ("cloz", "kloj", "cloze", "clouse", "cloze"),
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
        "start": ("stert", "stat", "start"),
        "stop": ("stap", "stopp"),
        "number": ("nanbar", "nambar", "numbar"),
        "cancel": ("cansal", "cancle", "cansel"),
        "copy": ("copi", "coopy"),
        "paste": ("paist", "pest"),
        "cut": ("kat", "katt"),
        "undo": ("ando", "undu"),
        "redo": ("redo", "rido"),
        "scroll": ("scrol", "skrol"),
        "back": ("bak", "bake"),
        "forward": ("forword", "foward", "forwad"),
        "refresh": ("refres", "refrech"),
    }

    # Common Hindi/Hinglish action words. These are syntax, not targets.
    HINDI_ACTIONS = {
        "khol": "open", "kholo": "open", "kholna": "open", "kholiye": "open",
        "kholen": "open", "khol do": "open", "kholdo": "open",
        "band": "close", "band karo": "close", "band kar": "close",
        "band kar do": "close", "rok": "stop", "rok do": "stop",
        "likho": "type", "likhen": "type", "likhna": "type",
        "taip karo": "type", "type karo": "type",
        "dabao": "press", "dabaye": "press", "click karo": "click",
        "save karo": "save", "bachaao": "save",
        "dhundo": "search", "dhoondo": "search", "khojo": "search",
    }

    def __init__(self, min_similarity: float = 0.74):
        self.min_similarity = float(min_similarity)
        self._alias_to_canonical = {}
        for canonical, aliases in self.COMMAND_ALIASES.items():
            self._alias_to_canonical[canonical] = canonical
            for alias in aliases:
                self._alias_to_canonical[alias] = canonical

    @staticmethod
    def _clean(text: str) -> str:
        value = str(text or "").strip().lower()
        value = re.sub(r"[^a-z0-9_\s-]", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def _best_word(self, word: str) -> Tuple[str, float]:
        normalized = self._clean(word)
        if not normalized:
            return "", 0.0
        exact = self._alias_to_canonical.get(normalized)
        if exact:
            return exact, 1.0

        best_name = normalized
        best_score = 0.0
        for alias, canonical in self._alias_to_canonical.items():
            score = difflib.SequenceMatcher(None, normalized, alias).ratio()
            if score > best_score:
                best_score = score
                best_name = canonical
        if best_score >= self.min_similarity:
            return best_name, best_score
        return normalized, best_score

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
        output: List[str] = []
        corrections = []
        scores = []

        index = 0
        while index < len(tokens):
            # Prefer known multi-word Hindi/Hinglish command phrases.
            if index + 2 < len(tokens):
                phrase = " ".join(tokens[index:index + 3])
                canonical = self.HINDI_ACTIONS.get(phrase)
                if canonical:
                    output.append(canonical)
                    corrections.append({"from": phrase, "to": canonical, "score": 1.0})
                    scores.append(1.0)
                    index += 3
                    continue
            if index + 1 < len(tokens):
                phrase = " ".join(tokens[index:index + 2])
                canonical = self.HINDI_ACTIONS.get(phrase)
                if canonical:
                    output.append(canonical)
                    corrections.append({"from": phrase, "to": canonical, "score": 1.0})
                    scores.append(1.0)
                    index += 2
                    continue

            token = tokens[index]
            canonical, score = self._best_word(token)
            # Only replace a token when it is a command alias/correction.
            if canonical != token and score >= self.min_similarity:
                output.append(canonical)
                corrections.append({"from": token, "to": canonical, "score": round(score, 4)})
                scores.append(score)
            else:
                output.append(token)
            index += 1

        normalized = " ".join(output).strip()
        # Confidence is conservative: an unchanged sentence is high-confidence
        # only when it already contains a known command word.
        command_hits = sum(1 for token in output if token in self.COMMAND_ALIASES)
        correction_scores = [float(item["score"]) for item in corrections]
        if correction_scores:
            confidence = min(correction_scores)
        elif command_hits:
            confidence = 1.0
        else:
            confidence = 0.0

        return {
            "text": normalized,
            "changed": normalized != original.lower(),
            "confidence": round(confidence, 4),
            "corrections": corrections,
        }

    def normalize_text(self, text: str) -> str:
        return str(self.normalize(text).get("text") or "")


__all__ = ["VoiceCommandNormalizer"]
