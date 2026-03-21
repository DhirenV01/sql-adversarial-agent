install:
	pip install -r requirements.txt

test:
	PYTHONPATH=. pytest tests/ -v

run:
	uvicorn api.main:app --reload --port 8000

.PHONY: install test run
