"""Conservative, application-agnostic recovery for noisy speech transcripts.

Only command-boundary words are compared with generic operation vocabulary.
User payloads are left alone. Runtime target names are corrected only when a
live/context-supplied candidate wins by a clear margin. The untouched transcript
is always retained by the caller for diagnostics and safe clarification.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    from tools.phonetic_matcher import score_candidate
except Exception:  # Keep transcript understanding available if matcher is unavailable.
    score_candidate = None


class TranscriptRecovery:
    """Recover likely command intent without embedding application-name aliases."""

    _PUNCTUATION = ".,!?;:،؟"

    @classmethod
    def _normalize(cls, value: Any) -> str:
        return re.sub(r"\\s+", " ", str(value or "").strip())

    @classmethod
    def _clean_token(cls, value: str) -> str:
        return str(value or "").strip(cls._PUNCTUATION)

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        a = re.sub(r"[^\\w]+", "", cls._normalize(left).casefold(), flags=re.UNICODE)
        b = re.sub(r"[^\\w]+", "", cls._normalize(right).casefold(), flags=re.UNICODE)
        if not a or not b:
            return 0.0
        score = SequenceMatcher(None, a, b).ratio()
        if score_candidate is not None and a.isascii() and b.isascii():
            try:
                score = max(score, float(score_candidate(a, b)))
            except Exception:
                pass
        return score

    @staticmethod
    def _phrase_tokens(phrase: str) -> List[str]:
        return [token for token in re.split(r"\\s+", str(phrase or "").strip()) if token]

    @classmethod
    def _best_phrase(
        cls,
        token_span: Sequence[str],
        phrases: Iterable[str],
    ) -> Optional[Tuple[str, float, float]]:
        cleaned = [cls._clean_token(token) for token in token_span]
        observed = " ".join(cleaned).strip()
        if not observed:
            return None

        normalized_observed = observed.casefold()
        ranked = []
        seen = set()
        for phrase in phrases:
            canonical = cls._normalize(phrase)
            if not canonical:
                continue
            parts = cls._phrase_tokens(canonical)
            if len(parts) != len(token_span):
                continue
            key = canonical.casefold()
            if key in seen:
                continue
            seen.add(key)
            if key == normalized_observed:
                return None
            ranked.append((cls._similarity(observed, canonical), canonical))

        ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
        if not ranked:
            return None
        best_score, best_phrase = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0
        threshold = 0.72 if len(observed.replace(" ", "")) >= 4 else 0.88
        if best_score < threshold or (best_score - second_score) < 0.035:
            return None
        return best_phrase, best_score, best_score - second_score

    @classmethod
    def _repair_boundary(
        cls,
        text: str,
        phrases: Iterable[str],
        side: str,
        corrections: List[Dict[str, Any]],
    ) -> str:
        tokens = text.split()
        if not tokens:
            return text
        limit = min(3, len(tokens))
        for size in sorted(range(1, limit + 1), reverse=True):
            span = tokens[:size] if side == "start" else tokens[-size:]
            candidate = cls._best_phrase(span, phrases)
            if not candidate:
                continue
            phrase, confidence, margin = candidate
            old = " ".join(span)
            if side == "start":
                tokens = cls._phrase_tokens(phrase) + tokens[size:]
            else:
                tokens = tokens[:-size] + cls._phrase_tokens(phrase)
            corrections.append({
                "kind": "operation_marker",
                "observed": old,
                "recovered": phrase,
                "confidence": round(confidence, 4),
                "margin": round(margin, 4),
                "position": side,
            })
            return " ".join(tokens)
        return text

    @classmethod
    def _candidate_values(cls, context: Mapping[str, Any]) -> List[str]:
        found: List[str] = []
        list_keys = (
            "runtime_candidates", "runtime_targets", "available_targets",
            "candidate_names", "app_candidates", "window_candidates",
            "running_windows", "visible_windows", "selection_options",
        )
        for key in list_keys:
            value = context.get(key)
            if not isinstance(value, (list, tuple, set)):
                continue
            for item in value:
                values = []
                if isinstance(item, Mapping):
                    values.extend(
                        item.get(field)
                        for field in ("name", "title", "display_name", "path", "target", "app_name")
                    )
                else:
                    values.append(item)
                for raw in values:
                    name = cls._normalize(raw)
                    if not name:
                        continue
                    choices = [name]
                    choices.extend(part.strip() for part in re.split(r"\\s+[—–-]\\s+", name) if part.strip())
                    for choice in choices:
                        if choice and choice.casefold() not in {item.casefold() for item in found}:
                            found.append(choice)

        for key in ("current_window", "current_app", "current_target"):
            value = context.get(key)
            if isinstance(value, Mapping):
                value = value.get("title") or value.get("name")
            name = cls._normalize(value)
            if name and name.casefold() not in {item.casefold() for item in found}:
                found.append(name)
        ui = context.get("ui")
        if isinstance(ui, Mapping):
            window = ui.get("active_window")
            if isinstance(window, Mapping):
                name = cls._normalize(window.get("title") or window.get("name"))
                if name and name.casefold() not in {item.casefold() for item in found}:
                    found.append(name)
        return found

    @classmethod
    def _surface_operation(
        cls,
        text: str,
        operation_phrases: Mapping[str, Sequence[str]],
    ) -> Optional[Tuple[str, str, str]]:
        tokens = text.split()
        if not tokens:
            return None
        for operation in ("open", "close"):
            phrases = sorted(
                operation_phrases.get(operation, ()),
                key=lambda item: len(cls._phrase_tokens(item)),
                reverse=True,
            )
            for phrase in phrases:
                size = len(cls._phrase_tokens(phrase))
                if size <= len(tokens) and " ".join(tokens[:size]).casefold() == phrase.casefold():
                    return operation, phrase, "start"
                if size <= len(tokens) and " ".join(tokens[-size:]).casefold() == phrase.casefold():
                    return operation, phrase, "end"
        return None

    @classmethod
    def _repair_runtime_target(
        cls,
        text: str,
        operation_phrases: Mapping[str, Sequence[str]],
        context: Mapping[str, Any],
        corrections: List[Dict[str, Any]],
    ) -> str:
        if re.search(r"\\s+(?:and|then|aur|phir|fir|और|फिर)\\s+", text, flags=re.IGNORECASE):
            return text
        surface = cls._surface_operation(text, operation_phrases)
        if not surface:
            return text
        operation, phrase, side = surface
        candidates = cls._candidate_values(context)
        tokens = text.split()
        marker_size = len(cls._phrase_tokens(phrase))
        target_tokens = tokens[marker_size:] if side == "start" else tokens[:-marker_size]
        target = " ".join(target_tokens).strip(cls._PUNCTUATION + " ")
        if not target or not candidates or target.casefold() in {item.casefold() for item in candidates}:
            return text

        ranked = sorted(
            ((cls._similarity(target, candidate), candidate) for candidate in candidates),
            key=lambda item: (-item[0], item[1].casefold()),
        )
        if not ranked:
            return text
        best_score, best_target = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score < 0.76 or (best_score - second_score) < 0.10:
            return text

        repaired = (
            cls._phrase_tokens(phrase) + [best_target]
            if side == "start"
            else [best_target] + cls._phrase_tokens(phrase)
        )
        corrections.append({
            "kind": "runtime_target",
            "observed": target,
            "recovered": best_target,
            "confidence": round(best_score, 4),
            "margin": round(best_score - second_score, 4),
            "operation": operation,
        })
        return " ".join(repaired)

    def recover(
        self,
        transcript: Any,
        operation_phrases: Mapping[str, Sequence[str]],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw = self._normalize(transcript)
        if not raw:
            return {
                "raw_transcript": raw,
                "text": raw,
                "corrections": [],
                "changed": False,
                "confidence": None,
            }
        ctx = context if isinstance(context, Mapping) else {}
        corrections: List[Dict[str, Any]] = []
        all_phrases = [phrase for phrases in operation_phrases.values() for phrase in phrases]
        text = self._repair_boundary(raw, all_phrases, "start", corrections)
        text = self._repair_boundary(text, all_phrases, "end", corrections)
        text = self._repair_runtime_target(text, operation_phrases, ctx, corrections)
        confidence_values = [item["confidence"] for item in corrections]
        return {
            "raw_transcript": raw,
            "text": text,
            "corrections": corrections,
            "changed": text != raw,
            "confidence": round(min(confidence_values), 4) if confidence_values else None,
        }


__all__ = ["TranscriptRecovery"]
