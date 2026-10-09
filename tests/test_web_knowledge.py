import io
import json
import unittest
from urllib.parse import parse_qs, urlparse

from ai_core.web_knowledge import WebKnowledge


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


if __name__ == "__main__":
    unittest.main()
