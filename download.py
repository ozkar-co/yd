"""Descarga YouTube ≤720p a inbox/."""

from __future__ import annotations

from pathlib import Path

import yt_dlp

from paths import category_dir

FORMAT = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"


def download_url(url: str, root: Path | None = None) -> Path:
    inbox = category_dir("inbox", root)
    before = {p.resolve() for p in inbox.iterdir() if p.is_file()}
    outtmpl = str(inbox / "%(title)s [%(id)s].%(ext)s")
    opts = {
        "format": FORMAT,
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    after = {p.resolve() for p in inbox.iterdir() if p.is_file()}
    new = after - before
    if not new:
        # mismo archivo re-descargado / ya existía
        raise SystemExit(
            "descarga terminó sin archivo nuevo en inbox/ "
            "(¿ya existía? revisá inbox)"
        )
    if len(new) > 1:
        # merge puede tocar varios; tomar el más reciente
        return max(new, key=lambda p: p.stat().st_mtime)
    return next(iter(new))
