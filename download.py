"""Descarga YouTube ≤720p."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp

from paths import RESERVED, VIDEO_EXT, category_dir, ensure_root, media_root

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
        opts["cookiefile"] = _cookie_snapshot(path)
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
        opts["cookiefile"] = _cookie_snapshot(default.resolve())
    return opts


def _cookie_snapshot(src: Path) -> str:
    """Copia temporal. yt-dlp reescribe el cookiefile al cerrar y se lleva LOGIN_INFO."""
    fd, name = tempfile.mkstemp(prefix="yd-cookies-", suffix=".txt")
    os.close(fd)
    shutil.copyfile(src, name)
    return name


def _discard_cookie_snapshot(opts: dict) -> None:
    raw = opts.get("cookiefile")
    if not isinstance(raw, str):
        return
    path = Path(raw)
    if path.name.startswith("yd-cookies-"):
        path.unlink(missing_ok=True)


def cookie_status(root: Path | None = None) -> str:
    """De dónde salen las cookies, sin contactar YouTube."""
    cookies = os.environ.get("YD_COOKIES", "").strip()
    browser = os.environ.get("YD_COOKIES_FROM_BROWSER", "").strip()
    if cookies and browser:
        return "mal: definí solo YD_COOKIES o YD_COOKIES_FROM_BROWSER"
    if cookies:
        path = Path(cookies).expanduser()
        return _cookie_file_status(path, f"YD_COOKIES {path}")
    if browser:
        return f"navegador {browser} (se leen al descargar)"
    default = (root or media_root()) / "cookies.txt"
    if not default.is_file():
        return "no (YouTube puede dar 403)"
    return _cookie_file_status(default, default.name)


def _cookie_file_status(path: Path, label: str) -> str:
    if not path.is_file():
        return f"no existe {label}"
    if path.stat().st_size == 0:
        return f"vacío {label}"
    text = path.read_text(encoding="utf-8", errors="replace")
    names = _cookie_names(text)
    if "youtube.com" not in text and "youtu.be" not in text:
        return f"{label} (sin cookies de youtube)"
    if "LOGIN_INFO" not in names or not (
        {"SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID"} & names
    ):
        return f"{label} (sin sesión: falta LOGIN_INFO o SAPISID)"
    return f"ok {label}"


def _cookie_names(text: str) -> set[str]:
    names: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_") :]
        elif not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            names.add(parts[5])
    return names


def is_playlist_url(url: str) -> bool:
    """URL de playlist. Un watch?v= con list= sigue siendo un vídeo."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    path = parsed.path.lower().rstrip("/")
    if path.endswith("/playlist"):
        return True
    return "list" in qs and "v" not in qs


def playlist_folder_name(title: str) -> str:
    name = re.sub(r'[\x00-\x1f\\/:*?"<>|]+', " ", title)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name or name in RESERVED or name.startswith("."):
        return "playlist"
    return name[:80]


def download_into(url: str, *, root: Path | None = None) -> list[Path]:
    """Un vídeo va a inbox. Una playlist, a una carpeta con su título."""
    root = ensure_root(root)
    if not is_playlist_url(url):
        return [download_url(url, category="inbox", root=root)]
    return _download_playlist(url, root)


def download_url(
    url: str,
    *,
    category: str = "inbox",
    root: Path | None = None,
) -> Path:
    paths = _download_to(
        url, category=category, root=root, noplaylist=True
    )
    if len(paths) == 1:
        return paths[0]
    return max(paths, key=lambda p: p.stat().st_mtime)


_ID_IN_NAME = re.compile(r"\[([^\[\]]+)\]")
_GONE = (
    "video unavailable",
    "private video",
    "has been removed",
    "video has been removed",
)


def video_id_from_url(url: str) -> str:
    """Id de YouTube en la URL. Vacío si no está a la vista."""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    parts = [p for p in parsed.path.split("/") if p]
    if host == "youtu.be":
        return parts[0] if parts else ""
    if host not in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
        return ""
    found = parse_qs(parsed.query).get("v", [""])[0].strip()
    if found:
        return found
    for marker in ("shorts", "embed", "live", "v"):
        if marker in parts:
            i = parts.index(marker)
            if i + 1 < len(parts):
                return parts[i + 1]
    return ""


def _ids_in_name(path: Path) -> list[str]:
    return [m.strip() for m in _ID_IN_NAME.findall(path.stem) if m.strip()]


def _remember(found: dict[str, Path], vid: str, path: Path) -> None:
    current = found.get(vid)
    if current is not None and current.suffix.lower() == ".mp4":
        return
    found[vid] = path


def _skipped_media_path(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part.startswith(".") or part in RESERVED for part in rel.parts)


def index_video_ids(root: Path) -> dict[str, Path]:
    """Todo texto entre [] , en cualquier carpeta, cuenta como ya descargado."""
    found: dict[str, Path] = {}
    if not root.is_dir():
        return found
    files = sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in VIDEO_EXT
        and not _skipped_media_path(p, root)
    )
    for path in files:
        resolved = path.resolve()
        for vid in _ids_in_name(path):
            _remember(found, vid, resolved)
    return found


def _index_by_id(dest: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not dest.is_dir():
        return found
    files = sorted(
        p
        for p in dest.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXT
    )
    for path in files:
        resolved = path.resolve()
        for vid in _ids_in_name(path):
            _remember(found, vid, resolved)
    return found


def _probe_video_id(url: str, root: Path) -> str:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "noplaylist": True,
        **_auth_opts(root),
    }
    info = None
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError:
        return ""
    finally:
        _discard_cookie_snapshot(opts)
    if isinstance(info, dict):
        return str(info.get("id") or "")
    return ""


def _existing_video(url: str, root: Path) -> Path | None:
    vid = video_id_from_url(url)
    if not vid:
        vid = _probe_video_id(url, root)
    if not vid:
        return None
    return index_video_ids(root).get(vid)


def _entry_url(entry: dict) -> str:
    vid = str(entry.get("id") or "")
    url = str(entry.get("url") or entry.get("webpage_url") or "")
    if url.startswith(("http://", "https://")):
        return url
    if vid:
        return f"https://www.youtube.com/watch?v={vid}"
    return ""


def _playlist_plan(
    entries: list[dict], existing: dict[str, Path]
) -> list[dict]:
    plan: list[dict] = []
    for entry in entries:
        vid = str(entry.get("id") or "")
        if vid and vid in existing:
            plan.append({"action": "skip", "path": existing[vid], "id": vid})
            continue
        url = _entry_url(entry)
        if not url:
            continue
        plan.append({"action": "download", "url": url, "id": vid})
    return plan


def _gone(msg: str) -> bool:
    low = msg.lower()
    return any(token in low for token in _GONE)


def _short(msg: str) -> str:
    line = msg.splitlines()[0].strip()
    return line[:180]


def _playlist_info(url: str, root: Path) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "noplaylist": False,
        **_auth_opts(root),
    }
    info = None
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        _raise_download(exc)
    finally:
        _discard_cookie_snapshot(opts)
    if not isinstance(info, dict):
        raise RuntimeError("playlist vacía")
    return info


def _download_playlist(url: str, root: Path) -> list[Path]:
    info = _playlist_info(url, root)
    title = str(info.get("title") or info.get("id") or "playlist")
    folder = playlist_folder_name(title)
    entries = [e for e in (info.get("entries") or []) if isinstance(e, dict)]
    plan = _playlist_plan(entries, index_video_ids(root))
    if not plan:
        raise RuntimeError("playlist vacía")
    n_skip = sum(step["action"] == "skip" for step in plan)
    n_dl = sum(step["action"] == "download" for step in plan)
    if n_skip:
        extra = f", siguen {n_dl}" if n_dl else ""
        print(f"\n[dl] {n_skip} ya en la biblioteca{extra}", flush=True)
    paths: list[Path] = []
    failures: list[str] = []
    for step in plan:
        if step["action"] == "skip":
            paths.append(step["path"])
            continue
        try:
            paths.extend(
                _download_to(
                    step["url"],
                    category=folder,
                    root=root,
                    noplaylist=True,
                )
            )
        except RuntimeError as exc:
            if _gone(str(exc)):
                continue
            failures.append(_short(str(exc)))
    if failures:
        raise RuntimeError(
            f"faltan {len(failures)} en [{folder}] "
            f"(volvé a lanzar dl); {failures[0]}"
        )
    if not paths:
        raise RuntimeError(f"playlist sin vídeos en [{folder}]")
    return paths


def _prepare_runtime() -> None:
    """deno resuelve la firma de YouTube. El instalador lo deja en ~/.local/deno/bin."""
    extra = Path.home() / ".local" / "deno" / "bin"
    if not (extra / "deno").is_file():
        return
    entry = str(extra)
    path = os.environ.get("PATH", "")
    if entry not in path.split(":"):
        os.environ["PATH"] = f"{entry}:{path}" if path else entry


def _download_to(
    url: str,
    *,
    category: str,
    root: Path | None,
    noplaylist: bool,
) -> list[Path]:
    root = ensure_root(root)
    found = _existing_video(url, root)
    if found is not None:
        print(f"\n[dl] ya está [{found.parent.name}]: {found.name}", flush=True)
        return [found]
    _prepare_runtime()
    dest = category_dir(category, root, create=True)
    before = {p.resolve() for p in dest.iterdir() if p.is_file()}
    opts = {
        "format": FORMAT,
        "outtmpl": str(dest / "%(title)s [%(id)s].%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": noplaylist,
        "overwrites": False,
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "writeautomaticsub": False,
        "subtitleslangs": ["es", "en"],
        "subtitlesformat": "vtt/srt/best",
        # Solver de firmas (edad / n-challenge). Sin esto yt-dlp no baja el script.
        "remote_components": ["ejs:github"],
        **_auth_opts(root),
    }
    if not noplaylist:
        opts["ignoreerrors"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        _raise_download(exc)
    finally:
        _discard_cookie_snapshot(opts)
    videos = _videos_from_info(info, dest, before)
    if not videos:
        raise RuntimeError("descarga sin archivo de vídeo nuevo")
    return videos


def _raise_download(exc: yt_dlp.utils.DownloadError) -> None:
    msg = str(exc)
    if "403" in msg or "Forbidden" in msg:
        raise RuntimeError(
            f"{msg}\n"
            "403: exportá sesión (YD_COOKIES_FROM_BROWSER o "
            "media/cookies.txt). Ver README."
        ) from exc
    raise RuntimeError(msg) from exc


def _videos_from_info(
    info: dict | None, dest: Path, before: set[Path]
) -> list[Path]:
    ordered: list[Path] = []
    seen: set[Path] = set()

    def add(raw: object) -> None:
        if not isinstance(raw, str) or not raw:
            return
        path = Path(raw)
        if path.suffix.lower() not in VIDEO_EXT or not path.is_file():
            return
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        ordered.append(resolved)

    def walk(entry: dict) -> None:
        for item in entry.get("requested_downloads") or []:
            if isinstance(item, dict):
                add(item.get("filepath") or item.get("filename"))
        add(entry.get("filepath"))
        add(entry.get("_filename"))

    if info:
        entries = info.get("entries")
        if entries:
            for entry in entries:
                if isinstance(entry, dict):
                    walk(entry)
        else:
            walk(info)
    if ordered:
        return ordered
    if info:
        indexed = _index_by_id(dest)
        vid = info.get("id")
        if isinstance(vid, str) and vid in indexed:
            return [indexed[vid]]
        for entry in info.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id")
            if isinstance(eid, str) and eid in indexed:
                ordered.append(indexed[eid])
        if ordered:
            return ordered
    after = {p.resolve() for p in dest.iterdir() if p.is_file()}
    return sorted(p for p in after - before if p.suffix.lower() in VIDEO_EXT)


def search_yt(query: str, limit: int = 9) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        **_auth_opts(),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    finally:
        _discard_cookie_snapshot(opts)
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
