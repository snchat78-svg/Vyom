import io
from datetime import datetime, timezone
import json
import socket
import unittest
import urllib.error
import urllib.request
from unittest import mock
from urllib.parse import parse_qs, urlparse

from ai_core.web_knowledge import (
    RetrievalProvider,
    WebKnowledge,
    _PinnedPublicHTTPConnection,
    _PinnedPublicHTTPSConnection,
    _PinnedPublicHTTPHandler,
    _PinnedPublicHTTPSHandler,
    _PublicOnlyRedirectHandler,
)


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
    @staticmethod
    def _provider_result(
        url="https://facts.example.org/item",
        excerpt="A bounded custom provider excerpt with source-grounded information.",
        title="Custom source",
        site="Example facts",
    ):
        return {
            "success": True,
            "answer": excerpt,
            "query": "test query",
            "language": "en",
            "evidence_type": "custom_provider_excerpt",
            "evidence_text": excerpt,
            "source": {"title": title, "url": url, "site": site},
        }

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

    @staticmethod
    def _resolver_for(*addresses):
        def resolve(host, port, type=0):
            records = []
            for address in addresses:
                if ":" in address:
                    sockaddr = (address, port, 0, 0)
                    family = socket.AF_INET6
                else:
                    sockaddr = (address, port)
                    family = socket.AF_INET
                records.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr))
            return records
        return resolve

    def test_dns_guard_rejects_mixed_public_and_private_answers(self):
        resolver = self._resolver_for("93.184.216.34", "10.0.0.8")
        self.assertFalse(
            WebKnowledge._dns_destination_is_public("https://example.com/page", resolver)
        )

    def test_dns_guard_rejects_resolution_failures_and_empty_answers(self):
        def failed_resolver(host, port, type=0):
            raise OSError("simulated DNS failure")

        self.assertFalse(
            WebKnowledge._dns_destination_is_public("https://example.com/page", failed_resolver)
        )
        self.assertFalse(
            WebKnowledge._dns_destination_is_public("https://example.com/page", lambda host, port, type=0: [])
        )

    def test_read_url_blocks_private_dns_answers_before_opening_connection(self):
        calls = []
        def opener(request, timeout=0):
            calls.append(request.full_url)
            return FakeResponse("must not be fetched")

        client = WebKnowledge(
            opener=opener,
            resolver=self._resolver_for("127.0.0.1"),
        )
        with self.assertRaisesRegex(ValueError, "public addresses"):
            client._read_url("https://example.com/private")
        self.assertEqual(calls, [])

    def test_read_url_allows_exclusively_public_dns_answers(self):
        calls = []
        def opener(request, timeout=0):
            calls.append(request.full_url)
            return FakeResponse("public content")

        client = WebKnowledge(
            opener=opener,
            resolver=self._resolver_for("93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"),
        )
        self.assertEqual(client._read_url("https://example.com/page"), "public content")
        self.assertEqual(len(calls), 1)

    def test_pinned_http_connection_uses_validated_numeric_sockaddr(self):
        resolver_calls = []
        base_resolver = self._resolver_for("93.184.216.34")

        def resolver(host, port, type=0):
            resolver_calls.append((host, port))
            return base_resolver(host, port, type=type)

        class RecordingSocket:
            def __init__(self):
                self.connected_to = None
                self.timeout = None
                self.closed = False

            def settimeout(self, value):
                self.timeout = value

            def connect(self, sockaddr):
                self.connected_to = sockaddr

            def bind(self, address):
                self.bound_to = address

            def close(self):
                self.closed = True

        raw_socket = RecordingSocket()
        with mock.patch("ai_core.web_knowledge.socket.socket", return_value=raw_socket) as socket_factory:
            connection = _PinnedPublicHTTPConnection(
                "example.com", timeout=0.5, resolver=resolver
            )
            connection.connect()

        self.assertEqual(resolver_calls, [("example.com", 80)])
        self.assertEqual(raw_socket.connected_to, ("93.184.216.34", 80))
        self.assertEqual(connection.host, "example.com")
        socket_factory.assert_called_once()

    def test_pinned_http_connection_rejects_mixed_dns_before_socket_creation(self):
        resolver = self._resolver_for("93.184.216.34", "10.0.0.8")
        with mock.patch("ai_core.web_knowledge.socket.socket") as socket_factory:
            connection = _PinnedPublicHTTPConnection(
                "example.com", timeout=0.5, resolver=resolver
            )
            with self.assertRaisesRegex(OSError, "non-public"):
                connection.connect()
        socket_factory.assert_not_called()

    def test_pinned_connection_fails_closed_on_malformed_dns_iterable(self):
        valid_record = self._resolver_for("93.184.216.34")("example.com", 80)[0]

        def malformed_resolver(host, port, type=0):
            def records():
                yield valid_record
                raise TypeError("malformed resolver output")
            return records()

        with mock.patch("ai_core.web_knowledge.socket.socket") as socket_factory:
            connection = _PinnedPublicHTTPConnection(
                "example.com", timeout=0.5, resolver=malformed_resolver
            )
            with self.assertRaisesRegex(OSError, "resolution/validation failed"):
                connection.connect()
        socket_factory.assert_not_called()

    def test_pinned_https_connection_keeps_hostname_for_tls_sni(self):
        resolver_calls = []
        base_resolver = self._resolver_for("93.184.216.34")

        def resolver(host, port, type=0):
            resolver_calls.append((host, port))
            return base_resolver(host, port, type=type)

        class RecordingSocket:
            def __init__(self):
                self.connected_to = None
                self.timeout = None
                self.closed = False

            def settimeout(self, value):
                self.timeout = value

            def connect(self, sockaddr):
                self.connected_to = sockaddr

            def close(self):
                self.closed = True

        raw_socket = RecordingSocket()
        tls_socket = object()
        context = mock.Mock()
        context.check_hostname = True
        context.wrap_socket.return_value = tls_socket

        with mock.patch("ai_core.web_knowledge.socket.socket", return_value=raw_socket):
            connection = _PinnedPublicHTTPSConnection(
                "example.com", timeout=0.5, resolver=resolver, context=context
            )
            connection.connect()

        self.assertEqual(resolver_calls, [("example.com", 443)])
        self.assertEqual(raw_socket.connected_to, ("93.184.216.34", 443))
        context.wrap_socket.assert_called_once_with(
            raw_socket, server_hostname="example.com"
        )
        self.assertIs(connection.sock, tls_socket)
        self.assertEqual(connection.host, "example.com")

    def test_default_web_opener_disables_ambient_proxy_and_uses_pinned_handlers(self):
        client = WebKnowledge()
        opener = client._opener.__self__
        proxy_handlers = [
            handler for handler in opener.handlers
            if isinstance(handler, urllib.request.ProxyHandler)
        ]
        # An empty ProxyHandler disables urllib's default environment-proxy handler;
        # because it has no protocols to handle, OpenerDirector does not retain it.
        self.assertEqual(len(proxy_handlers), 0)
        self.assertTrue(any(
            isinstance(handler, _PinnedPublicHTTPHandler)
            for handler in opener.handlers
        ))
        self.assertTrue(any(
            isinstance(handler, _PinnedPublicHTTPSHandler)
            for handler in opener.handlers
        ))

    def test_redirect_handler_blocks_hostname_resolving_to_private_address(self):
        handler = _PublicOnlyRedirectHandler(
            resolver=self._resolver_for("192.168.1.7")
        )
        request = urllib.request.Request("https://example.com/start")
        with self.assertRaisesRegex(urllib.error.HTTPError, "DNS destination"):
            handler.redirect_request(
                request, None, 302, "Found", None, "https://internal-looking.example/next"
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

    @staticmethod
    def _semantic_relation(left_excerpt, right_excerpt):
        return WebKnowledge._compare_source_evidence([
            {"excerpt": left_excerpt},
            {"excerpt": right_excerpt},
        ])

    def test_non_numeric_open_closed_claims_are_flagged_as_potential_conflict(self):
        relation = self._semantic_relation(
            "The museum is open to visitors every day.",
            "The museum is closed to visitors every day.",
        )
        self.assertEqual(relation, "potential_semantic_conflict")

    def test_negated_shared_predicate_is_flagged_as_potential_conflict(self):
        relation = self._semantic_relation(
            "The museum is open to visitors.",
            "The museum is not open to visitors.",
        )
        self.assertEqual(relation, "potential_semantic_conflict")

    def test_paraphrased_opposing_access_claims_are_flagged_conservatively(self):
        relation = self._semantic_relation(
            "Officials permitted public access to the archive.",
            "Authorities prohibited public access to the archive.",
        )
        self.assertEqual(relation, "potential_semantic_conflict")

    def test_unrelated_sentences_are_not_misclassified_as_semantic_conflict(self):
        relation = self._semantic_relation(
            "The museum is open to visitors during summer.",
            "The garden is closed during winter.",
        )
        self.assertEqual(relation, "divergent_unresolved")

    def test_compatible_different_wording_stays_unresolved_not_conflicting(self):
        relation = self._semantic_relation(
            "The clinic provides emergency care around the clock.",
            "Emergency services at the clinic operate 24 hours every day.",
        )
        self.assertNotEqual(relation, "potential_semantic_conflict")
        self.assertEqual(relation, "divergent_unresolved")

    def test_hindi_open_closed_claims_are_flagged_as_potential_conflict(self):
        relation = self._semantic_relation(
            "संग्रहालय आगंतुकों के लिए खुला है।",
            "संग्रहालय आगंतुकों के लिए बंद है।",
        )
        self.assertEqual(relation, "potential_semantic_conflict")

    def test_semantic_conflict_is_returned_as_unresolved_not_a_chosen_fact(self):
        client = WebKnowledge(total_timeout=2.0)
        results = {
            "hi": self._mock_source(
                "The museum is closed to visitors every day.",
                "https://museum.example.org/visiting", "Visitor information",
            ),
            "en": self._mock_source(
                "The museum is open to visitors every day.",
                "https://archive.example.net/museum-hours", "Hours page",
            ),
        }
        client._query_variants = lambda question: ["variant one", "variant two"]
        client._wikipedia = lambda query, language, output_language="hi": results[language]
        client._duckduckgo = lambda query, preferred_language: None

        result = client.answer("is the museum open?", preferred_language="en")

        self.assertTrue(result["success"])
        self.assertEqual(result["answer_status"], "conflicting_sources")
        self.assertEqual(
            result["evidence"]["cross_source_relation"],
            "potential_semantic_conflict",
        )
        self.assertIn("unresolved", result["answer"])
        self.assertTrue(any("bounded polarity/opposition vocabulary" in item for item in result["limitations"]))

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

    def test_configured_provider_contract_accepts_safe_sourced_result(self):
        calls = []

        def provider(client, query_variants, preferred_language):
            calls.append((tuple(query_variants), preferred_language))
            self.assertTrue(callable(client.fetch_text))
            return self._provider_result()

        client = WebKnowledge(
            opener=lambda _request, timeout=0: FakeResponse("unused"),
            providers=[RetrievalProvider("custom", provider)],
        )
        result = client.answer("a custom fact", preferred_language="en")

        self.assertTrue(result["success"])
        self.assertEqual(result["answer_status"], "sourced_excerpt")
        self.assertEqual(result["source"]["url"], "https://facts.example.org/item")
        self.assertEqual(result["sources"][0]["host"], "facts.example.org")
        self.assertEqual(result["provider"], "custom")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], "en")

    def test_provider_failure_and_unsafe_result_fall_through_in_configured_order(self):
        calls = []

        def failing(_client, _variants, _language):
            calls.append("broken")
            raise OSError("provider unavailable")

        def unsafe(_client, _variants, _language):
            calls.append("unsafe")
            return self._provider_result(url="http://127.0.0.1/private")

        def valid(_client, _variants, _language):
            calls.append("valid")
            return self._provider_result(url="https://valid.example.org/item")

        client = WebKnowledge(
            providers=[
                RetrievalProvider("broken", failing),
                RetrievalProvider("unsafe", unsafe),
                RetrievalProvider("valid", valid),
            ]
        )
        result = client.answer("fallback behavior")

        self.assertTrue(result["success"])
        self.assertEqual(result["source"]["url"], "https://valid.example.org/item")
        self.assertEqual(calls, ["broken", "unsafe", "valid"])

    def test_explicit_empty_provider_list_returns_unknown_without_default_fallback(self):
        client = WebKnowledge(providers=[])
        result = client.answer("no providers configured")
        self.assertFalse(result["success"])
        self.assertEqual(result["answer_status"], "unknown")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["evidence"]["source_count"], 0)

    def test_configured_providers_deduplicate_normalized_hosts(self):
        def first(_client, _variants, _language):
            return self._provider_result(
                url="https://www.duplicate.example.org/first",
                excerpt="One cited excerpt from the first path.",
            )

        def second(_client, _variants, _language):
            return self._provider_result(
                url="https://duplicate.example.org/second",
                excerpt="A different excerpt served from the same normalized host.",
            )

        def third(_client, _variants, _language):
            return self._provider_result(
                url="https://independent.example.net/third",
                excerpt="Another excerpt from a different host.",
            )

        client = WebKnowledge(
            providers=[
                RetrievalProvider("first", first),
                RetrievalProvider("second", second),
                RetrievalProvider("third", third),
            ]
        )
        result = client.answer("duplicate host")

        self.assertEqual(result["evidence"]["source_count"], 2)
        self.assertEqual(
            {source["host"] for source in result["sources"]},
            {"duplicate.example.org", "independent.example.net"},
        )
        self.assertEqual(result["source"]["url"], result["sources"][0]["url"])

    def test_provider_and_result_caps_bound_output_excerpt_and_metadata(self):
        calls = []
        long_excerpt = "word " * 500
        long_title = "Long title " * 40
        long_site = "Long site " * 40

        def provider_factory(provider_index):
            def provider(_client, _variants, _language):
                calls.append(provider_index)
                return [
                    self._provider_result(
                        url=f"https://p{provider_index}-r{result_index}.example.org/item",
                        excerpt=long_excerpt,
                        title=long_title,
                        site=long_site,
                    )
                    for result_index in range(8)
                ]
            return provider

        providers = [
            RetrievalProvider(f"provider-{index}", provider_factory(index), max_results=999)
            for index in range(4)
        ]
        # The fifth provider is outside the configured provider-count bound.
        providers.append(RetrievalProvider(
            "provider-over-limit",
            lambda *_args: (_ for _ in ()).throw(AssertionError("provider cap ignored")),
        ))

        client = WebKnowledge(providers=providers)
        result = client.answer("bounded provider output")

        self.assertTrue(result["success"])
        self.assertEqual(calls, [0, 1])
        self.assertEqual(len(result["sources"]), 6)
        for source in result["sources"]:
            self.assertLessEqual(len(source["excerpt"]), 1200)
            self.assertLessEqual(len(source["title"]), 240)
            self.assertLessEqual(len(source["site"]), 160)

    def test_provider_outbound_fetch_budget_is_bounded(self):
        fetches = []

        def opener(request, timeout=0):
            fetches.append(request.full_url)
            return FakeResponse("a small response")

        def provider(client, _variants, _language):
            for _ in range(20):
                try:
                    client.fetch_text("https://fetch-budget.example.org/item")
                except TimeoutError:
                    break
            return None

        client = WebKnowledge(
            opener=opener,
            providers=[RetrievalProvider("bounded-fetcher", provider)],
        )
        result = client.answer("bounded outbound work")

        self.assertFalse(result["success"])
        self.assertEqual(result["answer_status"], "unknown")
        self.assertEqual(len(fetches), client.MAX_FETCHES_PER_PROVIDER)
        self.assertLessEqual(len(fetches), client.MAX_TOTAL_PROVIDER_FETCHES)

    def test_malformed_provider_output_is_ignored_without_iteration(self):
        calls = []

        def malformed(_client, _variants, _language):
            calls.append("malformed")
            return (item for item in [self._provider_result()])

        def valid(_client, _variants, _language):
            calls.append("valid")
            return self._provider_result(url="https://fallback.example.net/item")

        client = WebKnowledge(
            providers=[
                RetrievalProvider("malformed", malformed),
                RetrievalProvider("valid", valid),
            ]
        )
        result = client.answer("finite output contract")

        self.assertTrue(result["success"])
        self.assertEqual(result["source"]["url"], "https://fallback.example.net/item")
        self.assertEqual(calls, ["malformed", "valid"])

    def test_unsafe_provider_citation_leaves_unknown_not_a_fabricated_answer(self):
        client = WebKnowledge(
            providers=[
                RetrievalProvider(
                    "unsafe-citation",
                    lambda *_args: self._provider_result(
                        url="file:///etc/passwd",
                        excerpt="This content must not be accepted.",
                    ),
                )
            ]
        )
        result = client.answer("unsafe citation")
        self.assertFalse(result["success"])
        self.assertEqual(result["answer_status"], "unknown")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["evidence"]["type"], "none")

    def test_configured_provider_count_is_capped_even_when_early_providers_return_nothing(self):
        calls = []

        def empty_provider(index):
            def provider(_client, _variants, _language):
                calls.append(index)
                return None
            return provider

        providers = [
            RetrievalProvider(f"provider-{index}", empty_provider(index))
            for index in range(4)
        ]
        providers.append(RetrievalProvider(
            "fifth-provider",
            lambda *_args: (_ for _ in ()).throw(AssertionError("provider-count cap ignored")),
        ))
        client = WebKnowledge(providers=providers)

        result = client.answer("provider count bound")

        self.assertFalse(result["success"])
        self.assertEqual(result["answer_status"], "unknown")
        self.assertEqual(calls, [0, 1, 2, 3])

    @staticmethod
    def _quality_source(
        excerpt="A detailed source excerpt describes a concrete result, a named institution, and its published findings.",
        url="https://facts.example.org/item",
        title="Published facts report",
        site="Facts publisher",
        published_date=None,
    ):
        from urllib.parse import urlparse
        source = {
            "title": title,
            "url": url,
            "site": site,
            "host": urlparse(url).hostname,
            "excerpt": excerpt,
        }
        if published_date is not None:
            source["published_date"] = published_date
        return source

    def test_source_quality_scores_freshness_only_when_publication_date_exists(self):
        as_of = datetime(2026, 10, 22, tzinfo=timezone.utc)
        fresh_source = self._quality_source(
            url="https://stats.example.org/current",
            published_date="2026-10-01",
        )
        fresh_source["publisher"] = "Statistics Office"
        stale_source = self._quality_source(
            url="https://stats.example.net/archive",
            published_date="2010-01-01",
        )
        stale_source["publisher"] = "Statistics Office"
        fresh, stale = WebKnowledge._evaluate_source_quality(
            [fresh_source, stale_source], reference_time=as_of
        )
        self.assertEqual(fresh["freshness"]["status"], "fresh")
        self.assertEqual(stale["freshness"]["status"], "very_stale")
        self.assertGreater(fresh["score"], stale["score"])
        self.assertEqual(fresh["score_semantics"], "heuristic metadata quality only; not a probability of truth")

        unknown = WebKnowledge._evaluate_source_quality(
            [self._quality_source()], reference_time=as_of
        )[0]
        self.assertEqual(unknown["freshness"]["status"], "unknown")
        self.assertIsNone(unknown["freshness"]["score_points"])

    def test_source_quality_flags_duplicate_excerpt_as_potential_repost(self):
        excerpt = (
            "The regional report identifies 125 schools across 14 districts and describes "
            "annual enrollment trends, inspection findings, and the published methodology."
        )
        sources = [
            self._quality_source(excerpt, url="https://first.example.org/report"),
            self._quality_source(excerpt, url="https://second.example.net/copy"),
        ]
        first, second = WebKnowledge._evaluate_source_quality(
            sources, reference_time=datetime(2026, 10, 22, tzinfo=timezone.utc)
        )
        self.assertEqual(first["duplicate_repost"]["status"], "not_detected_in_current_results")
        self.assertEqual(second["duplicate_repost"]["status"], "potential_repost")
        self.assertEqual(second["duplicate_repost"]["duplicate_of_source_index"], 1)
        self.assertEqual(second["duplicate_repost"]["score_points"], 0)

    def test_source_quality_score_is_not_increased_by_an_unrelated_extra_source(self):
        source = self._quality_source(published_date="2026-10-01")
        unrelated = self._quality_source(
            excerpt="Separate material describes different ecological observations in another region.",
            url="https://environment.example.net/observations",
            published_date="2026-10-01",
        )
        as_of = datetime(2026, 10, 22, tzinfo=timezone.utc)
        alone = WebKnowledge._evaluate_source_quality([source], reference_time=as_of)[0]
        with_unrelated = WebKnowledge._evaluate_source_quality(
            [source, unrelated], reference_time=as_of
        )[0]
        self.assertEqual(alone["score"], with_unrelated["score"])

    def test_short_or_boilerplate_primary_excerpt_returns_unknown_with_citation(self):
        client = WebKnowledge(
            providers=[
                RetrievalProvider(
                    "short-excerpt",
                    lambda *_args: self._provider_result(
                        excerpt="OK", url="https://brief.example.org/item"
                    ),
                )
            ]
        )
        result = client.answer("what is this?")
        self.assertEqual(result["answer_status"], "unknown")
        self.assertFalse(result["success"])
        self.assertEqual(result["evidence"]["source_quality"]["per_source"][0]["evidence_status"], "low_evidence")
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["source"]["url"], "https://brief.example.org/item")

    def test_provider_publication_date_is_preserved_for_quality_assessment(self):
        candidate = self._provider_result()
        candidate["source"]["published_date"] = "2026-10-01"
        normalized = WebKnowledge._normalize_provider_result(
            candidate, "test-provider", "test query", "en"
        )
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["source"]["published_date"], "2026-10-01")


if __name__ == "__main__":
    unittest.main()
