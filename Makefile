APP=app.main:app

.PHONY: run test lint type benchmark demo-artifact

run:
	uvicorn $(APP) --reload

test:
	pytest -q

lint:
	python -m py_compile app/main.py

type:
	python -c "import app.main"

benchmark:
	python scripts/run_benchmarks.py

demo-artifact:
	python scripts/generate_demo_artifact.py
