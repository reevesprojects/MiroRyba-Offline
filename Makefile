.PHONY: help setup precompute registry all

help:
	@echo "MiroRyba Swarm Identity Engine - Makefile"
	@echo "----------------------------------------"
	@echo "Available commands:"
	@echo "  make setup      - Install Python dependencies and initialize .env file"
	@echo "  make precompute - Run the demographic ETL script (csu_census -> json)"
	@echo "  make registry   - Build the regional registry mapping"
	@echo "  make all        - Run setup, precompute, and registry sequentially"
	@echo "----------------------------------------"

setup:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "IMPORTANT: Please edit .env to configure your LLM_API_KEY and Neo4j credentials before running the pipeline."; \
	else \
		echo ".env already exists. Skipping creation."; \
	fi

precompute:
	@echo "Precomputing demographic distributions..."
	python precompute_demographics.py --raw-dir "data/raw/csu_census" --output "data/processed/demographic_distributions.json"

registry:
	@echo "Building regional registry..."
	python data_pipeline.py --data-dir "data/raw" --output-file "data/processed/personas_registry.json"

all: setup precompute registry
	@echo "Data pipeline complete! You can now launch MiroFish via Docker or npm run dev."
