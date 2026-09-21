SHELL := /bin/sh
.DEFAULT_GOAL := help
PYTHON ?= python3.12
VENV_PY := .venv/bin/python
COMPOSE := docker compose --env-file .env -f infra/docker/compose.yaml

.PHONY: help doctor bootstrap contracts contracts-check coverage format format-check lint typecheck test build build-python proto-check verify-foundation verify verify-containers verify-native verify-agent verify-native-container verify-agent-container native-configure native-build dev-api dev-dashboard configure-local infra-check infra-up infra-down stack-up browser-install test-e2e

help:
	@echo "JOCKY foundation: bootstrap | doctor | dev-api | dev-dashboard | contracts | coverage"
	@echo "Checks: verify-foundation | verify (all host tools) | verify-containers | test-e2e"
	@echo "Native/Rust: verify-native-container | verify-agent-container | native-build"
	@echo "Infrastructure: configure-local | infra-check | infra-up | stack-up | infra-down"

doctor:
	$(PYTHON) scripts/doctor.py

bootstrap:
	UV_CACHE_DIR=.cache/uv uv sync --all-packages --frozen --python $(PYTHON)
	npm ci --cache .cache/npm --no-fund

contracts:
	$(VENV_PY) scripts/generate_contracts.py
	npm run contracts:types

contracts-check:
	$(VENV_PY) scripts/generate_contracts.py --check
	node scripts/generate-types.mjs --check
	$(VENV_PY) scripts/generate_coverage.py --check

coverage:
	$(VENV_PY) scripts/generate_coverage.py

format:
	.venv/bin/ruff check . --fix
	.venv/bin/ruff format .
	npm run format

format-check:
	.venv/bin/ruff format --check .
	npm run format:check

lint:
	.venv/bin/ruff check .
	npm run lint

typecheck:
	.venv/bin/mypy
	npm run typecheck

test:
	$(VENV_PY) -m pytest

build:
	npm run build

build-python:
	UV_CACHE_DIR=.cache/uv uv build --all-packages --out-dir dist/python

proto-check:
	$(VENV_PY) scripts/generate_agent_python.py --check
	mkdir -p build/proto
	$(VENV_PY) -m grpc_tools.protoc -I proto --descriptor_set_out=build/proto/jocky.pb --include_imports --python_out=build/proto --grpc_python_out=build/proto proto/jocky/v1/agent.proto

verify-foundation: contracts-check format-check lint typecheck test proto-check build-python build

native-configure:
	cmake -S . -B build/native -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON $(if $(LLVM_DIR),-DLLVM_DIR="$(LLVM_DIR)")

native-build: native-configure
	cmake --build build/native --parallel 2

verify-native: native-build
	ctest --test-dir build/native --output-on-failure
	build/native/native/compiler/jockyc --self-test
	$(PYTHON) scripts/format_native.py --check

verify-agent:
	cargo fmt --all -- --check
	cargo build --locked --workspace
	cargo test --locked --workspace
	cargo clippy --locked --workspace --all-targets -- -D warnings
	cargo run --locked -p jocky-agent -- doctor

verify-native-container:
	docker build -f infra/docker/native.Dockerfile -t jocky-native:foundation .

verify-agent-container:
	docker build -f infra/docker/agent.Dockerfile -t jocky-agent:foundation .

verify: verify-foundation verify-native verify-agent infra-check test-e2e

verify-containers: verify-foundation verify-native-container verify-agent-container infra-check test-e2e

dev-api:
	.venv/bin/uvicorn jocky_control_plane.app:app --host 127.0.0.1 --port 8000 --log-level info

dev-dashboard:
	JOCKY_API_URL=http://127.0.0.1:8000 npm run dev

configure-local:
	$(PYTHON) scripts/configure_local.py

infra-check:
	$(COMPOSE) --profile app --profile monitoring --profile relay config --quiet

infra-up:
	$(COMPOSE) up -d --wait postgres redis minio

stack-up:
	$(COMPOSE) --profile app up -d --build --wait

infra-down:
	$(COMPOSE) --profile app --profile monitoring --profile relay down

browser-install:
	PLAYWRIGHT_BROWSERS_PATH=.cache/playwright npx playwright install chromium

test-e2e:
	PLAYWRIGHT_BROWSERS_PATH=.cache/playwright npm run test:e2e

.PHONY: demo-up demo-prepare demo-down
demo-up: configure-local
	docker compose --env-file .env -f infra/docker/prototype.compose.yaml up -d --build --wait

demo-prepare:
	$(VENV_PY) scripts/prepare_demo.py

demo-down:
	docker compose --env-file .env -f infra/docker/prototype.compose.yaml down
