"""Cola de reproducción (queue.json)."""

from __future__ import annotations

import json
from pathlib import Path

from paths import queue_path


def _load(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"falta cola: {path} (corre: yd init)")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "items" not in data:
        raise SystemExit(f"cola inválida: {path}")
    items = data["items"]
    if not isinstance(items, list):
        raise SystemExit(f"cola inválida (items): {path}")
    return {"items": [str(x) for x in items]}


def _save(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def list_items(root: Path | None = None) -> list[str]:
    return _load(queue_path(root))["items"]


def enqueue(file_path: Path, root: Path | None = None) -> None:
    path = queue_path(root)
    data = _load(path)
    resolved = str(file_path.resolve())
    if resolved in data["items"]:
        return
    if not file_path.is_file():
        raise SystemExit(f"no existe archivo: {file_path}")
    data["items"].append(resolved)
    _save(path, data)


def remove_at(index: int, root: Path | None = None) -> str:
    path = queue_path(root)
    data = _load(path)
    if index < 1 or index > len(data["items"]):
        raise SystemExit(f"índice fuera de rango: {index}")
    item = data["items"].pop(index - 1)
    _save(path, data)
    return item


def clear(root: Path | None = None) -> None:
    _save(queue_path(root), {"items": []})
