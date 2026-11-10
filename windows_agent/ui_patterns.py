"""Generic helpers for Windows UI Automation control operations.

The module contains no application-specific names. It works with any UIA
wrapper that exposes the corresponding control-pattern operation.
"""

from typing import Any, Dict, Optional


ACTION_METHODS = {
    # Invoke is strict: a generic click method does not prove InvokePattern.
    "invoke": ("invoke",),
    # Prefer semantic activation methods before lower-level mouse input.
    "click": ("click", "invoke", "click_input"),
    "focus": ("set_focus",),
    "set_value": ("set_value",),
    "get_value": ("get_value",),
    "select": ("select",),
    "toggle": ("toggle",),
    "expand": ("expand",),
    "collapse": ("collapse",),
}


def select_operation(element: Any, operation: str) -> Optional[str]:
    """Choose the preferred callable method for one explicit operation."""
    methods = ACTION_METHODS.get(str(operation or "").strip().lower())
    if not methods or element is None:
        return None
    for method in methods:
        try:
            callback = getattr(element, method, None)
        except Exception:
            continue
        if callable(callback):
            return method
    return None


def supported_operations(element: Any) -> Dict[str, bool]:
    """Report generic operations available on a UIA wrapper."""
    return {
        operation: select_operation(element, operation) is not None
        for operation in ACTION_METHODS
    }


def _call_first(element: Any, operation: str, *args, **kwargs):
    method = select_operation(element, operation)
    if method is None:
        raise AttributeError(
            f"The UI element does not support the '{operation}' operation."
        )
    callback = getattr(element, method)
    return callback(*args, **kwargs)


def invoke(element: Any):
    return _call_first(element, "invoke")


def click(element: Any):
    return _call_first(element, "click")


def focus(element: Any):
    return _call_first(element, "focus")


def set_value(element: Any, value: Any):
    return _call_first(element, "set_value", value)


def get_value(element: Any):
    return _call_first(element, "get_value")


def select(element: Any):
    return _call_first(element, "select")


def toggle(element: Any):
    return _call_first(element, "toggle")


def expand(element: Any):
    return _call_first(element, "expand")


def collapse(element: Any):
    return _call_first(element, "collapse")


def operation_result(
    *,
    success: bool,
    operation: str,
    element_info: Optional[Dict[str, Any]] = None,
    result: Any = None,
    error: Optional[str] = None,
    method: Optional[str] = None,
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
    if method:
        payload["dispatch_method"] = str(method)
    if result is not None:
        payload["result"] = result
    if error:
        payload["error"] = str(error)
        payload["message"] = str(error)
    return payload


__all__ = [
    "supported_operations",
    "select_operation",
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
