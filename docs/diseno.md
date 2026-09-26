---
title: yd — diseño MVP
date: 2026-09-26
tags: [yd, media, diseno]
status: active
---

# yd — diseño

Pivote: de downloader interactivo a **CLI de estación
multimedia** (descarga + cola + mpv). Mismo comando en local o
por SSH.

Norte de producto (Laura):
`Laura/projects/personal/topics/estacion-multimedia.md`
`[PER-MEDIA]`.

## MVP

- Biblioteca: `~/data/media` (`YD_MEDIA_ROOT` para override).
- Calidad: ≤720p (`yt-dlp`).
- Solo URLs (sin import auto de playlists).
- Solo reproducción local (nunca stream).
- Control: `dl`, `add`, `play`, `next`, `stop`, `pause`,
  `status`, `list`, `mv`, `init`.
- Clasificación: carpetas a mano.

## Layout

```
$YD_MEDIA_ROOT/
  inbox/
  musica/ entrevistas/ documentales/
  videojuegos/ noticias/ otros/
  queue.json
  mpv.sock
```

## Stack

| Pieza | Elección |
|-------|----------|
| Entrypoint | `main.py` / `./run.sh` |
| Descarga | `yt-dlp` |
| Player | `mpv` + IPC Unix socket |
| Cola | `queue.json` |

El script interactivo `script.py` queda como legado (búsqueda);
el camino nuevo es subcomandos.

## SSH → pantalla

Si `yd play` corre por SSH, necesita `DISPLAY` (y a menudo
`XAUTHORITY`) de la sesión gráfica del usuario. Fail-fast si
mpv no puede abrir ventana.

## Sesión YouTube

No hay login interactivo. Cookies:

| Variable / archivo | Uso |
|--------------------|-----|
| `YD_COOKIES_FROM_BROWSER` | `firefox`, `chromium`, … |
| `YD_COOKIES` | path a `cookies.txt` |
| `$YD_MEDIA_ROOT/cookies.txt` | auto si existe |
