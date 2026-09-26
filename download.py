"""Descarga YouTube ≤720p."""

from __future__ import annotations

import os
from pathlib import Path

import yt_dlp

from paths import VIDEO_EXT, category_dir, ensure_root, media_root

# Preferir audio en español si existe; si no, mejor audio.
FORMAT = (
    "bestvideo[height<=720]+bestaudio[language^=es]/"
    "bestvideo[height<=720]+bestaudio/"
    "best[height<=720]/best"
)


def _auth_opts(root: Path | None = None) -> dict:
    opts: dict = {}
    cookies = os.environ.get("YD_COOKIES", "").strip()
    browser = os.environ.get("YD_COOKIES_FROM_BROWSER", "").strip()
    if cookies and browser:
        raise RuntimeError(
            "definí solo una: YD_COOKIES o YD_COOKIES_FROM_BROWSER"
        )
    if cookies:
        path = Path(cookies).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"no existe archivo de cookies: {path}")
        opts["cookiefile"] = str(path)
        return opts
    if browser:
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


def download_url(
    url: str,
    *,
    category: str = "inbox",
    root: Path | None = None,
) -> Path:
    root = ensure_root(root)
    dest = category_dir(category, root, create=True)
    before = {p.resolve() for p in dest.iterdir() if p.is_file()}
    outtmpl = str(dest / "%(title)s [%(id)s].%(ext)s")
    opts = {
        "format": FORMAT,
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # Solo subs manuales (no ASR / auto-generated).
        "writesubtitles": True,
        "writeautomaticsub": False,
        "subtitleslangs": ["es", "en"],
        "subtitlesformat": "vtt/srt/best",
        **_auth_opts(root),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc)
        if "403" in msg or "Forbidden" in msg:
            raise RuntimeError(
                f"{msg}\n"
                "403: exportá sesión (YD_COOKIES_FROM_BROWSER o "
                "media/cookies.txt). Ver README."
            ) from exc
        raise RuntimeError(msg) from exc
    after = {p.resolve() for p in dest.iterdir() if p.is_file()}
    new = after - before
    videos = {p for p in new if p.suffix.lower() in VIDEO_EXT}
    if not videos:
        raise RuntimeError("descarga sin archivo de vídeo nuevo")
    if len(videos) > 1:
        return max(videos, key=lambda p: p.stat().st_mtime)
    return next(iter(videos))


def search_yt(query: str, limit: int = 9) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        **_auth_opts(),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    entries = (data or {}).get("entries") or []
    hits: list[dict] = []
    for e in entries:
        if not e:
            continue
        vid = e.get("id") or ""
        url = e.get("url") or e.get("webpage_url")
        if not url and vid:
            url = f"https://www.youtube.com/watch?v={vid}"
        if not url:
            continue
        hits.append(
            {
                "title": e.get("title") or "(sin título)",
                "url": url,
                "id": vid,
            }
        )
    return hits
