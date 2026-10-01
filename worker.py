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
_watch: threading.Thread | None = None
_root: Path | None = None


def start(root: Path | None = None) -> None:
    global _thread, _watch, _root
    _root = root
    queue_store.reset_interrupted(root)
    _stop.clear()
    if not (_thread and _thread.is_alive()):
        _thread = threading.Thread(target=_loop, name="yd-dl", daemon=True)
        _thread.start()
    if not (_watch and _watch.is_alive()):
        _watch = threading.Thread(target=_watch_play, name="yd-play", daemon=True)
        _watch.start()


def _watch_play() -> None:
    """Saca de la cola el archivo que mpv ya está reproduciendo."""
    while not _stop.is_set():
        try:
            mpvctl.sync_queue(_root)
        except Exception:  # noqa: BLE001 — el watcher no debe morir
            pass
        _stop.wait(0.5)


def stop_worker() -> None:
    _stop.set()


def _loop() -> None:
    while not _stop.is_set():
        try:
            pending = queue_store.pending_urls(_root)
        except Exception as exc:  # noqa: BLE001 — worker no debe morir
            print(f"\n[dl] cola: {exc}", flush=True)
            print("yd> ", end="", flush=True)
            _stop.wait(2.0)
            continue
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
            paths = download.download_into(url, root=_root)
            queue_store.replace_url_with_files(url, paths, _root)
            if paths and mpvctl.is_running(_root):
                for path in paths:
                    try:
                        mpvctl.append_file(str(path), _root)
                    except RuntimeError:
                        break
            if not paths:
                print("yd> ", end="", flush=True)
                time.sleep(0.2)
                continue
            if len(paths) == 1:
                print(f"\n[dl] listo: {paths[0].name}", flush=True)
            else:
                print(
                    f"\n[dl] listo: {len(paths)} en [{paths[0].parent.name}]",
                    flush=True,
                )
            print("yd> ", end="", flush=True)
        except Exception as exc:  # noqa: BLE001 — worker no debe morir
            queue_store.mark_url_error(url, str(exc), _root)
            print(f"\n[dl] error: {exc}", flush=True)
            print("yd> ", end="", flush=True)
        time.sleep(0.2)
