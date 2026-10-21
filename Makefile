# AgriMine developer commands.   make help
PY ?= python
NPM ?= npm --prefix web

.PHONY: help install api dev build release contract test test-py test-web test-e2e lab

help:
	@echo "make install    install Python and Node dependencies"
	@echo "make api        run the API and the built site on http://127.0.0.1:8000 (and the lab on :8501)"
	@echo "make dev        API on :8000 and the Next dev server on :3000 (hot reload)"
	@echo "make build      build the web app into web/out (served by 'make api')"
	@echo "make release    build the site and pack dist/agrimine-release.zip (Python only to run: no Node needed)"
	@echo "make contract   regenerate api/openapi.json and web/lib/api/schema.d.ts"
	@echo "make test       every test: Python, web unit, browser (needs 'make build' first)"
	@echo "make lab        only the Streamlit technical lab (make api already starts it)"

install:
	$(PY) -m pip install -r requirements-test.txt
	$(NPM) install

api:
	$(PY) -m api

dev:
	AGRIMINE_DEV=1 $(PY) -m api & NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 $(NPM) run dev; kill %1

build:
	$(NPM) run build

release: build
	$(PY) tools/make_release.py

contract:
	$(PY) -m api.export
	$(NPM) run gen:api

test: test-py test-web test-e2e

test-py:
	$(PY) -m pytest -q tests

test-web:
	$(NPM) run typecheck
	$(NPM) run lint
	$(NPM) test

test-e2e:
	PYTHON=$(PY) $(NPM) run test:visual

lab:
	cd teachers-lab && streamlit run app.py
