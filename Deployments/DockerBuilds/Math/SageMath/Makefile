.PHONY: jupyter jupyter-logs down cli python

## Start Jupyter in background and print the URL
jupyter:
	docker compose up -d jupyter
	@echo ""
	@echo "  ✓ SageMath Jupyter is running → http://localhost:8889"
	@echo "    Get the authentication token with: docker compose logs jupyter"
	@echo ""

## Tail Jupyter logs
jupyter-logs:
	docker compose logs -f jupyter

## Interactive Sage REPL
cli:
	docker compose run --rm cli

## Interactive Python3 REPL (full SageMath env available via 'from sage.all import *')
python:
	docker compose run --rm python

## Stop all services
down:
	docker compose down
