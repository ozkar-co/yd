"""Control de mpv vía IPC Unix socket."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

from paths import ensure_root, sock_path

_proc: subprocess.Popen | None = None


def _find_xauthority() -> str | None:
    home = Path.home()
    candidates = [
        os.environ.get("XAUTHORITY"),
        str(home / ".Xauthority"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return None


def _ipc(cmd: list, root: Path | None = None, timeout: float = 5.0) -> dict:
    sock = sock_path(root)
    if not sock.exists():
        raise RuntimeError(f"mpv no está corriendo (falta {sock})")
    payload = json.dumps({"command": cmd}).encode("utf-8") + b"\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect(str(sock))
        except OSError as exc:
            raise RuntimeError(f"no conecta a mpv IPC: {exc}") from exc
        s.sendall(payload)
        chunks: list[bytes] = []
        while True:
            try:
                chunk = s.recv(4096)
            except socket.timeout as exc:
                raise RuntimeError("timeout leyendo respuesta mpv") from exc
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if not raw:
        raise RuntimeError("mpv no respondió")
    line = raw.splitlines()[0]
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"respuesta mpv inválida: {line!r}") from exc


def is_running(root: Path | None = None) -> bool:
    sock = sock_path(root)
    if not sock.exists():
        return False
    try:
        resp = _ipc(["get_property", "idle-active"], root=root)
        return resp.get("error") == "success"
    except RuntimeError:
        return False


def ensure_running(root: Path | None = None) -> None:
    global _proc
    if is_running(root):
        return
    ensure_root(root)
    sock = sock_path(root)
    if sock.exists():
        try:
            sock.unlink()
        except OSError:
            pass
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    xauth = _find_xauthority()
    if xauth:
        env["XAUTHORITY"] = xauth
    cmd = [
        "mpv",
        "--idle=yes",
        "--force-window=yes",
        "--fullscreen",
        "--keep-open=yes",
        f"--input-ipc-server={sock}",
        "--no-terminal",
    ]
    try:
        _proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("mpv no está instalado") from exc
    for _ in range(50):
        time.sleep(0.1)
        if is_running(root):
            return
    raise RuntimeError(
        "mpv no arrancó (¿DISPLAY/:0 y sesión gráfica activos?)"
    )


def play_files(paths: list[str], root: Path | None = None) -> None:
    if not paths:
        raise RuntimeError("nada para reproducir")
    ensure_running(root)
    _ipc(["playlist-clear"], root=root)
    for i, p in enumerate(paths):
        mode = "replace" if i == 0 else "append"
        resp = _ipc(["loadfile", p, mode], root=root)
        if resp.get("error") != "success":
            raise RuntimeError(f"loadfile falló ({p}): {resp}")
    _ipc(["set_property", "pause", False], root=root)


def play_one(path: str, root: Path | None = None) -> None:
    play_files([path], root=root)


def append_file(path: str, root: Path | None = None) -> None:
    if not is_running(root):
        return
    resp = _ipc(["loadfile", path, "append"], root=root)
    if resp.get("error") != "success":
        raise RuntimeError(f"append falló: {resp}")


def next_track(root: Path | None = None) -> None:
    if not is_running(root):
        raise RuntimeError("mpv no está corriendo")
    resp = _ipc(["playlist-next", "weak"], root=root)
    if resp.get("error") != "success":
        raise RuntimeError(f"next falló: {resp}")


def pause_toggle(root: Path | None = None) -> None:
    if not is_running(root):
        raise RuntimeError("mpv no está corriendo")
    resp = _ipc(["cycle", "pause"], root=root)
    if resp.get("error") != "success":
        raise RuntimeError(f"pause falló: {resp}")


def quit(root: Path | None = None) -> None:
    """Cierra mpv por completo."""
    global _proc
    sock = sock_path(root)
    if is_running(root):
        try:
            _ipc(["quit"], root=root)
        except RuntimeError:
            pass
        time.sleep(0.2)
    if _proc is not None and _proc.poll() is None:
        try:
            os.killpg(os.getpgid(_proc.pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                _proc.terminate()
            except OSError:
                pass
        try:
            _proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _proc.kill()
    _proc = None
    if sock.exists():
        try:
            sock.unlink()
        except OSError:
            pass


def status_text(root: Path | None = None) -> str:
    if not is_running(root):
        return "mpv: cerrado"
    path = _ipc(["get_property", "path"], root=root)
    pause = _ipc(["get_property", "pause"], root=root)
    pos = _ipc(["get_property", "playlist-pos"], root=root)
    count = _ipc(["get_property", "playlist-count"], root=root)
    title = path.get("data") or "(idle)"
    paused = pause.get("data")
    state = "pausa" if paused else "play"
    return (
        f"mpv: {state}\n"
        f"archivo: {title}\n"
        f"playlist: {pos.get('data')}/{count.get('data')}"
    )
