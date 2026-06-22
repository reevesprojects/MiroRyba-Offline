# Editorial Copilot: MiroRyba Swarm Identity Engine

## Problem Statement
Traditional LLM-based agentic simulations (swarms) often suffer from "persona collapse" and homogeneity, failing to represent diverse demographic nuances. This project solves the issue of demographic homogeneity in Czech political simulations by creating a robust data ingestion pipeline that translates raw governmental census and election data into statistically accurate, geographically bounded AI personas. 

This work serves as the foundational data ingestion and persona configuration layer for the broader MiroFish framework (based on the OASIS agentic simulation architecture).

## Scope
**Implemented:**
*   **Data Pipeline (`data_pipeline.py`)**: An automated ETL pipeline that ingests raw Czech Statistical Office (ČSÚ) demographic and electoral datasets, merges them geographically using NUTS codes, and synthesizes accurate regional personas. The pipeline now covers all 14 Czech regions fully without falling back to generalized mock aggregations when schema data is missing.
*   **Swarm Injector (`swarm_injector.py`)**: An asynchronous, Semaphore-throttled dispatch engine that injects the generated personas into a highly strict, localized prompt template and simulates the swarm execution against breaking news articles.
*   **Neo4j Graph Integration (`neo4j_importer.py`)**: Directly integrates the dynamically generated JSON personas as `Entity:Persona` nodes into the live Neo4j knowledge graph backend.

## Execution Guide
The project relies on strict command-line parameters utilizing `argparse`. Ensure you have installed the dependencies via `pip install -r requirements.txt`.

### 1. Build the Persona Registry
Ingests the raw CSU CSVs and builds the demographic JSON registry.
```bash
python data_pipeline.py --data-dir "data/raw" --output-file "data/processed/personas_registry.json" --regions "Ústecký kraj" "Praha" "Jihomoravský kraj"
```

### 2. Dispatch the LLM Swarm
Injects the personas into the prompts and executes the async throttled swarm logic.
```bash
python swarm_injector.py --registry-file "data/processed/personas_registry.json" --output-file "data/processed/swarm_output.json" --max-workers 4 --article "Vláda dnes oznámila novou metodiku pro výpočet energetických dotací."
```

### 3. Integrate with Neo4j Knowledge Graph
Pushes the generated dynamic personas directly into the live Neo4j database as `Entity` nodes.
```bash
python neo4j_importer.py --registry-file "data/processed/personas_registry.json" --neo4j-uri "bolt://localhost:7687" --neo4j-user "neo4j" --neo4j-password "password"
```

## Sample Output
A successful execution of the swarm engine produces a clean, JSON-formatted output containing the persona identifiers, the calculated prompt payload length, and the simulated regional response. A sample file can be found at `data/processed/swarm_output.json`.
