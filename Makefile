.PHONY: setup run nukita

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	./run.sh

# Limpia entorno de build (no borra ./media)
nukita:
	rm -rf .venv __pycache__ .pytest_cache
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete
