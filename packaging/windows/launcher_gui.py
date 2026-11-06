"""Entry point of the windowed Vanish.exe (no console window).

No arguments: open the app window (wizard on first launch, dashboard afterwards).
With arguments (e.g. `run --scheduled`, used by the scheduled task): behave like the CLI, but
without ever showing a console window.
"""
import multiprocessing
import os
import sys


def _quiet_streams() -> None:
    # A windowed exe has no stdout/stderr; printing would crash without this.
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))  # noqa: SIM115


def main() -> int:
    multiprocessing.freeze_support()
    _quiet_streams()
    if len(sys.argv) > 1:
        from vanish.cli import app
        app()
        return 0
    from vanish.wizard.desktop import main as desktop_main
    return desktop_main()


if __name__ == "__main__":
    sys.exit(main())
