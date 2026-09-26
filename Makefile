.PHONY: setup run clean dist

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# Modo dev / legado ([PREF-RUN])
run:
	./run.sh

# Borra venv, caches y artefactos de build (no ./media)
clean:
	rm -rf .venv __pycache__ .pytest_cache dist build main.build main.dist main.onefile-build
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete

# Deploy: Nuitka standalone onedir → dist/yd/ ([PREF-DIST])
# Requiere gcc/ccache útiles; compilar en la máquina de desarrollo.
dist: setup
	.venv/bin/pip install -q 'nuitka>=2.0' ordered-set zstandard
	.venv/bin/python -m nuitka \
		--standalone \
		--follow-imports \
		--include-package=yt_dlp \
		--output-dir=dist \
		--output-filename=yd \
		--assume-yes-for-downloads \
		main.py
	@echo "Bundle: dist/main.dist/  (ejecutar: ./yd  desde esa carpeta)"
	@echo "Copiar esa carpeta al host; allá: mpv + ffmpeg del sistema."
