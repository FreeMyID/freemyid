"""Entry point of the console vanish-cli.exe (used by the uninstaller and for support)."""
import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()
    from vanish.cli import app
    app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
