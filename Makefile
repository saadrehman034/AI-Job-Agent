.PHONY: install dev test lint clean demo

# ─── Setup ───────────────────────────────────────────────────────────────────

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	playwright install chromium
	cp .env.example .env
	mkdir -p data/applications data/faiss_index
	@echo "✓ Install complete. Edit .env and add your ANTHROPIC_API_KEY"

# ─── Running ─────────────────────────────────────────────────────────────────

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run ui/streamlit_app.py

dev:
	@echo "Starting API + UI in parallel..."
	uvicorn app.main:app --reload --port 8000 &
	streamlit run ui/streamlit_app.py

demo:
	python cli.py --demo --show-resume

# ─── Testing ─────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v -k "not asyncio" --ignore=tests/test_integration.py

# ─── Code quality ────────────────────────────────────────────────────────────

lint:
	python -m py_compile app/**/*.py ui/*.py cli.py
	@echo "✓ Syntax check passed"

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete 2>/dev/null; true
	rm -rf .pytest_cache htmlcov .coverage
	@echo "✓ Cleaned"

clean-data:
	rm -f data/applications/*.docx data/applications/*.pdf
	rm -f data/faiss_index/*.index data/faiss_index/*.pkl
	rm -f data/*.db
	@echo "✓ Data cleaned"

# ─── Help ────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "AI Job Application Agent — Available Commands"
	@echo "──────────────────────────────────────────────"
	@echo "  make install      Install dependencies + set up .env"
	@echo "  make api          Start FastAPI backend (port 8000)"
	@echo "  make ui           Start Streamlit frontend"
	@echo "  make demo         Run CLI demo with sample data"
	@echo "  make test         Run full test suite"
	@echo "  make test-fast    Run fast (non-async) tests only"
	@echo "  make lint         Syntax check all Python files"
	@echo "  make clean        Remove __pycache__ and build artifacts"
	@echo "  make clean-data   Remove generated documents and DB"
	@echo ""
