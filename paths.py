"""Rutas y categorías de la biblioteca yd."""

from __future__ import annotations

import os
from pathlib import Path

CATEGORIES = (
    "inbox",
    "musica",
    "entrevistas",
    "documentales",
    "videojuegos",
    "noticias",
    "otros",
)


def media_root() -> Path:
    raw = os.environ.get("YD_MEDIA_ROOT", "").strip()
    root = Path(raw).expanduser() if raw else Path.home() / "data" / "media"
    return root.resolve()


def queue_path(root: Path | None = None) -> Path:
    return (root or media_root()) / "queue.json"


def sock_path(root: Path | None = None) -> Path:
    return (root or media_root()) / "mpv.sock"


def category_dir(name: str, root: Path | None = None) -> Path:
    if name not in CATEGORIES:
        raise SystemExit(
            f"categoría desconocida: {name} "
            f"(válidas: {', '.join(CATEGORIES)})"
        )
    return (root or media_root()) / name


def ensure_layout(root: Path | None = None) -> Path:
    root = root or media_root()
    root.mkdir(parents=True, exist_ok=True)
    for name in CATEGORIES:
        (root / name).mkdir(exist_ok=True)
    qp = queue_path(root)
    if not qp.is_file():
        qp.write_text('{"items":[]}\n', encoding="utf-8")
    return root
