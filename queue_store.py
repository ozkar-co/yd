"""Cola de reproducción: archivos locales y URLs pendientes."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from paths import ensure_root, queue_path

_lock = threading.Lock()


def _default() -> dict[str, Any]:
    return {"items": []}


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _default()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError(f"cola inválida: {path}")
    return data


def _save(path: Path, data: dict[str, Any]) -> None:
    ensure_root(path.parent)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def list_items(root: Path | None = None) -> list[dict[str, Any]]:
    with _lock:
        return list(_load(queue_path(root))["items"])


def _write_items(items: list[dict[str, Any]], root: Path | None = None) -> None:
    path = queue_path(root)
    with _lock:
        _save(path, {"items": items})


def enqueue_file(path: Path, root: Path | None = None) -> None:
    resolved = str(path.resolve())
    items = list_items(root)
    if any(
        i.get("kind") == "file" and i.get("path") == resolved for i in items
    ):
        return
    items.append({"kind": "file", "path": resolved})
    _write_items(items, root)


def enqueue_url(url: str, title: str = "", root: Path | None = None) -> None:
    items = list_items(root)
    if any(i.get("kind") == "url" and i.get("url") == url for i in items):
        return
    items.append(
        {
            "kind": "url",
            "url": url,
            "title": title or url,
            "status": "pending",
        }
    )
    _write_items(items, root)


def enqueue_files(paths: list[Path], root: Path | None = None) -> int:
    n = 0
    for p in paths:
        before = len(list_items(root))
        enqueue_file(p, root)
        if len(list_items(root)) > before:
            n += 1
    return n


def promote_url(url: str, file_path: Path, root: Path | None = None) -> None:
    items = list_items(root)
    changed = False
    for i, item in enumerate(items):
        if item.get("kind") == "url" and item.get("url") == url:
            items[i] = {
                "kind": "file",
                "path": str(file_path.resolve()),
                "title": item.get("title") or file_path.name,
            }
            changed = True
            break
    if changed:
        _write_items(items, root)


def set_url_status(
    url: str, status: str, root: Path | None = None
) -> None:
    items = list_items(root)
    for item in items:
        if item.get("kind") == "url" and item.get("url") == url:
            item["status"] = status
            break
    _write_items(items, root)


def mark_url_error(url: str, error: str, root: Path | None = None) -> None:
    items = list_items(root)
    for item in items:
        if item.get("kind") == "url" and item.get("url") == url:
            item["status"] = "error"
            item["error"] = error
            break
    _write_items(items, root)


def clear(root: Path | None = None) -> None:
    _write_items([], root)


def ready_paths(root: Path | None = None) -> list[str]:
    out: list[str] = []
    for item in list_items(root):
        if item.get("kind") == "file" and item.get("path"):
            out.append(str(item["path"]))
    return out


def pending_urls(root: Path | None = None) -> list[dict[str, Any]]:
    return [
        i
        for i in list_items(root)
        if i.get("kind") == "url" and i.get("status") != "error"
    ]
