from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _show_startup_error(message: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "SDXL Easy Trainer - Startup Error", 0x10)
    except Exception:
        print(message, file=sys.stderr)


def main() -> int:
    project_root = Path(__file__).resolve().parent
    log_path = project_root / "startup_error.log"
    try:
        from app.main import main as app_main
        app_main()
        return 0
    except Exception:
        tb = traceback.format_exc()
        message = (
            "The application could not be started.\n\n"
            f"A diagnostic log was written to:\n{log_path}\n\n"
            "Details:\n" + tb
        )
        try:
            log_path.write_text(tb, encoding="utf-8")
        except Exception:
            pass
        _show_startup_error(message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
