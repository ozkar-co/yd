"""Worker: descarga en segundo plano ítems URL de la cola."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import download
import mpvctl
import queue_store

_stop = threading.Event()
_thread: threading.Thread | None = None
_root: Path | None = None


def start(root: Path | None = None) -> None:
    global _thread, _root
    _root = root
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="yd-dl", daemon=True)
    _thread.start()


def stop_worker() -> None:
    _stop.set()


def _loop() -> None:
    while not _stop.is_set():
        pending = queue_store.pending_urls(_root)
        if not pending:
            _stop.wait(1.0)
            continue
        item = pending[0]
        if item.get("status") == "downloading":
            _stop.wait(0.5)
            continue
        url = item["url"]
        queue_store.set_url_status(url, "downloading", _root)
        try:
            path = download.download_url(url, category="inbox", root=_root)
            queue_store.promote_url(url, path, _root)
            if mpvctl.is_running(_root):
                try:
                    mpvctl.append_file(str(path), _root)
                except RuntimeError:
                    pass
            print(f"\n[dl] listo: {path.name}", flush=True)
            print("yd> ", end="", flush=True)
        except Exception as exc:  # noqa: BLE001 — worker no debe morir
            queue_store.mark_url_error(url, str(exc), _root)
            print(f"\n[dl] error: {exc}", flush=True)
            print("yd> ", end="", flush=True)
        time.sleep(0.2)
