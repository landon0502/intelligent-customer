.PHONY: bootstrap dev build lint format typecheck

bootstrap:
	pnpm install
	cd apps/service && uv sync

dev:
	turbo dev

build:
	turbo build

lint:
	turbo lint

format:
	turbo format

typecheck:
	turbo typecheck
