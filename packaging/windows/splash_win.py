"""A small "Free My ID is starting" window shown while the app loads (Windows only).

The first start can take a minute or more (virus scan of the new files, first imports, the
WebView2 engine starting). Without this the person sees nothing and clicks again. The splash
stays up until the app window has actually loaded its page (`close()` is called from the
webview's "loaded" event, see freemyid.wizard.desktop). If that takes longer than
TIMEOUT_S, the text changes to a plain "still starting" message and the splash stops being
always-on-top, so it can never hide the app; it never just vanishes.

Pure ctypes, no extra packages. Every failure is swallowed: a missing splash must never stop
the app from starting.
"""
from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable

TEXT = ("Free My ID is starting.\r\n\r\nThe first time can take up to a minute.\r\n"
        "Please wait.")
SLOW_TEXT = ("Free My ID is still starting.\r\n\r\nThis is taking longer than usual.\r\n"
             "Please wait; there is no need to click it again.")
TIMEOUT_S = 120.0
_hwnd: list[int] = []
_done = threading.Event()


def pump(done: threading.Event, on_slow: Callable[[], None], tick: Callable[[], None],
         clock: Callable[[], float] = time.monotonic, timeout: float = TIMEOUT_S,
         step: float = 0.05) -> bool:
    """Keep the splash alive until `done` is set. Returns True if the slow state was shown.

    `on_slow` runs once, after `timeout` seconds without `done`; the loop then keeps going.
    `tick` pumps window messages. Separate from the Win32 code so it can be tested anywhere.
    """
    start = clock()
    slow = False
    while not done.is_set():
        tick()
        if not slow and clock() - start >= timeout:
            slow = True
            on_slow()
        done.wait(step)
    return slow


def _run() -> None:
    try:
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32  # type: ignore[attr-defined]
        u.CreateWindowExW.restype = wintypes.HWND
        u.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        u.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, wintypes.UINT]
        w, h = 440, 160
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

        def tick() -> None:
            while u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                u.TranslateMessage(ctypes.byref(msg))
                u.DispatchMessageW(ctypes.byref(msg))

        def on_slow() -> None:
            u.SetWindowTextW(hwnd, SLOW_TEXT)
            HWND_NOTOPMOST, SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = -2, 0x1, 0x2, 0x10
            u.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                           SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)

        pump(_done, on_slow, tick)
        u.DestroyWindow(hwnd)
    except Exception:  # noqa: BLE001
        pass


def show() -> None:
    if sys.platform == "win32":
        threading.Thread(target=_run, daemon=True).start()


def close() -> None:
    _done.set()
