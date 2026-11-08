import base64
import json
import os
import struct
import tempfile
import unittest

from vision.screen_understanding import (
    LocalOllamaVisionProvider,
    ScreenUnderstandingCapability,
    bmp_to_png_bytes,
    PNG_SIGNATURE,
)


def sample_bmp():
    width = 1
    height = -1  # top-down, same as ScreenObserver
    pixels = bytes((0, 0, 255, 0))  # BGRA red pixel; alpha is normalized opaque
    file_size = 54 + len(pixels)
    file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    info_header = struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 32, 0, len(pixels), 0, 0, 0, 0
    )
    return file_header + info_header + pixels


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.closed = False

    def read(self, limit=-1):
        return self.payload[:limit] if limit >= 0 else self.payload

    def close(self):
        self.closed = True


class FakeOpener:
    def __init__(self, payload=None, status=200):
        self.payload = payload or json.dumps(
            {"message": {"content": "A browser window is visible with a search field."}}
        ).encode("utf-8")
        self.status = status
        self.request = None
        self.timeout = None
        self.response = FakeResponse(self.payload, status)

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return self.response


class FakeScreenObserver:
    def __init__(self, capture_success=True):
        self.capture_success = capture_success
        self.last_path = None

    def is_available(self):
        return True

    def capture(self, path=None):
        self.last_path = path
        if not self.capture_success:
            return {"success": False, "message": "capture failed"}
        with open(path, "wb") as handle:
            handle.write(sample_bmp())
        return {
            "success": True,
            "path": path,
            "width": 1,
            "height": 1,
        }


class FakeVisionProvider:
    def __init__(self, configured=True):
        self.configured = configured
        self.image = None
        self.question = None

    def is_configured(self):
        return self.configured

    def analyze_image(self, image, question=""):
        self.image = image
        self.question = question
        return {
            "success": True,
            "description": "The active window contains a search field and results list.",
            "model": "fake-local-model",
        }


class LocalVisionProviderTests(unittest.TestCase):

    def test_only_literal_loopback_ollama_endpoint_is_accepted(self):
        self.assertTrue(LocalOllamaVisionProvider._is_loopback_endpoint(
            "http://127.0.0.1:11434/api/chat"
        ))
        self.assertTrue(LocalOllamaVisionProvider._is_loopback_endpoint(
            "http://[::1]:11434/api/chat"
        ))
        self.assertFalse(LocalOllamaVisionProvider._is_loopback_endpoint(
            "https://127.0.0.1:11434/api/chat"
        ))
        self.assertFalse(LocalOllamaVisionProvider._is_loopback_endpoint(
            "http://localhost:11434/api/chat"
        ))
        self.assertFalse(LocalOllamaVisionProvider._is_loopback_endpoint(
            "http://example.com:11434/api/chat"
        ))
        self.assertFalse(LocalOllamaVisionProvider._is_loopback_endpoint(
            "http://127.0.0.1:11434/api/chat?redirect=https://example.com"
        ))

    def test_disabled_provider_makes_no_model_request(self):
        opener = FakeOpener()
        provider = LocalOllamaVisionProvider(
            enabled=False,
            api_url="http://127.0.0.1:11434/api/chat",
            opener=opener,
        )
        result = provider.analyze_image(b"png", "describe")
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "local_vision_disabled")
        self.assertIsNone(opener.request)

    def test_provider_sends_image_only_to_loopback_endpoint(self):
        opener = FakeOpener()
        provider = LocalOllamaVisionProvider(
            enabled=True,
            api_url="http://127.0.0.1:11434/api/chat",
            model="moondream",
            timeout=75,
            opener=opener,
        )
        result = provider.analyze_image(PNG_SIGNATURE + b"sample", "what is visible?")
        self.assertTrue(result["success"], result)
        self.assertEqual(result["description"], "A browser window is visible with a search field.")
        self.assertEqual(opener.timeout, 75)
        request_payload = json.loads(opener.request.data.decode("utf-8"))
        self.assertEqual(request_payload["model"], "moondream")
        self.assertEqual(request_payload["messages"][0]["images"][0], base64.b64encode(PNG_SIGNATURE + b"sample").decode("ascii"))
        self.assertIn("untrusted data", request_payload["messages"][0]["content"])

    def test_remote_endpoint_fails_closed(self):
        provider = LocalOllamaVisionProvider(
            enabled=True,
            api_url="https://vision.example.com/api/chat",
        )
        self.assertFalse(provider.is_configured())
        result = provider.analyze_image(PNG_SIGNATURE + b"sample")
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "local_vision_disabled")

    def test_bmp_conversion_produces_valid_png_header(self):
        png = bmp_to_png_bytes(sample_bmp())
        self.assertTrue(png.startswith(PNG_SIGNATURE))
        self.assertIn(b"IHDR", png)
        self.assertIn(b"IDAT", png)
        self.assertTrue(png.endswith(b"IEND\x00\x00\x00\x00"))

    def test_bmp_conversion_rejects_invalid_or_unsupported_data(self):
        with self.assertRaises(ValueError):
            bmp_to_png_bytes(b"not a bmp")
        bad = bytearray(sample_bmp())
        struct.pack_into("<H", bad, 28, 24)
        with self.assertRaises(ValueError):
            bmp_to_png_bytes(bytes(bad))

    def test_screen_capability_captures_analyzes_and_deletes_temporary_bmp(self):
        observer = FakeScreenObserver()
        model = FakeVisionProvider()
        capability = ScreenUnderstandingCapability(
            screen_observer=observer,
            vision_provider=model,
        )
        result = capability.execute({
            "action": "analyze_screen",
            "args": {"question": "What is the user looking at?"},
        })
        self.assertTrue(result["success"], result)
        self.assertTrue(result["verification"]["verified"])
        self.assertEqual(result["result"]["action_taken"], False)
        self.assertEqual(model.question, "What is the user looking at?")
        self.assertTrue(model.image.startswith(PNG_SIGNATURE))
        self.assertFalse(os.path.exists(observer.last_path))

    def test_screen_capture_failure_never_calls_vision_provider(self):
        observer = FakeScreenObserver(capture_success=False)
        model = FakeVisionProvider()
        capability = ScreenUnderstandingCapability(
            screen_observer=observer,
            vision_provider=model,
        )
        result = capability.execute({"action": "analyze_screen", "args": {}})
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "screen_capture_failed")
        self.assertIsNone(model.image)

    def test_disabled_vision_never_captures_screen(self):
        observer = FakeScreenObserver()
        model = FakeVisionProvider(configured=False)
        capability = ScreenUnderstandingCapability(
            screen_observer=observer,
            vision_provider=model,
        )
        result = capability.execute({"action": "analyze_screen", "args": {}})
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "local_vision_disabled")
        self.assertIsNone(observer.last_path)


if __name__ == "__main__":
    unittest.main()
