"""A small "Free My ID is starting" window shown while the app loads (Windows only).

The first start can take up to 15 seconds (virus scan of the new files, first imports). Without
this the person sees nothing and clicks again. Pure ctypes, no extra packages. Every failure is
swallowed: a missing splash must never stop the app from starting.
"""
from __future__ import annotations

import sys
import threading

TEXT = "Free My ID is starting.\r\n\r\nThis can take up to 15 seconds the first time.\r\nPlease wait."
_hwnd: list[int] = []
_done = threading.Event()


def _run() -> None:
    try:
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        u.CreateWindowExW.restype = wintypes.HWND
        u.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        w, h = 420, 150
        x = (u.GetSystemMetrics(0) - w) // 2
        y = (u.GetSystemMetrics(1) - h) // 2
        WS_POPUP, WS_VISIBLE, WS_BORDER, SS_CENTER = 0x80000000, 0x10000000, 0x800000, 1
        TOPMOST, TOOLWINDOW = 0x8, 0x80
        hwnd = u.CreateWindowExW(TOPMOST | TOOLWINDOW, "STATIC", TEXT,
                                 WS_POPUP | WS_VISIBLE | WS_BORDER | SS_CENTER,
                                 x, y, w, h, None, None, None, None)
        if not hwnd:
            return
        _hwnd.append(hwnd)
        msg = wintypes.MSG()
        while not _done.is_set():
            while u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                u.TranslateMessage(ctypes.byref(msg))
                u.DispatchMessageW(ctypes.byref(msg))
            _done.wait(0.05)
        u.DestroyWindow(hwnd)
    except Exception:  # noqa: BLE001
        pass


def show() -> None:
    if sys.platform == "win32":
        threading.Thread(target=_run, daemon=True).start()


def close() -> None:
    _done.set()
