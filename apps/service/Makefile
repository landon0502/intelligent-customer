APP_NAME=service

run:
	uv run python main.py

dev:
	uv run python main.py

build:
	docker build -t service .

start:
	docker run -d --name service -p 8001:8001 --env-file .env service

clean:
	docker rm -f service 2>/dev/null || true

test:
	python -m pytest tests/ -v

fmt:
	ruff format app/ tests/

tidy:
	ruff check app/ tests/ --fix

install:
	pip install -r requirements.txt

seed:
	python -m app.db.seed
