.PHONY: install dev test demo retry docker-up

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -e '.[dev]'

dev:
	uvicorn app.main:app --reload

test:
	pytest

demo:
	python scripts/bootstrap_demo.py

retry:
	python scripts/retry_worker.py

docker-up:
	docker compose up --build
