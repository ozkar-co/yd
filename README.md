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

## Sesión YouTube (403 Forbidden)

yt-dlp **no inicia sesión** con usuario/clave. Usa cookies de un
navegador donde ya estés logueado.

**Opción A — navegador en el AIO** (recomendado si XFCE tiene Firefox):

```bash
# una vez logueado en youtube.com en Firefox del AIO
export YD_COOKIES_FROM_BROWSER=firefox
./run.sh dl 'URL'
```

Chrome/Chromium: `YD_COOKIES_FROM_BROWSER=chromium` (o `chrome`).
Perfil concreto: `firefox:default-release`.

**Opción B — archivo `cookies.txt`**

1. En el PC donde tengas sesión YT, extensión
   *Get cookies.txt LOCALLY* → exportar para youtube.com.
2. Copiar a `~/data/media/cookies.txt` en el AIO
   (se usa solo si existe; no va a git).
3. O: `YD_COOKIES=/ruta/cookies.txt ./run.sh dl 'URL'`

`cookies.txt` es secreto de sesión: no lo subas al repo.

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
