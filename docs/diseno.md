---
title: yd — diseño
date: 2026-09-26
tags: [yd, media, diseno]
status: active
---

# yd — diseño

CLI → **REPL** de estación multimedia. Repo portable: biblioteca
por defecto `./media` (cwd del proceso).

Laura: `[PER-MEDIA]`
`estacion-multimedia.md`.

## Modelo

| Concepto | Regla |
|----------|-------|
| Raíz | `./media` o `YD_MEDIA_ROOT` |
| Categorías | subdirs creados con `mv n cat` (no `init`) |
| IDs | asignados al hacer `list` (sesión) |
| Cola | archivos + URLs; worker descarga async → `inbox/` |
| `stop` | `quit` de mpv (proceso cerrado) |
| Focus | `list`→lib; `search`→search (`queue n`) |
| Audio | preferir pista `es` si yt-dlp la ofrece |
| Subs | solo manuales `es`+`en` (no ASR); `cc [es\|en]` en sesión |

## Comandos

`list`, `play`, `queue`, `search`, `mv`, `next`, `pause`,
`stop`, `status`, `help`, `exit`.

## Stack

`yt-dlp` + `mpv` IPC + hilo `worker` + `./run.sh` / `make run`
(modo **dev**). Deploy: `make dist` (Nuitka onedir) según
`[PREF-DIST]` en Laura `docs/preferencias-proyectos-minimos.md`.
