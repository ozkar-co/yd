# yd

CLI: descarga YouTube (≤720p) + cola + reproducción local con
mpv. Sirve en el mismo PC o por SSH.

```bash
./run.sh init
./run.sh dl 'https://www.youtube.com/watch?v=…'
./run.sh play
./run.sh list
```

Diseño: [docs/diseno.md](docs/diseno.md).

## Requisitos

- Python 3.10+
- `ffmpeg`, `mpv`, `yt-dlp` (vía pip en `.venv`)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh init
```

Biblioteca por defecto: `~/data/media` (`YD_MEDIA_ROOT`).

## Comandos

| Comando | Efecto |
|---------|--------|
| `init` | Crea carpetas + `queue.json` |
| `dl <url>` | Descarga a `inbox/` y encola |
| `add <path\|url>` | Encola path o descarga URL |
| `play` | Arranca mpv / cola |
| `next` `stop` `pause` | Control |
| `status` `list` | Estado y cola |
| `mv <n\|file> <cat>` | Mueve a categoría |
| `search` | Legado: búsqueda interactiva |

## Legado

`script.py` / `yd search`: busca 9 resultados y descarga al cwd.
Preferir `dl` + biblioteca bajo `~/data/media`.
