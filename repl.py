"""REPL yd — estación multimedia."""

from __future__ import annotations

import shlex
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import download
import library
import mpvctl
import queue_store
import worker
from paths import category_dir, ensure_root, list_categories, media_root

HELP = """\
comandos:
  list [cat]     biblioteca (IDs únicos) o una categoría
  play [n]       reproduce cola, o el ítem n
  queue          muestra cola de reproducción
  queue <n|cat>  encola ítem (lib/search) o categoría entera
  search <q>     busca en YouTube (luego queue <n>)
  dl <url>       vídeo → inbox; playlist → carpeta (si ya está, salta)
  mv <n> <cat>   mueve ítem a categoría (crea cat si no existe)
  cc [es|en]     subtítulos on (idioma) / off (sin arg)
  next pause     control mpv
  stop           cierra mpv
  status         config (cats, archivos, cookies) + mpv + cola
  help exit      ayuda / salir
"""


class Repl:
    def __init__(self) -> None:
        self.root = ensure_root()
        self.lib: list[library.LibItem] = []
        self.search_hits: list[dict] = []
        self.focus = "lib"  # lib | search
        self.cc_lang: str | None = None  # sesión: es|en|None
        worker.start(self.root)

    def refresh_lib(self, category: str | None = None) -> None:
        self.lib = library.scan(self.root, category=category)
        self.focus = "lib"

    def cmd_list(self, args: list[str]) -> None:
        cat = args[0] if args else None
        try:
            self.refresh_lib(cat)
        except FileNotFoundError as exc:
            print(exc)
            return
        cats = list_categories(self.root)
        if not cat:
            print(f"root: {self.root}")
            if not cats:
                print("(sin categorías — mv n <nombre> crea una)")
            else:
                print("categorías: " + ", ".join(cats))
        if not self.lib:
            print("(sin archivos)")
            return
        current_cat = None
        for it in self.lib:
            if it.category != current_cat:
                current_cat = it.category
                print(f"\n[{current_cat}]")
            print(f"  {it.id:3d}. {it.path.name}")

    def cmd_search(self, args: list[str]) -> None:
        if not args:
            print("uso: search <query>")
            return
        query = " ".join(args)
        print(f"buscando: {query}")
        try:
            hits = download.search_yt(query)
        except Exception as exc:  # noqa: BLE001
            print(f"error: {exc}")
            return
        if not hits:
            print("sin resultados")
            return
        self.search_hits = hits
        self.focus = "search"
        for i, h in enumerate(hits, 1):
            print(f"  {i:3d}. {h['title']}")

    def _resolve_queue_target(self, token: str) -> None:
        # categoría
        if not token.isdigit():
            cat = token
            if cat not in list_categories(self.root):
                print(f"no existe categoría: {cat}")
                return
            items = library.scan(self.root, category=cat)
            n = queue_store.enqueue_files([it.path for it in items], self.root)
            print(f"encolados {n} de [{cat}]")
            return
        n = int(token)
        if self.focus == "search":
            if n < 1 or n > len(self.search_hits):
                print(f"índice search fuera de rango: {n}")
                return
            hit = self.search_hits[n - 1]
            queue_store.enqueue_url(hit["url"], hit["title"], self.root)
            print(f"encolado (dl): {hit['title']}")
            return
        try:
            it = library.by_id(self.lib, n)
        except KeyError:
            if not self.lib:
                self.refresh_lib()
            try:
                it = library.by_id(self.lib, n)
            except KeyError:
                print(f"no hay ítem {n} — corre list")
                return
        queue_store.enqueue_file(it.path, self.root)
        print(f"encolado: {it.path.name}")

    def cmd_dl(self, args: list[str]) -> None:
        if len(args) != 1 or not _is_url(args[0]):
            print("uso: dl <url>")
            return
        url = args[0]
        state = queue_store.enqueue_url(url, url, self.root)
        kind = "playlist" if download.is_playlist_url(url) else "vídeo"
        if state == "queued":
            print(f"ya en cola: {url}")
            return
        if state == "retry":
            print(f"reintento ({kind}): {url}")
            return
        print(f"encolado ({kind}): {url}")

    def cmd_queue(self, args: list[str]) -> None:
        if not args:
            items = queue_store.list_items(self.root)
            if not items:
                print("(cola vacía)")
                return
            for i, item in enumerate(items, 1):
                if item.get("kind") == "file":
                    name = Path(item["path"]).name
                    print(f"  {i:3d}. [ok] {name}")
                else:
                    st = item.get("status") or "pending"
                    title = item.get("title") or item.get("url")
                    print(f"  {i:3d}. [{st}] {title}")
            return
        self._resolve_queue_target(args[0])

    def cmd_play(self, args: list[str]) -> None:
        if not args:
            ready = queue_store.ready_paths(self.root)
            pending = queue_store.pending_urls(self.root)
            if not ready and pending:
                print(
                    f"cola sin archivos listos "
                    f"({len(pending)} descargando/pendientes)"
                )
                return
            if not ready:
                print("cola vacía — queue <n|cat> o search")
                return
            try:
                mpvctl.play_files(
                    ready, self.root, sub_lang=self.cc_lang
                )
            except RuntimeError as exc:
                print(exc)
                return
            print(f"play cola: {len(ready)} listos"
                  + (f", {len(pending)} pendientes" if pending else ""))
            return
        if not args[0].isdigit():
            print("uso: play [n]")
            return
        n = int(args[0])
        if self.focus == "search":
            print("search → usá: queue n  (descarga async); luego play")
            return
        if not self.lib:
            self.refresh_lib()
        try:
            it = library.by_id(self.lib, n)
        except KeyError:
            print(f"no hay ítem {n} — corre list")
            return
        try:
            mpvctl.play_one(
                str(it.path), self.root, sub_lang=self.cc_lang
            )
        except RuntimeError as exc:
            print(exc)
            return
        print(f"play: {it.path.name}")

    def cmd_mv(self, args: list[str]) -> None:
        if len(args) != 2 or not args[0].isdigit():
            print("uso: mv <n> <categoria>")
            return
        n = int(args[0])
        cat = args[1]
        if not self.lib:
            self.refresh_lib()
        try:
            it = library.by_id(self.lib, n)
        except KeyError:
            print(f"no hay ítem {n} — corre list")
            return
        dest_dir = category_dir(cat, self.root, create=True)
        dest = dest_dir / it.path.name
        if dest.exists():
            print(f"ya existe: {dest}")
            return
        shutil.move(str(it.path), str(dest))
        # Sidecars de subs: Title [id].es.vtt, etc.
        moved_subs = 0
        stem = it.path.stem
        parent = it.path.parent
        for p in list(parent.iterdir()):
            if not p.is_file():
                continue
            if p.name.startswith(stem + ".") and p.suffix.lower() in {
                ".vtt",
                ".srt",
                ".ass",
            }:
                target = dest_dir / p.name
                if not target.exists():
                    shutil.move(str(p), str(target))
                    moved_subs += 1
        extra = f" (+{moved_subs} subs)" if moved_subs else ""
        print(f"movido → {dest}{extra}")
        self.refresh_lib()

    def cmd_cc(self, args: list[str]) -> None:
        if not args:
            self.cc_lang = None
            try:
                mpvctl.apply_subs(None, self.root)
            except RuntimeError as exc:
                print(exc)
                return
            print("cc: off")
            return
        lang = args[0].lower()
        if lang not in ("es", "en"):
            print("uso: cc [es|en]  (sin arg = off)")
            return
        self.cc_lang = lang
        try:
            mpvctl.apply_subs(lang, self.root)
        except RuntimeError as exc:
            # mpv cerrado: queda para el próximo play
            print(f"cc: {lang} (sesión; mpv no corría: {exc})")
            return
        print(f"cc: {lang}")

    def cmd_next(self, _: list[str]) -> None:
        try:
            mpvctl.next_track(self.root)
            print("next")
        except RuntimeError as exc:
            print(exc)

    def cmd_pause(self, _: list[str]) -> None:
        try:
            mpvctl.pause_toggle(self.root)
            print("pause")
        except RuntimeError as exc:
            print(exc)

    def cmd_stop(self, _: list[str]) -> None:
        mpvctl.quit(self.root)
        print("mpv cerrado")

    def config_lines(self) -> list[str]:
        cats = list_categories(self.root)
        items = library.scan(self.root)
        counts: dict[str, int] = {}
        for it in items:
            counts[it.category] = counts.get(it.category, 0) + 1
        if cats:
            shown = ", ".join(f"{c} ({counts.get(c, 0)})" for c in cats)
            cat_line = f"categorías: {shown}"
        else:
            cat_line = "categorías: (ninguna — mv n <nombre> crea una)"
        tools = []
        for name in ("mpv", "ffmpeg"):
            tools.append(
                f"{name} {'ok' if shutil.which(name) else 'no está en PATH'}"
            )
        return [
            cat_line,
            f"archivos: {len(items)}",
            f"cookies: {download.cookie_status(self.root)}",
            "herramientas: " + ", ".join(tools),
        ]

    def cmd_status(self, _: list[str]) -> None:
        print(f"root: {self.root}")
        for line in self.config_lines():
            print(line)
        print(f"focus: {self.focus}")
        print(mpvctl.status_text(self.root, sub_lang=self.cc_lang))
        items = queue_store.list_items(self.root)
        print(f"cola: {len(items)} ítem(s)")

    def dispatch(self, line: str) -> bool:
        """True = seguir; False = exit."""
        line = line.strip()
        if not line:
            return True
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            print(f"línea inválida: {exc}")
            return True
        cmd, args = parts[0].lower(), parts[1:]
        if cmd in ("exit", "quit", "q"):
            return False
        if cmd in ("help", "?"):
            print(HELP)
            return True
        handlers = {
            "list": self.cmd_list,
            "search": self.cmd_search,
            "dl": self.cmd_dl,
            "queue": self.cmd_queue,
            "play": self.cmd_play,
            "mv": self.cmd_mv,
            "cc": self.cmd_cc,
            "next": self.cmd_next,
            "pause": self.cmd_pause,
            "stop": self.cmd_stop,
            "status": self.cmd_status,
        }
        fn = handlers.get(cmd)
        if not fn:
            print(f"comando desconocido: {cmd} (help)")
            return True
        fn(args)
        return True

    def run(self) -> int:
        print(f"yd — media: {self.root}")
        for line in self.config_lines():
            print(line)
        print("help para comandos; exit para salir")
        while True:
            try:
                line = input("yd> ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print("^C")
                continue
            if not self.dispatch(line):
                break
        mpvctl.quit(self.root)
        worker.stop_worker()
        return 0


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def main() -> int:
    return Repl().run()


if __name__ == "__main__":
    raise SystemExit(main())
