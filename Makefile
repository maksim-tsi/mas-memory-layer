.PHONY: build up down logs test-unit

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test-unit:
	poetry run pytest tests/ -m "not integration"
