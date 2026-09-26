.PHONY: setup run clean dist

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# Modo dev / legado ([PREF-RUN])
run:
	./run.sh

# Borra venv, caches y artefactos de build (no ./media)
clean:
	rm -rf .venv __pycache__ .pytest_cache dist build *.spec main.build main.dist main.onefile-build
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete

# Deploy: PyInstaller onedir → dist/ con ./yd y ./media ([PREF-DIST]).
# yt-dlp es Python puro enorme: se copia, no se compila a C.
dist: setup
	.venv/bin/pip install -q 'pyinstaller>=6'
	rm -rf build/pyi build/pyi-work dist
	.venv/bin/python -m PyInstaller --noconfirm --clean --onedir \
		--name yd \
		--contents-directory yd.pkg \
		--distpath build/pyi \
		--workpath build/pyi-work \
		--specpath build/pyi \
		--collect-all yt_dlp \
		main.py
	mkdir -p dist
	cp -a build/pyi/yd/yd dist/yd
	cp -a build/pyi/yd/yd.pkg dist/yd.pkg
	chmod +x dist/yd
	printf '%s\n' \
	  'Carpeta portable. Ejecutar ./yd desde aqui.' \
	  'Los videos quedan en ./media (esta misma carpeta).' \
	  'Otra ruta: YD_MEDIA_ROOT=/otra/ruta ./yd' \
	  'En el host hacen falta mpv y ffmpeg del sistema.' \
	  > dist/LEEME.txt
	@echo "Bundle: dist/  (./yd ; datos en ./media, o YD_MEDIA_ROOT)"
