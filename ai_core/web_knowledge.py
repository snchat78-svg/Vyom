"""Website-backed factual lookup without a conversational AI provider.

The lookup layer retrieves concise article introductions/snippets directly from
Wikipedia and public web-search results. It never asks an LLM to generate facts.
Hindi pages are preferred by default; retrieved text is kept extractive and the
source title/domain is returned with the answer.
"""
from __future__ import annotations

import html
import ipaddress
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import time
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


class _ReadablePageParser(HTMLParser):
    """Extract readable title, description, headings, and paragraphs."""

    _SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}
    _VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.headings: List[str] = []
        self.paragraphs: List[str] = []
        self._capture: Optional[str] = None
        self._capture_depth = 0
        self._capture_parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = str(tag or "").lower()
        attributes = dict(attrs)
        if self._skip_depth:
            if tag not in self._VOID_TAGS:
                self._skip_depth += 1
            return
        if tag in self._SKIP_TAGS:
            self._skip_depth = 1
            return
        if tag == "meta":
            key = str(attributes.get("name") or attributes.get("property") or "").lower()
            content = re.sub(r"\s+", " ", str(attributes.get("content") or "")).strip()
            if key in {"description", "og:description", "twitter:description"} and content and not self.description:
                self.description = content
            return
        if self._capture:
            if tag not in self._VOID_TAGS:
                self._capture_depth += 1
            return
        if tag in {"title", "h1", "h2", "p"}:
            self._capture = tag
            self._capture_depth = 1
            self._capture_parts = []

    def handle_endtag(self, tag):
        tag = str(tag or "").lower()
        if self._skip_depth:
            if tag not in self._VOID_TAGS:
                self._skip_depth -= 1
            return
        if not self._capture or tag in self._VOID_TAGS:
            return
        self._capture_depth -= 1
        if self._capture_depth > 0:
            return
        value = re.sub(r"\s+", " ", html.unescape("".join(self._capture_parts))).strip()
        if value:
            if self._capture == "title":
                self.title = value
            elif self._capture in {"h1", "h2"} and value not in self.headings:
                self.headings.append(value)
            elif self._capture == "p" and value not in self.paragraphs:
                self.paragraphs.append(value)
        self._capture = None
        self._capture_parts = []

    def handle_data(self, data):
        if self._capture and not self._skip_depth:
            self._capture_parts.append(data)

    def extract(self) -> str:
        parts = []
        for value in [self.description] + self.headings + self.paragraphs[:5]:
            clean = re.sub(r"\s+", " ", str(value or "")).strip()
            if clean and clean not in parts:
                parts.append(clean)
        return " ".join(parts)


class _PublicOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects to URLs the public-source fetcher would not request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not WebKnowledge._is_public_web_url(newurl):
            raise urllib.error.HTTPError(
                req.full_url,
                code,
                "Blocked redirect to a non-public URL",
                headers,
                fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class WebKnowledge:
    """Searches public web sources and returns extractive answers."""

    _ROMAN_HINDI = {
        "india": "भारत", "bharat": "भारत", "rajasthan": "राजस्थान",
        "nepal": "नेपाल", "pakistan": "पाकिस्तान", "china": "चीन", "japan": "जापान",
        "russia": "रूस", "america": "अमेरिका", "goa": "गोवा", "gova": "गोवा", "delhi": "दिल्ली",
        "ki": "की", "ka": "का", "ke": "के", "k": "का", "kya": "क्या", "hai": "है",
        "hain": "हैं", "ha": "है", "he": "है", "tha": "था", "thi": "थी", "the": "थे",
        "men": "में", "mein": "में", "me": "में", "main": "में", "kul": "कुल",
        "rajadhani": "राजधानी", "rajdhani": "राजधानी", "kaun": "कौन", "kyu": "क्यों",
        "kyun": "क्यों", "kyon": "क्यों", "kab": "कब", "kahan": "कहाँ", "kahaan": "कहाँ",
        "kaise": "कैसे", "kitna": "कितना", "kitana": "कितना", "kitanaa": "कितना",
        "kitni": "कितनी", "kitani": "कितनी", "kitnee": "कितनी", "kitne": "कितने",
        "kitane": "कितने", "kitney": "कितने", "kitnay": "कितने", "kis": "किस",
        "kise": "किसे", "kiska": "किसका", "kiski": "किसकी", "kiske": "किसके",
        "kisne": "किसने", "kisko": "किसको", "rajy": "राज्य", "rajya": "राज्य",
        "rashtriy": "राष्ट्रीय", "rashtriya": "राष्ट्रीय", "pakshi": "पक्षी",
        "kshetraphal": "क्षेत्रफल", "kshetrafal": "क्षेत्रफल", "ksetraphal": "क्षेत्रफल",
        "area": "क्षेत्रफल", "ganv": "गाँव", "gaon": "गाँव", "gaav": "गाँव",
        "jila": "जिला", "jile": "जिले", "zilla": "जिला", "zila": "जिला", "zile": "जिले",
        "pashu": "पशु", "pasu": "पशु", "sa": "सा", "se": "से", "state": "राज्य", "district": "जिला",
        "nam": "नाम", "naam": "नाम", "tumhara": "तुम्हारा", "tumhari": "तुम्हारी",
        "mera": "मेरा", "meri": "मेरी", "mere": "मेरे", "pani": "पानी", "paanee": "पानी",
        "duniya": "दुनिया", "sabse": "सबसे", "bada": "बड़ा", "badi": "बड़ी", "bade": "बड़े",
        "hota": "होता", "hoti": "होती", "hote": "होते", "batao": "बताओ", "bataiye": "बताइए",
        "samjhao": "समझाओ", "kaaran": "कारण", "bird": "पक्षी",
    }

    def __init__(
        self,
        timeout: float = 1.8,
        total_timeout: float = 6.0,
        opener: Optional[Callable[..., Any]] = None,
        max_response_bytes: int = 1_000_000,
    ) -> None:
        # Each socket request is short, and the complete lookup has its own
        # deadline. A series of failed sources must not freeze a voice turn for
        # several independent per-request timeouts.
        self.timeout = min(2.0, max(1.0, float(timeout)))
        self.total_timeout = min(8.0, max(2.0, float(total_timeout)))
        try:
            configured_limit = int(max_response_bytes)
        except (TypeError, ValueError, OverflowError):
            configured_limit = 1_000_000
        self.max_response_bytes = min(1_000_000, max(1, configured_limit))
        self._deadline: Optional[float] = None
        self._opener = opener or urllib.request.build_opener(
            _PublicOnlyRedirectHandler()
        ).open

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
        # Keep a complete Hindi query first and preserve the exact query second.
        variants = [translated, clean] if translated else [converted, clean]
        result = []
        for value in variants:
            value = re.sub(r"\s+", " ", str(value or "")).strip()
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
                    r"\b[A-Za-z]+\b",
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

    @staticmethod
    def _is_public_web_url(url: str) -> bool:
        """Reject non-web schemes, credential URLs, and obvious private targets."""
        try:
            parsed = urllib.parse.urlparse(str(url or "").strip())
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                return False
            if parsed.username or parsed.password:
                return False
            host = parsed.hostname.lower().rstrip(".")
            if host in {"localhost", "localhost.localdomain"} or host.endswith(
                (".localhost", ".local", ".internal", ".test")
            ):
                return False
            try:
                address = ipaddress.ip_address(host)
                if not address.is_global:
                    return False
            except ValueError:
                pass
            return True
        except Exception:
            return False

    def _extract_webpage(self, url: str, preferred_language: str) -> Optional[Dict[str, Any]]:
        """Extract a bounded summary from a public search result."""
        if not self._is_public_web_url(url):
            return None
        if self._deadline is not None and time.monotonic() >= self._deadline:
            return None
        try:
            page = self._read_url(url)
            parser = _ReadablePageParser()
            parser.feed(page)
            summary = self._trim_summary(parser.extract(), 1200)
        except Exception:
            return None
        if len(summary) < 40:
            return None
        parsed = urllib.parse.urlparse(url)
        title = parser.title or (parsed.hostname or "Web page")
        has_hindi = bool(re.search(r"[\u0900-\u097F]", summary))
        answer = summary
        if preferred_language == "hi" and not has_hindi:
            answer = "वेबसाइट का मूल अंग्रेज़ी अंश: " + summary
        answer += "\nस्रोत: " + title
        return {
            "success": True,
            "answer": answer,
            "query": url,
            "language": "hi" if has_hindi else "en",
            "evidence_type": "webpage_extract",
            "evidence_text": summary,
            "source": {"title": title, "url": url, "site": parsed.hostname or "वेबसाइट"},
        }

    def _read_url(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VyomLocalKnowledge/1.0 (+https://github.com/snchat78-svg/Vyom)",
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "Accept-Language": "hi-IN,hi;q=0.9,en;q=0.7",
            },
        )
        request_timeout = self.timeout
        if self._deadline is not None:
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Web knowledge lookup deadline reached.")
            request_timeout = min(request_timeout, remaining)
        with self._opener(request, timeout=request_timeout) as response:
            try:
                raw = response.read(self.max_response_bytes + 1)
            except TypeError:
                # Retain compatibility with simple injected test/readers that
                # implement read() but not the standard optional size argument.
                raw = response.read()
        if isinstance(raw, bytes):
            if len(raw) > self.max_response_bytes:
                raise ValueError("Web response exceeded the configured byte limit.")
            return raw.decode("utf-8", errors="replace")
        text = str(raw or "")
        if len(text.encode("utf-8", errors="replace")) > self.max_response_bytes:
            raise ValueError("Web response exceeded the configured byte limit.")
        return text

    def _wikipedia(self, query: str, language: str, output_language: str = "hi") -> Optional[Dict[str, Any]]:
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

        for candidate in candidates[:1]:
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
                        candidate_url = str(page.get("fullurl") or "").strip()
                        if candidate_url and self._is_public_web_url(candidate_url):
                            page_url = candidate_url
            except Exception:
                pass

            summary = self._trim_summary(summary)
            if not summary:
                continue
            language_label = "हिन्दी" if language == "hi" else "अंग्रेज़ी"
            if language == "hi":
                answer = summary + "\nस्रोत: विकिपीडिया (हिन्दी) — " + title
            elif output_language == "hi":
                answer = (
                    "हिन्दी विकिपीडिया पर उपयुक्त लेख नहीं मिला। अंग्रेज़ी "
                    "विकिपीडिया से मिला अंश: " + summary
                    + "\nस्रोत: Wikipedia (English) — " + title
                )
            else:
                answer = summary + "\nSource: Wikipedia (English) — " + title
            return {
                "success": True,
                "answer": answer,
                "query": query,
                "language": language,
                "evidence_type": "encyclopedia_extract",
                "evidence_text": summary,
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
        # A search snippet without a safe public citation is not a usable answer.
        if not self._is_public_web_url(source_url):
            return None
        if not snippet and not source_url:
            return None
        # Prefer readable text from a public result page when available.
        page_result = self._extract_webpage(source_url, preferred_language) if source_url else None
        if page_result:
            return page_result
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
            "evidence_type": "search_result_snippet",
            "evidence_text": snippet,
            "source": {"title": title, "url": source_url, "site": "वेब खोज"},
        }

    @staticmethod
    def _source_host(source: Dict[str, Any]) -> str:
        """Return a normalized hostname, not an assertion of publisher independence."""
        try:
            parsed = urllib.parse.urlparse(str(source.get("url") or "").strip())
            host = (parsed.hostname or "").lower().rstrip(".")
            return host[4:] if host.startswith("www.") else host
        except Exception:
            return ""

    @staticmethod
    def _sentence_facts(text: str) -> List[Dict[str, Any]]:
        """Extract language-agnostic token context and numeric/date-like values."""
        sentences = re.split(r"(?<=[.!?।])\\s+|[\\r\\n]+", str(text or ""))
        facts: List[Dict[str, Any]] = []
        for sentence in sentences:
            value = sentence.strip()
            if not value:
                continue
            terms = {
                token.casefold()
                for token in re.findall(r"[^\\W_]+", value, flags=re.UNICODE)
                if not token.isdigit()
            }
            numbers = set(
                re.findall(r"(?<!\\w)\\d+(?:[.,:/-]\\d+)*(?:%|[A-Za-z]+)?", value)
            )
            if terms:
                facts.append({"terms": terms, "numbers": numbers})
        return facts

    @classmethod
    def _compare_source_evidence(cls, sources: List[Dict[str, Any]]) -> str:
        """Conservatively compare retrieved excerpts without inventing semantic certainty."""
        if len(sources) < 2:
            return "single_source"

        excerpts = [
            cls._sentence_facts(str(source.get("excerpt") or ""))
            for source in sources
        ]
        potential_numeric_conflict = False
        textually_aligned = False

        for left_index in range(len(excerpts)):
            for right_index in range(left_index + 1, len(excerpts)):
                for left in excerpts[left_index]:
                    for right in excerpts[right_index]:
                        left_terms = left["terms"]
                        right_terms = right["terms"]
                        smaller_context = min(len(left_terms), len(right_terms))
                        if smaller_context == 0:
                            continue
                        shared = len(left_terms & right_terms)
                        context_coverage = shared / smaller_context

                        # Only flag a *potential* conflict when sentence context
                        # substantially overlaps and both excerpts report numeric
                        # or date-like values that differ. This is deliberately
                        # not a claim that every natural-language contradiction
                        # can be recognized without a semantic model.
                        if (
                            context_coverage >= 0.65
                            and left["numbers"]
                            and right["numbers"]
                            and left["numbers"] != right["numbers"]
                        ):
                            potential_numeric_conflict = True
                            break

                        union_size = len(left_terms | right_terms)
                        similarity = shared / union_size if union_size else 0.0
                        if (
                            similarity >= 0.72
                            and left["numbers"] == right["numbers"]
                        ):
                            textually_aligned = True
                    if potential_numeric_conflict:
                        break
                if potential_numeric_conflict:
                    break
            if potential_numeric_conflict:
                break

        if potential_numeric_conflict:
            return "potential_numeric_conflict"
        if textually_aligned:
            return "textually_aligned"
        return "divergent_unresolved"

    @staticmethod
    def _unknown_result(question: str, reason: str) -> Dict[str, Any]:
        """Return an honest unknown result with explicit evidence limits."""
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "query": question,
            "reason": reason,
            "answer_status": "unknown",
            "evidence": {
                "type": "none",
                "source_count": 0,
                "inference_used": False,
                "independent_corroboration": "not_checked",
                "source_content_trust": "untrusted",
            },
        }

    def answer(self, question: str, preferred_language: str = "hi") -> Dict[str, Any]:
        """Return a sourced, extractive answer; never call an AI chat model."""
        variants = self._query_variants(question)
        if not variants:
            return self._unknown_result(question, "empty_query")

        preferred = "en" if str(preferred_language or "hi").lower().startswith("en") else "hi"
        other = "en" if preferred == "hi" else "hi"
        previous_deadline = self._deadline
        new_deadline = time.monotonic() + self.total_timeout
        self._deadline = min(previous_deadline, new_deadline) if previous_deadline else new_deadline

        # Keep the order useful for Hindi/Hinglish: normalized preferred-
        # language Wikipedia, the original query on the preferred wiki, then
        # a clearly labelled cross-language/search fallback. _read_url enforces
        # the same overall deadline at every network boundary.
        try:
            attempts = [(variants[0], preferred, preferred)]
            if len(variants) > 1:
                attempts.append((variants[1], preferred, preferred))
                attempts.append((variants[1], other, preferred))
            attempts.extend((query, "ddg", preferred) for query in variants)

            collected: List[Dict[str, Any]] = []
            for query, source_language, output_language in attempts:
                if self._deadline is not None and time.monotonic() >= self._deadline:
                    break
                if source_language == "ddg":
                    result = self._duckduckgo(query, preferred)
                else:
                    result = self._wikipedia(query, source_language, output_language=output_language)
                if not result:
                    continue
                source = result.get("source")
                if (
                    not isinstance(source, dict)
                    or not self._is_public_web_url(source.get("url", ""))
                ):
                    # Never present a factual excerpt without a safe citation.
                    continue
                collected.append(result)

            if not collected:
                reason = (
                    "lookup_deadline_exceeded"
                    if self._deadline is not None and time.monotonic() >= self._deadline
                    else "no_source_or_network_unavailable"
                )
                return self._unknown_result(question, reason)

            # Preserve the first usable result as the primary excerpt, then add
            # only additional distinct hostnames. Different hosts are not proof
            # of independent publishers, so provenance remains explicitly cautious.
            primary = dict(collected[0])
            sources: List[Dict[str, Any]] = []
            seen_hosts = set()
            for candidate in collected:
                source = candidate.get("source")
                if not isinstance(source, dict):
                    continue
                host = self._source_host(source)
                if not host or host in seen_hosts:
                    continue
                seen_hosts.add(host)
                excerpt = self._trim_summary(
                    str(candidate.get("evidence_text") or ""), 1200
                )
                source_entry = {
                    "title": str(source.get("title") or "")[:240],
                    "url": str(source.get("url") or ""),
                    "site": str(source.get("site") or host)[:160],
                    "host": host,
                    "excerpt": excerpt,
                }
                sources.append(source_entry)

            if not sources:
                return self._unknown_result(question, "no_safe_source_after_validation")

            relation = self._compare_source_evidence(sources)
            primary["sources"] = sources
            primary.pop("source", None)
            primary.pop("evidence_text", None)
            primary["evidence_type"] = str(primary.get("evidence_type") or "source_excerpt")
            primary["evidence"] = {
                "type": primary["evidence_type"],
                "source_count": len(sources),
                "inference_used": False,
                "independent_corroboration": "not_established",
                "source_content_trust": "untrusted",
                "cross_source_relation": relation,
            }
            primary["limitations"] = []
            if relation == "single_source":
                primary["answer_status"] = "sourced_excerpt"
                primary["limitations"].append(
                    "Only one distinct hostname was available; independent corroboration was not established."
                )
            elif relation == "textually_aligned":
                primary["answer_status"] = "sourced_excerpt"
                primary["limitations"].append(
                    "Retrieved excerpts have strong textual overlap, but publisher independence and factual correctness were not established."
                )
            elif relation == "potential_numeric_conflict":
                primary["answer_status"] = "conflicting_sources"
                if preferred == "en":
                    primary["answer"] = (
                        "The retrieved sources differ on numeric or date-like values in similar sentence contexts. "
                        "I cannot resolve that conflict reliably from these excerpts; treat the claim as unresolved "
                        "and compare the cited sources before relying on either value."
                    )
                else:
                    primary["answer"] = (
                        "मिले हुए स्रोतों में मिलते-जुलते संदर्भ के संख्यात्मक या तारीख़-संबंधी दावों में अंतर है। "
                        "इन अंशों से इस अंतर का भरोसेमंद समाधान नहीं हो सका; किसी एक मान को निश्चित न मानें और "
                        "नीचे दिए स्रोतों की तुलना करें।"
                    )
                primary["limitations"].append(
                    "A potential numeric/date conflict was detected by generic sentence-context overlap; broader semantic conflicts may remain undetected."
                )
            else:
                primary["answer_status"] = "sourced_excerpt"
                primary["limitations"].append(
                    "Multiple hostnames returned excerpts, but their claims did not align closely enough to confirm agreement or a specific conflict."
                )
            primary["query"] = question
            return primary
        finally:
            self._deadline = previous_deadline



__all__ = ["WebKnowledge"]
