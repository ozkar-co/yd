#!/usr/bin/env python3
"""yd — descarga YouTube + cola + mpv."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import download
import mpvctl
import queue_store
from paths import CATEGORIES, category_dir, ensure_layout, media_root


def _is_url(value: str) -> bool:
    p = urlparse(value)
    return p.scheme in ("http", "https") and bool(p.netloc)


def cmd_init(_: argparse.Namespace) -> None:
    root = ensure_layout()
    print(f"listo: {root}")


def cmd_dl(args: argparse.Namespace) -> None:
    ensure_layout()
    path = download.download_url(args.url)
    queue_store.enqueue(path)
    if mpvctl.is_running():
        mpvctl.append_file(str(path))
    print(f"descargado y encolado: {path}")


def cmd_add(args: argparse.Namespace) -> None:
    ensure_layout()
    target = args.target
    if _is_url(target):
        path = download.download_url(target)
        queue_store.enqueue(path)
        if mpvctl.is_running():
            mpvctl.append_file(str(path))
        print(f"descargado y encolado: {path}")
        return
    path = Path(target).expanduser().resolve()
    queue_store.enqueue(path)
    if mpvctl.is_running():
        mpvctl.append_file(str(path))
    print(f"encolado: {path}")


def cmd_play(_: argparse.Namespace) -> None:
    ensure_layout()
    items = queue_store.list_items()
    mpvctl.load_queue(items)
    print(f"reproduciendo {len(items)} ítem(s)")


def cmd_next(_: argparse.Namespace) -> None:
    mpvctl.next_track()
    print("next")


def cmd_stop(_: argparse.Namespace) -> None:
    mpvctl.stop()
    print("stop")


def cmd_pause(_: argparse.Namespace) -> None:
    mpvctl.pause_toggle()
    print("pause toggled")


def cmd_list(_: argparse.Namespace) -> None:
    ensure_layout()
    items = queue_store.list_items()
    if not items:
        print("(cola vacía)")
        return
    for i, item in enumerate(items, 1):
        name = Path(item).name
        print(f"{i:3d}. {name}")
        print(f"     {item}")


def cmd_status(_: argparse.Namespace) -> None:
    ensure_layout()
    print(f"root: {media_root()}")
    items = queue_store.list_items()
    print(f"cola: {len(items)} ítem(s)")
    print(mpvctl.status_text())


def cmd_mv(args: argparse.Namespace) -> None:
    ensure_layout()
    dest = category_dir(args.category)
    token = args.target
    src: Path
    if token.isdigit():
        removed = queue_store.remove_at(int(token))
        src = Path(removed)
    else:
        src = Path(token).expanduser().resolve()
        if not src.is_file():
            raise SystemExit(f"no existe: {src}")
        # quitar de cola si estaba
        items = queue_store.list_items()
        if str(src) in items:
            idx = items.index(str(src)) + 1
            queue_store.remove_at(idx)
    if args.category == "inbox":
        raise SystemExit("usá otra categoría (no inbox)")
    dest_file = dest / src.name
    if dest_file.exists():
        raise SystemExit(f"ya existe destino: {dest_file}")
    shutil.move(str(src), str(dest_file))
    print(f"movido → {dest_file}")


def cmd_search(_: argparse.Namespace) -> None:
    # legado interactivo
    from script import buscar_y_descargar

    buscar_y_descargar()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="yd",
        description="YouTube download + cola + mpv (local/SSH)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="crea ~/data/media").set_defaults(
        func=cmd_init
    )

    p_dl = sub.add_parser("dl", help="descarga URL a inbox y encola")
    p_dl.add_argument("url")
    p_dl.set_defaults(func=cmd_dl)

    p_add = sub.add_parser("add", help="encola path o descarga URL")
    p_add.add_argument("target")
    p_add.set_defaults(func=cmd_add)

    sub.add_parser("play", help="reproduce la cola en mpv").set_defaults(
        func=cmd_play
    )
    sub.add_parser("next").set_defaults(func=cmd_next)
    sub.add_parser("stop").set_defaults(func=cmd_stop)
    sub.add_parser("pause").set_defaults(func=cmd_pause)
    sub.add_parser("list", help="lista la cola").set_defaults(func=cmd_list)
    sub.add_parser("status").set_defaults(func=cmd_status)

    p_mv = sub.add_parser("mv", help="mueve a categoría")
    p_mv.add_argument("target", help="índice de cola o path")
    p_mv.add_argument(
        "category",
        help=", ".join(c for c in CATEGORIES if c != "inbox"),
    )
    p_mv.set_defaults(func=cmd_mv)

    sub.add_parser(
        "search", help="legado: búsqueda interactiva"
    ).set_defaults(func=cmd_search)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nabort", file=sys.stderr)
        raise SystemExit(130) from None
