"""Generic helpers for Windows UI Automation control operations.

The module contains no application-specific names. It works with any UIA
wrapper that exposes the corresponding control-pattern operation.
"""

from typing import Any, Dict, Optional


ACTION_METHODS = {
    "invoke": ("invoke", "click"),
    "click": ("click", "invoke", "click_input"),
    "focus": ("set_focus",),
    "set_value": ("set_value",),
    "get_value": ("get_value",),
    "select": ("select",),
    "toggle": ("toggle",),
    "expand": ("expand",),
    "collapse": ("collapse",),
}


def supported_operations(element: Any) -> Dict[str, bool]:
    """Report generic operations available on a UIA wrapper."""
    return {
        operation: any(callable(getattr(element, method, None))
                       for method in methods)
        for operation, methods in ACTION_METHODS.items()
    }


def _call_first(element: Any, methods, *args, **kwargs):
    for method in methods:
        callback = getattr(element, method, None)
        if callable(callback):
            return callback(*args, **kwargs)
    raise AttributeError("The UI element does not expose the requested operation.")


def invoke(element: Any):
    return _call_first(element, ACTION_METHODS["invoke"])


def click(element: Any):
    return _call_first(element, ACTION_METHODS["click"])


def focus(element: Any):
    return _call_first(element, ACTION_METHODS["focus"])


def set_value(element: Any, value: Any):
    return _call_first(element, ACTION_METHODS["set_value"], value)


def get_value(element: Any):
    return _call_first(element, ACTION_METHODS["get_value"])


def select(element: Any):
    return _call_first(element, ACTION_METHODS["select"])


def toggle(element: Any):
    return _call_first(element, ACTION_METHODS["toggle"])


def expand(element: Any):
    return _call_first(element, ACTION_METHODS["expand"])


def collapse(element: Any):
    return _call_first(element, ACTION_METHODS["collapse"])


def operation_result(
    *,
    success: bool,
    operation: str,
    element_info: Optional[Dict[str, Any]] = None,
    result: Any = None,
    error: Optional[str] = None,
    verification_level: str = "semantic_dispatch",
) -> Dict[str, Any]:
    """Build a serializable semantic UI operation result."""
    payload = {
        "success": bool(success),
        "stage": f"{operation}_{'completed' if success else 'failed'}",
        "operation": operation,
        "verification": {
            "verified": bool(success),
            "verification_level": verification_level,
            "method": "windows_ui_automation",
        },
    }
    if element_info:
        payload["element"] = dict(element_info)
    if result is not None:
        payload["result"] = result
    if error:
        payload["error"] = str(error)
        payload["message"] = str(error)
    return payload


__all__ = [
    "supported_operations",
    "invoke",
    "click",
    "focus",
    "set_value",
    "get_value",
    "select",
    "toggle",
    "expand",
    "collapse",
    "operation_result",
]
