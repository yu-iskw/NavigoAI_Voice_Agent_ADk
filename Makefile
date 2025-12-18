.PHONY: setup-python run-server run-client

setup-python:
	uv venv --allow-existing
	uv pip install -r ./server/requirements.txt

run-server:
	@echo "Starting the streaming service on port 8080..."
	cd server && uv run python streaming_service.py

run-client:
	@echo "Starting the client on http://localhost:8000/interface.html"
	cd client && python3 -m http.server 8000

lint:
	pre-commit run --all-files
