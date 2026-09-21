"""
Project : Vyom AI
Version : 1.0
Module  : Clipboard Manager

Purpose:
    Generic Unicode Windows clipboard access using Win32 APIs.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Any, Dict, Optional

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040


class ClipboardManager:
    """Minimal Unicode clipboard provider without third-party dependencies."""

    def __init__(self, retries: int = 5, retry_delay: float = 0.05):
        self.available = os.name == "nt"
        self._user32 = getattr(ctypes, "windll", None).user32 if self.available else None
        self._kernel32 = getattr(ctypes, "windll", None).kernel32 if self.available else None
        if self.available and self._user32 is not None and self._kernel32 is not None:
            try:
                self._user32.OpenClipboard.argtypes = [wintypes.HWND]
                self._user32.OpenClipboard.restype = wintypes.BOOL
                self._user32.CloseClipboard.restype = wintypes.BOOL
                self._user32.EmptyClipboard.restype = wintypes.BOOL
                self._user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
                self._user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
                self._user32.GetClipboardData.argtypes = [wintypes.UINT]
                self._user32.GetClipboardData.restype = wintypes.HANDLE
                self._user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
                self._user32.SetClipboardData.restype = wintypes.HANDLE
                self._kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
                self._kernel32.GlobalAlloc.restype = wintypes.HANDLE
                self._kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
                self._kernel32.GlobalFree.restype = wintypes.HANDLE
                self._kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
                self._kernel32.GlobalLock.restype = ctypes.c_void_p
                self._kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
                self._kernel32.GlobalUnlock.restype = wintypes.BOOL
            except Exception:
                pass
        self.retries = max(1, int(retries))
        self.retry_delay = max(0.0, float(retry_delay))

    def is_available(self) -> bool:
        return bool(self.available and self._user32 and self._kernel32)

    def _open(self) -> bool:
        if not self.is_available():
            return False
        for _ in range(self.retries):
            if self._user32.OpenClipboard(None):
                return True
            if self.retry_delay:
                import time
                time.sleep(self.retry_delay)
        return False

    def set_text(self, text: Any) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}

        value = str(text if text is not None else "")
        if not self._open():
            return {"success": False, "stage": "clipboard_busy", "message": "Clipboard is busy or unavailable."}

        handle = None
        try:
            if not self._user32.EmptyClipboard():
                return {"success": False, "stage": "clipboard_clear_failed", "message": "Could not clear the clipboard."}

            encoded = (value + "\x00").encode("utf-16-le")
            handle = self._kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(encoded))
            if not handle:
                return {"success": False, "stage": "clipboard_alloc_failed", "message": "Could not allocate clipboard memory."}

            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                self._kernel32.GlobalFree(handle)
                handle = None
                return {"success": False, "stage": "clipboard_lock_failed", "message": "Could not lock clipboard memory."}

            ctypes.memmove(pointer, encoded, len(encoded))
            self._kernel32.GlobalUnlock(handle)

            if not self._user32.SetClipboardData(CF_UNICODETEXT, handle):
                self._kernel32.GlobalFree(handle)
                handle = None
                return {"success": False, "stage": "clipboard_set_failed", "message": "Could not set clipboard data."}

            # Ownership transfers to the clipboard after SetClipboardData.
            handle = None
            return {
                "success": True,
                "stage": "clipboard_set",
                "text_length": len(value),
                "verification": {"verified": True, "verification_level": "dispatch"},
            }
        except Exception as error:
            if handle:
                try:
                    self._kernel32.GlobalFree(handle)
                except Exception:
                    pass
            return {"success": False, "stage": "clipboard_set_error", "message": str(error)}
        finally:
            try:
                self._user32.CloseClipboard()
            except Exception:
                pass

    def get_text(self) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}
        if not self._open():
            return {"success": False, "stage": "clipboard_busy", "message": "Clipboard is busy or unavailable."}

        handle = None
        pointer = None
        try:
            if not self._user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return {"success": False, "stage": "clipboard_format_missing", "message": "No Unicode text is available on the clipboard."}

            handle = self._user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return {"success": False, "stage": "clipboard_data_missing", "message": "Clipboard text could not be read."}

            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                return {"success": False, "stage": "clipboard_lock_failed", "message": "Clipboard text could not be locked."}

            value = ctypes.wstring_at(pointer)
            return {
                "success": True,
                "stage": "clipboard_read",
                "text": value,
                "verification": {"verified": True, "verification_level": "state"},
            }
        except Exception as error:
            return {"success": False, "stage": "clipboard_get_error", "message": str(error)}
        finally:
            if pointer:
                try:
                    self._kernel32.GlobalUnlock(handle)
                except Exception:
                    pass
            try:
                self._user32.CloseClipboard()
            except Exception:
                pass

    def clear(self) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}
        if not self._open():
            return {"success": False, "stage": "clipboard_busy", "message": "Clipboard is busy or unavailable."}
        try:
            success = bool(self._user32.EmptyClipboard())
            return {
                "success": success,
                "stage": "clipboard_cleared" if success else "clipboard_clear_failed",
                "verification": {"verified": success, "verification_level": "dispatch"},
            }
        except Exception as error:
            return {"success": False, "stage": "clipboard_clear_error", "message": str(error)}
        finally:
            try:
                self._user32.CloseClipboard()
            except Exception:
                pass
