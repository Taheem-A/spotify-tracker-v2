from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SUPPORTED_MIN = (3, 11)
SUPPORTED_MAX = (3, 13)


def ensure_supported_python() -> None:
    version = sys.version_info[:2]
    if version < SUPPORTED_MIN or version > SUPPORTED_MAX:
        supported = "3.11, 3.12, or 3.13"
        raise SystemExit(
            f"Tracker V2 requires Python {supported}. "
            f"Detected Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}."
        )


if __name__ == "__main__":
    ensure_supported_python()
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
        app_dir=str(ROOT),
    )
