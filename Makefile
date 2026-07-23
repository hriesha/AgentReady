VENV ?= .venv
PY = $(VENV)/bin/python

.PHONY: dev build test demo-fixture

dev:
	trap 'kill 0' INT TERM; \
	(cd api && ../$(VENV)/bin/uvicorn app.main:app --reload --port 8000) & \
	(cd web && npm run dev) & \
	wait

build:
	cd web && npm run build
	$(PY) -m compileall -q api/app

test:
	cd api && ../$(VENV)/bin/python -m pytest -q

demo-fixture:
	cd api && ../$(VENV)/bin/python scripts/build_demo_fixture.py
