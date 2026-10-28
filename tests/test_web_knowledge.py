undefined

    def test_provider_transport_failures_are_logged_and_reported_without_raw_error_data(self):
        def fail_fetch(_client, _variants, _language):
            raise OSError("private query text and credentials must not leak")

        client = WebKnowledge(
            providers=[RetrievalProvider("failing-provider", fail_fetch, max_results=1)],
            total_timeout=2.0,
        )
        result = client.answer("capital of India", preferred_language="en")

        self.assertFalse(result["success"])
        self.assertEqual(result["answer_status"], "unknown")
        diagnostics = result["evidence"].get("provider_diagnostics", [])
        self.assertEqual(diagnostics[0]["provider"], "failing-provider")
        self.assertEqual(diagnostics[0]["stage"], "provider_call")
        self.assertEqual(diagnostics[0]["error_type"], "OSError")
        self.assertNotIn("private query text", json.dumps(diagnostics))
