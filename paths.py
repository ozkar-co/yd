"""Raíz de biblioteca: ./media junto al proceso, o YD_MEDIA_ROOT.

En desarrollo es el directorio de trabajo. En el bundle de `make dist`
es la carpeta del ejecutable (la misma donde vive `yd`). YD_MEDIA_ROOT
la saca de ahí.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RESERVED = frozenset(
    {
        "queue.json",
        "mpv.sock",
        "cookies.txt",
        ".download-tmp",
    }
)

VIDEO_EXT = frozenset(
    {
        ".mp4",
        ".webm",
        ".mkv",
        ".m4a",
        ".opus",
        ".ogg",
        ".avi",
        ".mov",
    }
)


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def media_root() -> Path:
    raw = os.environ.get("YD_MEDIA_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (_app_dir() / "media").resolve()


def queue_path(root: Path | None = None) -> Path:
    return (root or media_root()) / "queue.json"


def sock_path(root: Path | None = None) -> Path:
    return (root or media_root()) / "mpv.sock"


def ensure_root(root: Path | None = None) -> Path:
    """Solo crea la raíz media/; no categorías."""
    root = root or media_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def is_category_dir(path: Path, root: Path) -> bool:
    if not path.is_dir():
        return False
    if path.parent != root:
        return False
    if path.name in RESERVED or path.name.startswith("."):
        return False
    return True


def list_categories(root: Path | None = None) -> list[str]:
    root = root or media_root()
    if not root.is_dir():
        return []
    cats = [
        p.name
        for p in sorted(root.iterdir())
        if is_category_dir(p, root)
    ]
    return cats


def category_dir(name: str, root: Path | None = None, *, create: bool = False) -> Path:
    root = root or media_root()
    if not name or name in RESERVED or "/" in name or name.startswith("."):
        raise ValueError(f"categoría inválida: {name!r}")
    path = root / name
    if create:
        ensure_root(root)
        path.mkdir(parents=True, exist_ok=True)
    return path
