---
title: yd — diseño
date: 2026-09-26
tags: [yd, media, diseno]
status: active
---

# yd — diseño

CLI → **REPL** de estación multimedia. Repo portable: biblioteca
por defecto `./media` junto al proceso (cwd en dev; carpeta del
ejecutable en `make dist`). `YD_MEDIA_ROOT` la pone en otra ruta.

Laura: `[PER-MEDIA]`
`estacion-multimedia.md`.

## Modelo

| Concepto | Regla |
|----------|-------|
| Raíz | `./media` junto al ejecutable, o `YD_MEDIA_ROOT` |
| Categorías | subdirs creados con `mv n cat` (no `init`) |
| IDs | asignados al hacer `list` (sesión) |
| Cola | archivos + URLs; `dl` manda un vídeo a `inbox/` y una playlist a una carpeta con su título. Al empezar a sonar, el archivo sale de la cola |
| Ya descargado | cualquier texto entre `[]` en el nombre, en cualquier carpeta, evita bajar ese id otra vez |
| `stop` | `quit` de mpv (proceso cerrado) |
| Números | `list` numera la biblioteca (`queue n`, `play n`, `mv n`). `search` numera la última búsqueda (`dl n`, y encola) |
| Cola visible | `queue` sin números, para no mezclarlos con los de `list` |
| Audio | preferir pista `es` si yt-dlp la ofrece |
| Subs | solo manuales `es`+`en` (no ASR); `cc [es\|en]` en sesión |
| Random | `random` revuelve toda la cola y la reproduce desde el inicio |
| `clear` | vacía la cola y lo que sigue en mpv; el archivo que suena sigue |

## Comandos

`list`, `play`, `queue`, `search`, `dl`, `mv`, `cc`, `random`,
`clear`, `next`, `pause`, `stop`, `status`, `help`, `exit`.

Al arrancar y en `status`: categorías (con conteo), archivos,
cookies (`YD_COOKIES`, `YD_COOKIES_FROM_BROWSER` o `cookies.txt`)
y si `mpv`/`ffmpeg` están en el PATH.

## Stack

`yt-dlp` + `mpv` IPC + hilo `worker` + `./run.sh` / `make run`
(modo **dev**). Deploy: `make dist` (PyInstaller onedir; `yt-dlp`
es demasiado grande para Nuitka) según `[PREF-DIST]` en Laura
`docs/preferencias-proyectos-minimos.md`.
