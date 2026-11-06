"""Entry point of the console freemyid-cli.exe (used by the uninstaller and for support)."""
import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()
    from freemyid.cli import app
    app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
