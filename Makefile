.PHONY: build up down logs test-unit healthcheck

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

healthcheck:
	bash scripts/healthcheck_v2.sh
