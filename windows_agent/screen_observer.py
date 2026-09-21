"""
Project : Vyom AI
Version : 1.0
Module  : Screen Observer

Purpose:
    Capture the Windows desktop using native GDI APIs without requiring a
    third-party screenshot package.

The observer provides pixels as a BMP file only; OCR/visual reasoning are
separate future capabilities.
"""

from __future__ import annotations

import ctypes
import os
import struct
import tempfile
from ctypes import wintypes
from typing import Any, Dict, Optional

SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
BI_RGB = 0


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]


class ScreenObserver:
    """Native Windows screenshot provider."""

    def __init__(self):
        self.available = os.name == "nt"
        self._user32 = getattr(ctypes, "windll", None).user32 if self.available else None
        self._gdi32 = getattr(ctypes, "windll", None).gdi32 if self.available else None
        if self.available and self._user32 is not None and self._gdi32 is not None:
            try:
                self._user32.GetDC.argtypes = [wintypes.HWND]
                self._user32.GetDC.restype = wintypes.HDC
                self._user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
                self._user32.ReleaseDC.restype = ctypes.c_int
                self._gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
                self._gdi32.CreateCompatibleDC.restype = wintypes.HDC
                self._gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
                self._gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
                self._gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
                self._gdi32.SelectObject.restype = wintypes.HGDIOBJ
                self._gdi32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
                self._gdi32.BitBlt.restype = wintypes.BOOL
                self._gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(_BITMAPINFO), wintypes.UINT]
                self._gdi32.GetDIBits.restype = ctypes.c_int
                self._gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
                self._gdi32.DeleteObject.restype = wintypes.BOOL
                self._gdi32.DeleteDC.argtypes = [wintypes.HDC]
                self._gdi32.DeleteDC.restype = wintypes.BOOL
            except Exception:
                pass

    def is_available(self) -> bool:
        return bool(self.available and self._user32 and self._gdi32)

    def get_size(self) -> Dict[str, int]:
        if not self.is_available():
            return {"width": 0, "height": 0}
        return {
            "width": int(self._user32.GetSystemMetrics(0)),
            "height": int(self._user32.GetSystemMetrics(1)),
        }

    def capture(
        self,
        path: Optional[str] = None,
        x: int = 0,
        y: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "stage": "windows_unavailable", "message": "Windows APIs are unavailable."}

        screen = self.get_size()
        try:
            x = int(x)
            y = int(y)
            width = int(width if width is not None else screen["width"] - x)
            height = int(height if height is not None else screen["height"] - y)
        except (TypeError, ValueError):
            return {"success": False, "stage": "invalid_capture_region", "message": "Capture region is invalid."}

        if width <= 0 or height <= 0:
            return {"success": False, "stage": "invalid_capture_region", "message": "Capture region must be positive."}

        destination = str(path or "").strip()
        if not destination:
            fd, destination = tempfile.mkstemp(prefix="vyom_screen_", suffix=".bmp")
            os.close(fd)
        else:
            destination = os.path.abspath(os.path.expandvars(os.path.expanduser(destination)))
            parent = os.path.dirname(destination)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

        screen_dc = None
        memory_dc = None
        bitmap = None
        previous = None
        try:
            screen_dc = self._user32.GetDC(None)
            if not screen_dc:
                return {"success": False, "stage": "screen_dc_failed", "message": "Could not acquire the desktop device context."}

            memory_dc = self._gdi32.CreateCompatibleDC(screen_dc)
            bitmap = self._gdi32.CreateCompatibleBitmap(screen_dc, width, height)
            if not memory_dc or not bitmap:
                return {"success": False, "stage": "bitmap_create_failed", "message": "Could not create a screen bitmap."}

            previous = self._gdi32.SelectObject(memory_dc, bitmap)
            if not self._gdi32.BitBlt(memory_dc, 0, 0, width, height, screen_dc, x, y, SRCCOPY | CAPTUREBLT):
                return {"success": False, "stage": "screen_capture_failed", "message": "Windows could not copy the screen."}

            info = _BITMAPINFO()
            info.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
            info.bmiHeader.biWidth = width
            info.bmiHeader.biHeight = -height  # top-down
            info.bmiHeader.biPlanes = 1
            info.bmiHeader.biBitCount = 32
            info.bmiHeader.biCompression = BI_RGB
            info.bmiHeader.biSizeImage = width * height * 4

            buffer = (ctypes.c_ubyte * info.bmiHeader.biSizeImage)()
            scan_lines = self._gdi32.GetDIBits(
                memory_dc,
                bitmap,
                0,
                height,
                ctypes.byref(buffer),
                ctypes.byref(info),
                DIB_RGB_COLORS,
            )
            if int(scan_lines) != height:
                return {"success": False, "stage": "dib_read_failed", "message": "Could not read the captured pixels."}

            pixels = bytes(buffer)
            file_header = struct.pack(
                "<2sIHHI",
                b"BM",
                14 + ctypes.sizeof(_BITMAPINFOHEADER) + len(pixels),
                0,
                0,
                14 + ctypes.sizeof(_BITMAPINFOHEADER),
            )
            info_header = struct.pack(
                "<IiiHHIIiiII",
                40, width, -height, 1, 32, BI_RGB, len(pixels), 0, 0, 0, 0
            )

            with open(destination, "wb") as handle:
                handle.write(file_header)
                handle.write(info_header)
                handle.write(pixels)

            return {
                "success": True,
                "stage": "screen_captured",
                "path": destination,
                "width": width,
                "height": height,
                "verification": {
                    "verified": os.path.isfile(destination) and os.path.getsize(destination) > 54,
                    "verification_level": "state",
                },
            }
        except Exception as error:
            return {"success": False, "stage": "screen_capture_error", "message": str(error)}
        finally:
            if previous and memory_dc:
                try:
                    self._gdi32.SelectObject(memory_dc, previous)
                except Exception:
                    pass
            if bitmap:
                try:
                    self._gdi32.DeleteObject(bitmap)
                except Exception:
                    pass
            if memory_dc:
                try:
                    self._gdi32.DeleteDC(memory_dc)
                except Exception:
                    pass
            if screen_dc:
                try:
                    self._user32.ReleaseDC(None, screen_dc)
                except Exception:
                    pass
