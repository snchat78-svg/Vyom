"""Generic Devanagari -> Roman text normalization for Vyom voice input.

This module is intentionally application-agnostic.  It converts Hindi/
Devanagari script at the voice boundary into Latin/Roman text so downstream
intent, resolver, and execution layers receive one stable command format.

Latin/English input is preserved.  No application names or command aliases are
stored here.
"""

import re
import unicodedata


class RomanTextNormalizer:
    """Normalize voice transcripts into Latin/Roman script without dependencies."""

    # Independent Devanagari vowels.
    INDEPENDENT_VOWELS = {
        "अ": "a", "आ": "aa", "इ": "i", "ई": "ii",
        "उ": "u", "ऊ": "uu", "ऋ": "ri", "ॠ": "ri",
        "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    }

    # Base consonants.  Explicit nukta forms are included as well.
    CONSONANTS = {
        "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
        "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
        "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
        "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
        "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
        "य": "y", "र": "r", "ल": "l", "व": "v",
        "श": "sh", "ष": "sh", "स": "s", "ह": "h",
        "ळ": "l",
        "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z",
        "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y",
    }

    # Dependent vowel signs.
    MATRAS = {
        "ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu",
        "ृ": "ri", "ॄ": "ri", "े": "e", "ै": "ai", "ो": "o",
        "ौ": "au", "ॉ": "o", "ॅ": "e", "ॊ": "o", "ॆ": "e",
    }

    DEVANAGARI_DIGITS = {
        "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
        "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
    }

    SPECIAL = {
        "ं": "n", "ँ": "n", "ः": "h", "ऽ": "'",
    }

    _NUKTA = "़"
    _VIRAMA = "्"
    _JOINERS = {"\u200c", "\u200d"}

    @classmethod
    def contains_devanagari(cls, text):
        value = str(text or "")
        return any("\u0900" <= char <= "\u097f" for char in value)

    @classmethod
    def _lookup_consonant(cls, char, next_char=None):
        """Return the consonant mapping, including base+nukta sequences."""
        if next_char == cls._NUKTA:
            nukta_pairs = {
                "क": "q", "ख": "kh", "ग": "gh", "ज": "z",
                "ड": "r", "ढ": "rh", "फ": "f", "य": "y",
            }
            mapped = nukta_pairs.get(char)
            if mapped:
                return mapped
        return cls.CONSONANTS.get(char)

    @classmethod
    def _romanize_devanagari_run(cls, text):
        result = []
        index = 0

        while index < len(text):
            char = text[index]

            if char in cls._JOINERS:
                index += 1
                continue

            if char in cls.DEVANAGARI_DIGITS:
                result.append(cls.DEVANAGARI_DIGITS[char])
                index += 1
                continue

            if char in cls.INDEPENDENT_VOWELS:
                result.append(cls.INDEPENDENT_VOWELS[char])
                index += 1
                continue

            if char in cls.CONSONANTS:
                mapped = cls._lookup_consonant(
                    char,
                    text[index + 1] if index + 1 < len(text) else None,
                )
                consumed_nukta = (
                    index + 1 < len(text)
                    and text[index + 1] == cls._NUKTA
                )
                next_index = index + (2 if consumed_nukta else 1)

                if next_index < len(text) and text[next_index] == cls._VIRAMA:
                    result.append(mapped)
                    index = next_index + 1
                    continue

                if next_index < len(text) and text[next_index] in cls.MATRAS:
                    result.append(mapped + cls.MATRAS[text[next_index]])
                    index = next_index + 1
                    continue

                # Hindi's inherent 'a' is normally silent at the end of a
                # Devanagari word.  Keep it between consonants, but drop it
                # before the end of this run.
                next_is_end = next_index >= len(text)
                if next_is_end:
                    result.append(mapped)
                else:
                    result.append(mapped + "a")

                index = next_index
                continue

            if char in cls.MATRAS:
                result.append(cls.MATRAS[char])
                index += 1
                continue

            if char == cls._VIRAMA or char == cls._NUKTA:
                index += 1
                continue

            if char in cls.SPECIAL:
                result.append(cls.SPECIAL[char])
                index += 1
                continue

            result.append(char)
            index += 1

        return "".join(result)

    @classmethod
    def _collapse_transliteration(cls, value):
        value = re.sub(r"aa", "a", value)
        value = re.sub(r"ii", "i", value)
        value = re.sub(r"uu", "u", value)
        return value

    # Common Hindi command-language spellings are normalized to the Roman
    # forms already understood by Vyom's generic intent parser. This list is
    # language syntax only; it contains no application names.
    COMMAND_WORDS = {
        "नंबर": "number", "nanbar": "number", "क्रमांक": "kramank",
        "खोलो": "kholo", "खोलना": "kholna", "खोलिए": "kholiye", "खोलिये": "kholiye",
        "खोल": "khol", "ओपन": "open", "लॉन्च": "launch", "स्टार्ट": "start",
        "चालू": "chalu", "चलाओ": "chalao",
        "बंद": "band", "बंद करो": "band karo", "बंद कर": "band kar",
        "बंद कर दो": "band kar do", "रोक": "rok", "रोक दो": "rok do",
        "क्लोज": "close", "सर्च": "search", "फाइंड": "find",
        "लिखो": "likho", "लिखें": "likhen", "टाइप": "type", "टाइप करो": "type karo",
        "करो": "karo", "कर दो": "kar do", "कृपया": "kripya",
    }

    @classmethod
    def _normalize_command_words(cls, value):
        # Longest phrases first so "बंद कर दो" is not reduced to "बंद".
        for source in sorted(cls.COMMAND_WORDS, key=len, reverse=True):
            replacement = cls.COMMAND_WORDS[source]
            value = re.sub(r"(?<!\S)" + re.escape(source) + r"(?!\S)", replacement, value)
        return value

    @classmethod
    def normalize(cls, text):
        """Return the transcript in Latin/Roman script.

        English/Latin words are preserved as typed by the recognizer.  Only
        Devanagari segments and Devanagari digits are transformed.
        """
        original = unicodedata.normalize("NFC", str(text or ""))
        if not original.strip():
            return ""

        pieces = []
        index = 0

        while index < len(original):
            char = original[index]

            if "\u0900" <= char <= "\u097f":
                start = index
                while index < len(original) and (
                    "\u0900" <= original[index] <= "\u097f"
                    or original[index] in cls._JOINERS
                ):
                    index += 1
                run = original[start:index]
                converted = cls._romanize_devanagari_run(run)
                converted = cls._collapse_transliteration(converted)
                pieces.append(converted)
                continue

            pieces.append(char)
            index += 1

        value = "".join(pieces)
        value = re.sub(r"[\r\n\t]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        value = cls._normalize_command_words(value)
        return value


def normalize_voice_text(text):
    """Public voice-boundary helper used by STT and VoiceController."""
    return RomanTextNormalizer.normalize(text)


__all__ = ["RomanTextNormalizer", "normalize_voice_text"]
