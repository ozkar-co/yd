# yd

REPL: descarga YouTube (≤720p) + cola + mpv. Biblioteca en
`./media` (junto al proyecto). Local o por SSH.

```bash
make setup
make run
```

```
yd> search queen of kings
yd> queue 1
yd> list
yd> mv 1 musica
yd> play 1
yd> stop
yd> exit
```

Diseño: [docs/diseno.md](docs/diseno.md).

## Requisitos

- Python 3.10+, `ffmpeg`, `mpv`
- Cookies si YouTube da 403 (ver abajo)

## Setup

```bash
make setup          # .venv + deps
make run            # entra al REPL
make nukita         # borra .venv / caches (no ./media)
```

Override raíz: `YD_MEDIA_ROOT=/otra/ruta make run`.

## Comandos REPL

| Comando | Efecto |
|---------|--------|
| `list [cat]` | IDs únicos; o una categoría |
| `play [n]` | cola lista, o ítem n |
| `queue` | muestra cola |
| `queue <n\|cat>` | encola ítem o categoría |
| `search <q>` | YouTube → `queue n` encola URL (dl async) |
| `mv <n> <cat>` | mueve; **crea** cat si no existe |
| `cc [es\|en]` | subtítulos sesión; sin arg = off |
| `next` `pause` | control |
| `stop` | **cierra** mpv |
| `status` | mpv + cola |
| `help` `exit` | |

Descargas: audio **es** si existe; subs **manuales** `es`+`en`
(no auto-generados) junto al vídeo. `mv` mueve también los
`.vtt`/`.srt` hermanos.

Tras `search`, los números de `queue n` son resultados de
búsqueda. Tras `list`, son IDs de biblioteca.

La cola descarga URLs en un hilo; cuando terminan, entran a
`inbox/` y se pueden `play` / append a mpv si ya está sonando.

## Sesión YouTube (403)

```bash
export YD_COOKIES_FROM_BROWSER=firefox
make run
```

O `media/cookies.txt` (no va a git).
