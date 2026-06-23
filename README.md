# Editorial Copilot: MiroRyba Swarm Identity Engine

## Problem Statement
Traditional LLM-based agentic simulations (swarms) often suffer from "persona collapse" and demographic homogeneity, failing to represent nuanced societal distributions. This limits their validity in simulating real-world sociological or political discourse. 
This project solves the issue of demographic homogeneity in Czech political simulations by building a hierarchical probabilistic pipeline that translates raw governmental census and election data into statistically accurate, individualized AI personas. 

Reference paper: *Generative Agents: Interactive Simulacra of Human Behavior* (Park et al., 2023) which highlights the necessity of robustly initialized agent memories and demographic traits to produce believable emergent behavior in multi-agent environments.

## Scope

**Implemented:**
* **Precomputed Demographic Tree (`precompute_demographics.py`)**: An ETL script that parses hundreds of megabytes of raw 2021 Czech Statistical Office (ČSÚ) CSVs to build an $O(1)$ hierarchical sampling JSON tree for age, gender, education, religion, and economic activity.
* **Graph Injector (`neo4j_importer.py`)**: A robust, PEP8-compliant script that generates unique individualized citizens. It uses `faker` for identity generation, blends real-world election data with sociological demographic modifiers, and injects the resulting `Entity:Person` nodes directly into the live Neo4j knowledge graph.
* **Data Pipeline (`data_pipeline.py`)**: Synthesizes qualitative regional archetypes.

**Left for Future:**
* Creating dynamic Neo4j social network edges (`[:KNOWS]`, `[:WORKS_WITH]`) based on shared demographics or region.
* Expanding the political ideology sampler by ingesting historical election timelines.
* Implementing a real-time scraping module for daily ČTK news to feed the simulation.

## Execution Guide

The project relies on strict command-line parameters and standard Python structures. Ensure dependencies are installed via `pip install -r requirements.txt` (or via the provided `pyproject.toml`).

### 1. Precompute Demographic and Election Data
First, generate the probability distributions from the raw data.
```bash
python precompute_demographics.py --raw-dir "data/raw/csu_census" --output "data/processed/demographic_distributions.json"
```

### 2. Build the Regional Registry
Synthesizes the qualitative geographic mapping.
```bash
python data_pipeline.py --data-dir "data/raw" --output-file "data/processed/personas_registry.json"
```

### 3. Integrate with Neo4j Knowledge Graph
Samples the exact statistical attributes and injects unique individuals into the graph.
```bash
python neo4j_importer.py --registry-file "data/processed/personas_registry.json" --neo4j-uri "bolt://localhost:7687" --neo4j-user "neo4j" --neo4j-password "password" --num-agents 100
```

## Sample Output
A successful graph injection produces mathematically accurate persona JSONs. A sample representation can be found in `data/processed/election_2025_distributions.json` (showing the parsed XML) or within the Neo4j database as:

```json
{
  "realname": "Zdenka Kopecká",
  "username": "lmasek882",
  "region_typ": "Moravskoslezský kraj",
  "age": 23,
  "gender": "female",
  "education": "úplné střední všeobecné vzdělání",
  "politicka_preference": "Česká pirátská strana",
  "hlavni_zajem": "Kempování, Domácí mazlíčci",
  "bio": "Obyvatel regionu Moravskoslezský kraj. Volí: Česká pirátská strana..."
}
```
