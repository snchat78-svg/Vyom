import io
import json
import unittest
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse

from ai_core.web_knowledge import WebKnowledge, _PublicOnlyRedirectHandler


class FakeResponse:
    def __init__(self, value):
        self.value = value.encode("utf-8") if isinstance(value, str) else value

    def read(self):
        return self.value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class WebKnowledgeTests(unittest.TestCase):
    def test_roman_hindi_query_is_normalized_for_hindi_wikipedia(self):
        variants = WebKnowledge._query_variants("bharat ki rajadhani kya hai")
        self.assertEqual(variants[0], "भारत की राजधानी क्या है")

    def test_english_question_is_rewritten_as_hindi_search_query(self):
        variants = WebKnowledge._query_variants("what is the capital of India?")
        self.assertEqual(variants[0], "भारत की राजधानी क्या है")

    def test_stt_roman_hindi_spelling_generates_hindi_search_query(self):
        variants = WebKnowledge._query_variants(
            "rajasthan men gova ka kshetraphal kitana hai"
        )
        self.assertEqual(variants[0], "राजस्थान में गोवा का क्षेत्रफल कितना है")

    def test_english_question_uses_hindi_query_and_preserves_original(self):
        variants = WebKnowledge._query_variants("what is the capital of India?")
        self.assertEqual(variants[0], "भारत की राजधानी क्या है")
        self.assertEqual(variants[1], "what is the capital of India")

    def test_wikipedia_answer_is_extractive_and_has_a_source(self):
        calls = []

        def opener(request, timeout=0):
            parsed = urlparse(request.full_url)
            params = parse_qs(parsed.query)
            calls.append(request.full_url)
            if params.get("list") == ["search"]:
                payload = {
                    "query": {"search": [{
                        "title": "भारत",
                        "snippet": "भारत दक्षिण एशिया में स्थित एक देश है।",
                    }]}
                }
            elif params.get("prop") == ["extracts"]:
                payload = {
                    "query": {"pages": {"1": {
                        "title": "भारत",
                        "extract": "भारत दक्षिण एशिया में स्थित एक देश है। इसकी राजधानी नई दिल्ली है।",
                        "fullurl": "https://hi.wikipedia.org/wiki/भारत",
                    }}}
                }
            else:
                payload = {}
            return FakeResponse(json.dumps(payload, ensure_ascii=False))

        client = WebKnowledge(opener=opener)
        result = client.answer("bharat ki rajadhani kya hai")

        self.assertTrue(result["success"])
        self.assertIn("नई दिल्ली", result["answer"])
        self.assertIn("विकिपीडिया", result["answer"])
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(result["answer_status"], "sourced_excerpt")
        self.assertEqual(result["evidence_type"], "encyclopedia_extract")
        self.assertEqual(result["evidence"]["source_count"], 1)
        self.assertFalse(result["evidence"]["inference_used"])
        self.assertEqual(result["evidence"]["independent_corroboration"], "not_checked")
        self.assertEqual(result["evidence"]["source_content_trust"], "untrusted")
        self.assertTrue(result["sources"][0]["url"].startswith("https://"))
        self.assertEqual(result["source"]["url"], result["sources"][0]["url"])


    def test_public_redirect_handler_blocks_local_and_private_destinations(self):
        handler = _PublicOnlyRedirectHandler()
        request = urllib.request.Request("https://example.com/start")
        unsafe_targets = (
            "http://127.0.0.1/private",
            "http://169.254.169.254/latest/meta-data",
            "http://localhost/secret",
            "file:///etc/passwd",
        )
        for target in unsafe_targets:
            with self.subTest(target=target):
                with self.assertRaises(urllib.error.HTTPError):
                    handler.redirect_request(
                        request, None, 302, "Found", None, target
                    )

    def test_read_url_enforces_a_hard_response_byte_limit(self):
        class SizedResponse(FakeResponse):
            def read(self, size=-1):
                return self.value if size < 0 else self.value[:size]

        def opener(_request, timeout=0):
            return SizedResponse(b"0123456789abcdef")

        client = WebKnowledge(opener=opener, max_response_bytes=8)
        with self.assertRaisesRegex(ValueError, "byte limit"):
            client._read_url("https://example.com/page")

    def test_unknown_result_does_not_claim_a_source_or_inference(self):
        def opener(_request, timeout=0):
            return FakeResponse("{}")

        result = WebKnowledge(opener=opener).answer("some unknown fact")

        self.assertFalse(result["success"])
        self.assertEqual(result["answer_status"], "unknown")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["evidence"]["type"], "none")
        self.assertEqual(result["evidence"]["source_count"], 0)
        self.assertFalse(result["evidence"]["inference_used"])
        self.assertEqual(result["evidence"]["source_content_trust"], "untrusted")


    @staticmethod
    def _mock_source(excerpt, url, title):
        from urllib.parse import urlparse
        return {
            "success": True,
            "answer": excerpt + "\\nSource: " + title,
            "query": "test query",
            "language": "en",
            "evidence_type": "webpage_extract",
            "evidence_text": excerpt,
            "source": {"title": title, "url": url, "site": urlparse(url).hostname},
        }

    def test_multiple_sources_flag_numeric_disagreement_as_unresolved(self):
        client = WebKnowledge(total_timeout=2.0)
        results = {
            "hi": self._mock_source(
                "Region X had a population of 1,200 people in 2020.",
                "https://statistics.example.gov/region-x", "Statistics report",
            ),
            "en": self._mock_source(
                "Region X had a population of 1,400 people in 2020.",
                "https://data.example.org/region-x", "Data report",
            ),
        }
        client._query_variants = lambda question: ["variant one", "variant two"]
        client._wikipedia = lambda query, language, output_language="hi": results[language]
        client._duckduckgo = lambda query, preferred_language: None

        result = client.answer("population of Region X")

        self.assertTrue(result["success"])
        self.assertEqual(result["answer_status"], "conflicting_sources")
        self.assertEqual(result["evidence"]["cross_source_relation"], "potential_numeric_conflict")
        self.assertEqual(result["evidence"]["source_count"], 2)
        self.assertEqual(result["evidence"]["independent_corroboration"], "not_established")
        self.assertIn("अंतर", result["answer"])
        self.assertEqual(
            {item["host"] for item in result["sources"]},
            {"statistics.example.gov", "data.example.org"},
        )

    def test_multiple_sources_with_matching_text_are_only_textually_aligned(self):
        client = WebKnowledge(total_timeout=2.0)
        excerpt = "Region X covers an area of 500 square kilometres."
        results = {
            "hi": self._mock_source(excerpt, "https://facts.example.gov/region-x", "Fact sheet"),
            "en": self._mock_source(excerpt, "https://records.example.org/region-x", "Record"),
        }
        client._query_variants = lambda question: ["variant one", "variant two"]
        client._wikipedia = lambda query, language, output_language="hi": results[language]
        client._duckduckgo = lambda query, preferred_language: None

        result = client.answer("area of Region X")

        self.assertEqual(result["answer_status"], "sourced_excerpt")
        self.assertEqual(result["evidence"]["cross_source_relation"], "textually_aligned")
        self.assertEqual(result["evidence"]["source_count"], 2)
        self.assertEqual(result["evidence"]["independent_corroboration"], "not_established")
        self.assertTrue(any("publisher independence" in item for item in result["limitations"]))

    def test_different_excerpts_without_numeric_conflict_remain_unresolved(self):
        client = WebKnowledge(total_timeout=2.0)
        results = {
            "hi": self._mock_source(
                "Region X was founded by local communities and developed over many years.",
                "https://history.example.gov/region-x", "History page",
            ),
            "en": self._mock_source(
                "Region X is known for culture and has many historical sites.",
                "https://culture.example.org/region-x", "Culture page",
            ),
        }
        client._query_variants = lambda question: ["variant one", "variant two"]
        client._wikipedia = lambda query, language, output_language="hi": results[language]
        client._duckduckgo = lambda query, preferred_language: None

        result = client.answer("history of Region X")

        self.assertEqual(result["answer_status"], "sourced_excerpt")
        self.assertEqual(result["evidence"]["cross_source_relation"], "divergent_unresolved")
        self.assertEqual(result["evidence"]["source_count"], 2)
        self.assertTrue(any("did not align closely enough" in item for item in result["limitations"]))

    def test_same_hostname_is_not_counted_as_two_sources(self):
        client = WebKnowledge(total_timeout=2.0)
        results = {
            "hi": self._mock_source("The area is 500 square kilometres.", "https://www.example.com/one", "First page"),
            "en": self._mock_source("The area is 500 square kilometres.", "https://example.com/two", "Second page"),
        }
        client._query_variants = lambda question: ["variant one", "variant two"]
        client._wikipedia = lambda query, language, output_language="hi": results[language]
        client._duckduckgo = lambda query, preferred_language: None

        result = client.answer("area")

        self.assertEqual(result["evidence"]["source_count"], 1)
        self.assertEqual(result["evidence"]["cross_source_relation"], "single_source")

if __name__ == "__main__":
    unittest.main()
