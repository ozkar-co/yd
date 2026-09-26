"""Índice en memoria: IDs únicos por archivo en media/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from paths import VIDEO_EXT, list_categories, media_root


@dataclass(frozen=True)
class LibItem:
    id: int
    path: Path
    category: str


def scan(root: Path | None = None, category: str | None = None) -> list[LibItem]:
    root = root or media_root()
    if not root.is_dir():
        return []
    cats = [category] if category else list_categories(root)
    if category and category not in list_categories(root):
        raise FileNotFoundError(f"no existe categoría: {category}")
    items: list[LibItem] = []
    n = 1
    for cat in cats:
        cdir = root / cat
        if not cdir.is_dir():
            continue
        files = sorted(
            p
            for p in cdir.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXT
        )
        for f in files:
            items.append(LibItem(id=n, path=f.resolve(), category=cat))
            n += 1
    return items


def by_id(items: list[LibItem], item_id: int) -> LibItem:
    for it in items:
        if it.id == item_id:
            return it
    raise KeyError(item_id)
