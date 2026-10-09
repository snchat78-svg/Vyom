"""Website-backed factual lookup without a conversational AI provider.

The lookup layer retrieves concise article introductions/snippets directly from
Wikipedia and public web-search results. It never asks an LLM to generate facts.
Hindi pages are preferred by default; retrieved text is kept extractive and the
source title/domain is returned with the answer.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional


class _DuckDuckGoResults(HTMLParser):
    """Small dependency-free parser for DuckDuckGo HTML result markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: List[Dict[str, str]] = []
        self.current: Optional[Dict[str, str]] = None
        self._capture_key: Optional[str] = None
        self._capture_depth = 0
        self._capture_parts: List[str] = []

    @staticmethod
    def _clean_url(value: str) -> str:
        value = html.unescape(str(value or ""))
        parsed = urllib.parse.urlparse(value)
        query = urllib.parse.parse_qs(parsed.query)
        if query.get("uddg"):
            return query["uddg"][0]
        return value

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        classes = set(str(values.get("class") or "").split())

        if self._capture_key is not None:
            self._capture_depth += 1
            return

        if tag == "a" and "result__a" in classes:
            if self.current and self.current.get("title"):
                self.results.append(self.current)
            self.current = {
                "title": "",
                "url": self._clean_url(str(values.get("href") or "")),
                "snippet": "",
            }
            self._capture_key = "title"
            self._capture_depth = 1
            self._capture_parts = []
        elif "result__snippet" in classes:
            if self.current is None:
                self.current = {"title": "", "url": "", "snippet": ""}
            self._capture_key = "snippet"
            self._capture_depth = 1
            self._capture_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_key is not None:
            self._capture_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture_key is None:
            return
        self._capture_depth -= 1
        if self._capture_depth > 0:
            return
        value = re.sub(r"\s+", " ", html.unescape("".join(self._capture_parts))).strip()
        if self.current is not None:
            self.current[self._capture_key] = value
        self._capture_key = None
        self._capture_parts = []

    def finish(self) -> List[Dict[str, str]]:
        if self.current and self.current.get("title"):
            self.results.append(self.current)
        return [
            item for item in self.results
            if item.get("title") and item.get("snippet")
        ]


class WebKnowledge:
    """Searches public web sources and returns extractive answers."""

    _ROMAN_HINDI = {
        "india": "भारत", "bharat": "भारत", "rajasthan": "राजस्थान",
        "nepal": "नेपाल", "pakistan": "पाकिस्तान", "china": "चीन",
        "japan": "जापान", "russia": "रूस", "america": "अमेरिका",
        "ki": "की", "ka": "का", "ke": "के",
        "kya": "क्या", "hai": "है", "hain": "हैं", "tha": "था",
        "thi": "थी", "the": "थे", "rajadhani": "राजधानी",
        "rajdhani": "राजधानी", "kaun": "कौन", "kyu": "क्यों",
        "kyun": "क्यों", "kab": "कब", "kahan": "कहाँ",
        "kahaan": "कहाँ", "kaise": "कैसे", "kitna": "कितना",
        "kitni": "कितनी", "kitne": "कितने", "mein": "में",
        "me": "में", "kisne": "किसने", "kiska": "किसका",
        "kiski": "किसकी", "kisko": "किसको", "kise": "किसे",
        "pani": "पानी", "paanee": "पानी", "duniya": "दुनिया",
        "sabse": "सबसे", "bada": "बड़ा", "badi": "बड़ी",
        "bade": "बड़े", "hota": "होता", "hoti": "होती",
        "hote": "होते", "batao": "बताओ", "bataiye": "बताइए",
        "samjhao": "समझाओ", "kyon": "क्यों", "kaaran": "कारण",
    }

    def __init__(
        self,
        timeout: float = 3.5,
        opener: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.timeout = max(1.0, float(timeout))
        self._opener = opener or urllib.request.urlopen

    @classmethod
    def _query_variants(cls, question: str) -> List[str]:
        clean = re.sub(r"\s+", " ", str(question or "")).strip(" \t\r\n?？")
        if not clean:
            return []

        translated = cls._english_question_to_hindi(clean)
        converted = re.sub(
            r"\b[A-Za-z]+\b",
            lambda match: cls._ROMAN_HINDI.get(match.group(0).lower(), match.group(0)),
            clean,
        )
        variants = []
        if translated:
            variants.append(translated)
        if converted and converted.lower() != clean.lower():
            variants.append(converted)
        variants.append(clean)
        result = []
        for value in variants:
            if value and value not in result:
                result.append(value)
        return result[:2]

    @staticmethod
    def _english_question_to_hindi(question: str) -> str:
        value = str(question or "").strip().rstrip("?？. ").strip()
        patterns = (
            (r"what is (?:the )?capital of (.+)", r"\1 की राजधानी क्या है"),
            (r"what is (.+)", r"\1 क्या है"),
            (r"what are (.+)", r"\1 क्या हैं"),
            (r"who is (.+)", r"\1 कौन है"),
            (r"who was (.+)", r"\1 कौन था"),
            (r"where is (.+)", r"\1 कहाँ है"),
            (r"when was (.+)", r"\1 कब था"),
            (r"why is (.+)", r"\1 क्यों है"),
            (r"how does (.+) work", r"\1 कैसे काम करता है"),
            (r"how to (.+)", r"\1 कैसे करें"),
        )
        for pattern, replacement in patterns:
            match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
            if match:
                return re.sub(
                    r"\\b[A-Za-z]+\\b",
                    lambda token: WebKnowledge._ROMAN_HINDI.get(token.group(0).lower(), token.group(0)),
                    re.sub(pattern, replacement, value, flags=re.IGNORECASE),
                )
        return ""

    @staticmethod
    def _clean_markup(value: Any) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _trim_summary(value: str, limit: int = 900) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(text) <= limit:
            return text
        shortened = text[:limit].rsplit(" ", 1)[0].strip()
        return shortened + "…"

    def _read_url(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VyomLocalKnowledge/1.0 (+https://github.com/snchat78-svg/Vyom)",
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "Accept-Language": "hi-IN,hi;q=0.9,en;q=0.7",
            },
        )
        with self._opener(request, timeout=self.timeout) as response:
            raw = response.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        return str(raw or "")

    def _wikipedia(self, query: str, language: str) -> Optional[Dict[str, Any]]:
        api = "https://" + language + ".wikipedia.org/w/api.php?"
        search_url = api + urllib.parse.urlencode({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": "3",
            "format": "json",
            "utf8": "1",
        })
        try:
            search_data = json.loads(self._read_url(search_url))
            candidates = search_data.get("query", {}).get("search", [])
        except Exception:
            return None

        for candidate in candidates[:3]:
            title = str(candidate.get("title") or "").strip()
            if not title:
                continue
            summary = self._clean_markup(candidate.get("snippet") or "")
            page_url = "https://" + language + ".wikipedia.org/wiki/" + urllib.parse.quote(
                title.replace(" ", "_")
            )
            extract_url = api + urllib.parse.urlencode({
                "action": "query",
                "prop": "extracts",
                "exintro": "1",
                "explaintext": "1",
                "redirects": "1",
                "titles": title,
                "format": "json",
                "utf8": "1",
            })
            try:
                extract_data = json.loads(self._read_url(extract_url))
                pages = extract_data.get("query", {}).get("pages", {})
                if isinstance(pages, dict):
                    page = next(iter(pages.values()), {})
                    extract = str(page.get("extract") or "").strip()
                    if extract:
                        summary = extract
                        page_url = str(page.get("fullurl") or page_url)
            except Exception:
                pass

            summary = self._trim_summary(summary)
            if not summary:
                continue
            language_label = "हिन्दी" if language == "hi" else "अंग्रेज़ी"
            if language == "hi":
                answer = summary + "\nस्रोत: विकिपीडिया (हिन्दी) — " + title
            else:
                answer = (
                    "हिन्दी विकिपीडिया पर उपयुक्त लेख नहीं मिला। अंग्रेज़ी "
                    "विकिपीडिया में उपलब्ध जानकारी: " + summary
                    + "\nस्रोत: Wikipedia (English) — " + title
                )
            return {
                "success": True,
                "answer": answer,
                "query": query,
                "language": language,
                "source": {"title": title, "url": page_url, "site": language_label + " Wikipedia"},
            }
        return None

    def _duckduckgo(self, query: str, preferred_language: str) -> Optional[Dict[str, Any]]:
        url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({
            "q": query,
            "kl": "in-hi" if preferred_language == "hi" else "wt-wt",
        })
        try:
            parser = _DuckDuckGoResults()
            parser.feed(self._read_url(url))
            candidates = parser.finish()
        except Exception:
            return None
        if not candidates:
            return None

        if preferred_language == "hi":
            hindi_candidates = [
                item for item in candidates
                if re.search(r"[\u0900-\u097F]", item.get("snippet", ""))
            ]
            selected = hindi_candidates[0] if hindi_candidates else candidates[0]
        else:
            selected = candidates[0]

        title = self._clean_markup(selected.get("title"))
        snippet = self._trim_summary(self._clean_markup(selected.get("snippet")), 700)
        source_url = str(selected.get("url") or "").strip()
        if not snippet:
            return None

        has_hindi = bool(re.search(r"[\u0900-\u097F]", snippet))
        if preferred_language == "hi" and not has_hindi:
            answer = (
                "हिन्दी स्रोत का अंश नहीं मिला; वेबसाइट के मूल अंग्रेज़ी अंश के "
                "आधार पर: " + snippet
            )
        else:
            answer = snippet
        if title:
            answer += "\nस्रोत: " + title
        return {
            "success": True,
            "answer": answer,
            "query": query,
            "language": "hi" if has_hindi else "en",
            "source": {"title": title, "url": source_url, "site": "वेब खोज"},
        }

    def answer(self, question: str, preferred_language: str = "hi") -> Dict[str, Any]:
        """Return a sourced, extractive answer; never call an AI chat model."""
        variants = self._query_variants(question)
        if not variants:
            return {"success": False, "answer": "", "sources": [], "reason": "empty_query"}

        preferred = "en" if str(preferred_language or "hi").lower().startswith("en") else "hi"
        order = [preferred, "en" if preferred == "hi" else "hi"]

        # Prefer Hindi pages and transliterated Hindi queries where available.
        for language in order:
            for query in variants[:1]:
                result = self._wikipedia(query, language)
                if result:
                    result["sources"] = [result.get("source", {})]
                    return result

        # Search the web directly if Wikipedia has no suitable article.
        query = variants[0]
        result = self._duckduckgo(query, preferred)
        if result:
            result["sources"] = [result.get("source", {})]
            return result

        # One final attempt with the user's original wording on the other
        # Wikipedia language, capped to avoid long delays on poor networks.
        if len(variants) > 1:
            result = self._wikipedia(variants[-1], order[-1])
            if result:
                result["sources"] = [result.get("source", {})]
                return result

        return {
            "success": False,
            "answer": "",
            "sources": [],
            "query": question,
            "reason": "no_source_or_network_unavailable",
        }


__all__ = ["WebKnowledge"]
