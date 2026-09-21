"""
Project : Vyom AI
Version : 1.0
Module  : Input Controller

Purpose:
    Generic Windows mouse and keyboard input through the Win32 SendInput API.

The controller knows keyboard protocol values, not application-specific
commands. Targets are supplied at runtime by the validated action schema.
"""

from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes
from typing import Any, Iterable, List


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_int32),
        ("dy", ctypes.c_int32),
        ("mouseData", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_uint16),
        ("wScan", ctypes.c_uint16),
        ("dwFlags", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_uint32),
        ("wParamL", ctypes.c_uint16),
        ("wParamH", ctypes.c_uint16),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", _MOUSEINPUT),
        ("ki", _KEYBDINPUT),
        ("hi", _HARDWAREINPUT),
    ]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("u", _INPUT_UNION),
    ]


class InputController:
    """Generic keyboard and mouse input provider."""

    KEY_NAMES = {
        "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "return": 0x0D,
        "shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12,
        "pause": 0x13, "capslock": 0x14, "esc": 0x1B, "escape": 0x1B,
        "space": 0x20, "pageup": 0x21, "pagedown": 0x22,
        "end": 0x23, "home": 0x24, "left": 0x25, "up": 0x26,
        "right": 0x27, "down": 0x28, "insert": 0x2D, "delete": 0x2E,
        "win": 0x5B, "windows": 0x5B, "lwin": 0x5B, "rwin": 0x5C,
        "numlock": 0x90, "scrolllock": 0x91,
        "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63,
        "numpad4": 0x64, "numpad5": 0x65, "numpad6": 0x66, "numpad7": 0x67,
        "numpad8": 0x68, "numpad9": 0x69,
        "multiply": 0x6A, "add": 0x6B, "subtract": 0x6D, "decimal": 0x6E,
        "divide": 0x6F, "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
        "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
        "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    }

    BUTTONS = {
        "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
        "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
    }

    def __init__(self):
        self.available = os.name == "nt"
        self._user32 = getattr(ctypes, "windll", None).user32 if self.available else None
        if self.available and self._user32 is not None:
            try:
                self._user32.SetCursorPos.argtypes = [wintypes.INT, wintypes.INT]
                self._user32.SetCursorPos.restype = wintypes.BOOL
                self._user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
                self._user32.SendInput.restype = wintypes.UINT
            except Exception:
                pass

    def is_available(self) -> bool:
        return self.available and self._user32 is not None

    def _send_inputs(self, inputs: List[_INPUT]) -> bool:
        if not self.is_available() or not inputs:
            return False
        array_type = _INPUT * len(inputs)
        array = array_type(*inputs)
        sent = self._user32.SendInput(len(inputs), ctypes.byref(array), ctypes.sizeof(_INPUT))
        return int(sent) == len(inputs)

    def move_mouse(self, x: Any, y: Any) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}
        try:
            ix, iy = int(x), int(y)
            success = bool(self._user32.SetCursorPos(ix, iy))
        except Exception as error:
            return {"success": False, "stage": "mouse_move_error", "message": str(error)}
        return {
            "success": success,
            "stage": "mouse_moved" if success else "mouse_move_failed",
            "position": {"x": ix, "y": iy},
            "verification": {"verified": success, "verification_level": "dispatch"},
        }

    def click(self, button: str = "left", x: Any = None, y: Any = None, count: int = 1, interval: float = 0.05) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}

        key = str(button or "left").strip().lower()
        events = self.BUTTONS.get(key)
        if events is None:
            return {"success": False, "stage": "invalid_mouse_button", "message": "Unsupported mouse button."}

        if x is not None or y is not None:
            move = self.move_mouse(x, y)
            if not move.get("success"):
                return move

        try:
            clicks = max(1, int(count))
            inputs: List[_INPUT] = []
            for index in range(clicks):
                down, up = events
                inputs.append(self._mouse_input(down))
                inputs.append(self._mouse_input(up))
                if index + 1 < clicks and interval > 0:
                    # Keep the timing outside SendInput to preserve double-click behavior.
                    if not self._send_inputs(inputs):
                        return {"success": False, "stage": "click_failed", "message": "Windows input dispatch failed."}
                    inputs = []
                    time.sleep(min(float(interval), 1.0))
            success = self._send_inputs(inputs) if inputs else True
        except Exception as error:
            return {"success": False, "stage": "click_error", "message": str(error)}

        return {
            "success": success,
            "stage": "mouse_clicked" if success else "click_failed",
            "button": key,
            "count": max(1, int(count)),
            "verification": {"verified": success, "verification_level": "dispatch"},
        }

    def _mouse_input(self, flags: int, mouse_data: int = 0) -> _INPUT:
        item = _INPUT()
        item.type = INPUT_MOUSE
        item.mi = _MOUSEINPUT(0, 0, int(mouse_data) & 0xFFFFFFFF, flags, 0, None)
        return item

    def _keyboard_input(self, vk: int, scan: int = 0, flags: int = 0) -> _INPUT:
        item = _INPUT()
        item.type = INPUT_KEYBOARD
        item.ki = _KEYBDINPUT(vk, scan, flags, 0, None)
        return item

    def _key_to_vk(self, key: Any) -> int:
        if isinstance(key, bool):
            raise ValueError("Boolean is not a valid key.")
        if isinstance(key, int):
            if 0 <= key <= 255:
                return key
            raise ValueError("Virtual key code must be in the range 0..255.")

        text = str(key or "").strip().lower()
        if not text:
            raise ValueError("Key is empty.")
        if text in self.KEY_NAMES:
            return self.KEY_NAMES[text]
        if len(text) == 1 and text.isalpha():
            return ord(text.upper())
        if len(text) == 1 and text.isdigit():
            return ord(text)
        if text.startswith("0x"):
            return int(text, 16)
        raise ValueError(f"Unsupported key: {key}")

    def keypress(self, key: Any) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}
        try:
            vk = self._key_to_vk(key)
            success = self._send_inputs([
                self._keyboard_input(vk),
                self._keyboard_input(vk, flags=KEYEVENTF_KEYUP),
            ])
        except Exception as error:
            return {"success": False, "stage": "keypress_error", "message": str(error)}
        return {
            "success": success,
            "stage": "key_pressed" if success else "keypress_failed",
            "key": str(key),
            "verification": {"verified": success, "verification_level": "dispatch"},
        }

    def hotkey(self, keys: Iterable[Any]) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}

        if isinstance(keys, str):
            values = [part.strip() for part in keys.replace("+", " ").split() if part.strip()]
        else:
            values = list(keys or [])
        if not values:
            return {"success": False, "stage": "invalid_hotkey", "message": "No keys were supplied."}

        try:
            vks = [self._key_to_vk(value) for value in values]
            down = [self._keyboard_input(vk) for vk in vks]
            up = [self._keyboard_input(vk, flags=KEYEVENTF_KEYUP) for vk in reversed(vks)]
            success = self._send_inputs(down + up)
        except Exception as error:
            return {"success": False, "stage": "hotkey_error", "message": str(error)}

        return {
            "success": success,
            "stage": "hotkey_sent" if success else "hotkey_failed",
            "keys": [str(value) for value in values],
            "verification": {"verified": success, "verification_level": "dispatch"},
        }

    def type_text(self, text: Any) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}

        value = str(text if text is not None else "")
        if not value:
            return {"success": True, "stage": "empty_text", "verification": {"verified": True, "verification_level": "dispatch"}}

        inputs: List[_INPUT] = []
        for char in value:
            codepoint = ord(char)
            if codepoint > 0xFFFF:
                # Windows Unicode SendInput uses UTF-16 code units.
                encoded = char.encode("utf-16-le")
                code_units = [int.from_bytes(encoded[i:i + 2], "little") for i in range(0, len(encoded), 2)]
            else:
                code_units = [codepoint]
            for unit in code_units:
                inputs.append(self._keyboard_input(0, scan=unit, flags=KEYEVENTF_UNICODE))
                inputs.append(self._keyboard_input(0, scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))

            # Avoid unbounded single API batches for long text.
            if len(inputs) >= 200:
                if not self._send_inputs(inputs):
                    return {"success": False, "stage": "type_text_failed", "message": "Unicode input dispatch failed."}
                inputs = []

        try:
            success = self._send_inputs(inputs) if inputs else True
        except Exception as error:
            return {"success": False, "stage": "type_text_error", "message": str(error)}

        return {
            "success": success,
            "stage": "text_typed" if success else "type_text_failed",
            "text_length": len(value),
            "verification": {"verified": success, "verification_level": "dispatch"},
        }

    def scroll(self, amount: Any) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}
        try:
            value = int(amount)
            data = value * 120
            success = self._send_inputs([self._mouse_input(MOUSEEVENTF_WHEEL, data)])
        except Exception as error:
            return {"success": False, "stage": "scroll_error", "message": str(error)}
        return {
            "success": success,
            "stage": "scrolled" if success else "scroll_failed",
            "amount": value,
            "verification": {"verified": success, "verification_level": "dispatch"},
        }
