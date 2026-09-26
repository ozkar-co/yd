"""Descarga YouTube ≤720p a inbox/."""

from __future__ import annotations

import os
from pathlib import Path

import yt_dlp

from paths import category_dir, media_root

FORMAT = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"


def _auth_opts(root: Path | None = None) -> dict:
    """Sesión YouTube vía cookies (no hay login/password en yt-dlp)."""
    opts: dict = {}
    cookies = os.environ.get("YD_COOKIES", "").strip()
    browser = os.environ.get("YD_COOKIES_FROM_BROWSER", "").strip()
    if cookies and browser:
        raise SystemExit(
            "definí solo una: YD_COOKIES o YD_COOKIES_FROM_BROWSER"
        )
    if cookies:
        path = Path(cookies).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"no existe archivo de cookies: {path}")
        opts["cookiefile"] = str(path)
        return opts
    if browser:
        # firefox | chrome | chromium | brave
        # opcional perfil: firefox:default-release
        if ":" in browser:
            name, profile = browser.split(":", 1)
            opts["cookiesfrombrowser"] = (name, profile, None, None)
        else:
            opts["cookiesfrombrowser"] = (browser, None, None, None)
        return opts
    default = (root or media_root()) / "cookies.txt"
    if default.is_file():
        opts["cookiefile"] = str(default.resolve())
    return opts


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
        **_auth_opts(root),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc)
        if "403" in msg or "Forbidden" in msg:
            raise SystemExit(
                f"{msg}\n"
                "YouTube bloqueó la descarga (403). Exportá sesión:\n"
                "  1) En el AIO, iniciá sesión en YouTube (Firefox/Chrome).\n"
                "  2) YD_COOKIES_FROM_BROWSER=firefox ./run.sh dl URL\n"
                "  o cookies.txt en ~/data/media/ (Get cookies.txt LOCALLY).\n"
                "  Ver README → Sesión YouTube."
            ) from exc
        raise SystemExit(msg) from exc
    after = {p.resolve() for p in inbox.iterdir() if p.is_file()}
    new = after - before
    if not new:
        raise SystemExit(
            "descarga terminó sin archivo nuevo en inbox/ "
            "(¿ya existía? revisá inbox)"
        )
    if len(new) > 1:
        return max(new, key=lambda p: p.stat().st_mtime)
    return next(iter(new))
