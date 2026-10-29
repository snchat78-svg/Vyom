"""Regression tests for domain-safe app-launch fallback."""
from tools.tool_manager import ToolManager


def test_app_suggestions_do_not_trigger_global_fuzzy_file_search():
    class FakeResolver:
        def __init__(self):
            self.file_only_calls = []
            self.find_calls = 0

        def find_file_or_folder(self, target):
            self.file_only_calls.append(target)
            return []

        def find(self, target):
            self.find_calls += 1
            raise AssertionError("No app suggestion should trigger global fuzzy file search")

    class FakeSelection:
        def __init__(self):
            self.results = []

        def save(self, values):
            self.results = list(values)

        def clear(self):
            self.results = []

        def has_results(self):
            return bool(self.results)

    manager = ToolManager.__new__(ToolManager)
    manager.resolver = FakeResolver()
    manager.selection_manager = FakeSelection()
    manager.selection_source = None
    manager.max_results = 10

    response = manager._handle_launcher_response(
        "amejon",
        {
            "success": False,
            "results": [],
            "suggestions": ["Amazon", "Amazon Music"],
        },
    )

    assert "Amazon" in response
    assert manager.resolver.file_only_calls == ["amejon"]
    assert manager.resolver.find_calls == 0
    assert manager.selection_source == "app"
    assert all(item.get("type") == "suggestion" for item in manager.selection_manager.results)


def test_explicit_photos_query_can_use_fuzzy_file_resolver_after_app_miss():
    class FakeResolver:
        def __init__(self):
            self.file_only_calls = []
            self.find_calls = 0

        def find_file_or_folder(self, target):
            self.file_only_calls.append(target)
            return []

        def find(self, target):
            self.find_calls += 1
            return [
                {"name": "Photos A To Z.jpg", "path": "C:/Pictures/Photos A To Z.jpg", "type": "file"},
                {"name": "Photos Archive.jpg", "path": "C:/Pictures/Photos Archive.jpg", "type": "file"},
            ]

    class FakeSelection:
        def __init__(self):
            self.results = []

        def save(self, values):
            self.results = list(values)

        def clear(self):
            self.results = []

        def has_results(self):
            return bool(self.results)

    manager = ToolManager.__new__(ToolManager)
    manager.resolver = FakeResolver()
    manager.selection_manager = FakeSelection()
    manager.selection_source = None
    manager.max_results = 10

    response = manager._handle_launcher_response(
        "photos e tu j",
        {"success": False, "results": [], "suggestions": ["Photos"]},
    )

    assert "Photos A To Z.jpg" in response
    assert manager.resolver.file_only_calls == []
    assert manager.resolver.find_calls == 1
    assert manager.selection_source == "resolver"
