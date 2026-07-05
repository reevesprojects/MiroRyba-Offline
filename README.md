# Editorial Copilot: MiroRyba Swarm Identity Engine

## Project Extension Summary

**1. What is the point of this extension?**
Traditional LLM-based agentic simulations (swarms) often suffer from "persona collapse" and demographic homogeneity, failing to represent nuanced societal distributions. This limits their validity in simulating real-world sociological or political discourse. 
This extension solves that problem by building a hierarchical probabilistic pipeline that translates raw governmental census (ČSÚ) and election data into statistically accurate, individualized AI personas for the swarm.

**2. How to run it?**

### Prerequisites

| Tool | Minimum Version | Description |
|------|---------|-------------|
| **Node.js** | 18+ | Frontend runtime (required if running manually) |
| **Python** | 3.11+ | Backend runtime (required if running manually) |
| **Docker** | Latest | Required for Neo4j DB and containerized deployment |
| **Make** | Optional | Recommended for easy pipeline execution |

To make testing easier, a `Makefile` has been provided for local execution.

**A. Preparation (Docker & Neo4j)**
1. Ensure you have Docker and Docker Compose installed on your system.
2. Start the required services (including the Neo4j Graph Database) by running:
   ```bash
   docker compose up -d
   ```
3. Wait a moment for Neo4j to fully initialize on port `7687`.

**B. Configuration (.env & API Keys)**
Run `make setup` to install Python dependencies and automatically generate your `.env` file from `.env.example`. 

You must modify the `.env` file to configure your LLM backend. By default, the project is configured to use the Cerit-SC OpenAI cluster:
- **Base URL:** `https://llm.ai.e-infra.cz/v1`
- **API Key Generation:** Available to all UFAL members after sign-up at [chat.ai.e-infra.cz](https://chat.ai.e-infra.cz/). For step-by-step instructions, see the [Cerit AI API Documentation](https://docs.cerit.io/en/docs/ai-as-a-service/ai-api).
- Insert your generated key into the `LLM_API_KEY` and `OPENAI_API_KEY` variables in your `.env`.

Note: After doing testing in the feat/LLM-judge-eval branch, I determined that qwen3.5-122b was the best model for this task that is available at [chat.ai.e-infra.cz](https://chat.ai.e-infra.cz/)

*Alternative LLM Setups:*
You can easily swap out the model provider. For example, if you want to use Google Gemini or another cloud provider, your `.env` would look like this:
```env
LLM_API_KEY=AIzaSy...[CENSORED]...
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL_NAME=gemini-3.1-flash-lite-preview
```

**C. Execution Pipeline**
1. Run `make all` to execute the data pipeline (this precomputes the demographic distributions and builds the registry). This needs to be done whether you are using Docker or a manual setup.

**2a. Start Services via Docker (Recommended)**
If you haven't already started all services in the preparation step, run:
```bash
docker compose up -d
```

**2b. Start Services Manually (Alternative)**
If you prefer not to use Docker for the backend and frontend, start them separately:
```bash
# Terminal 1
python backend/run.py

# Terminal 2
cd frontend && npm run dev
```

**3. Inject Agents (Both Methods)**
Open `http://localhost:3000` in your browser. The actual graph injection happens dynamically when you launch the swarm simulation in the UI. You will set the exact number of agents you want, and the backend will instantly sample from our precomputed demographic registry and inject them directly into Neo4j.

---

## Key Files Modified in this Branch

This extension modifies the core simulation architecture to replace hallucinated LLM personas with statistically accurate demographic sampling. Here is how the key files connect to this goal:

1. **[`precompute_demographics.py`](./precompute_demographics.py)**
   - Parses raw Czech Statistical Office (ČSÚ) census CSVs to build an $O(1)$ hierarchical sampling JSON tree. This is the mathematical foundation of the demographic simulation.
2. **[`neo4j_importer.py`](./neo4j_importer.py)**
   - The injection script. Instead of running via CLI, this is now triggered by the backend. It takes the generated demographic traits, blends them with Faker names/bios, and injects the resulting `Entity:Person` nodes directly into the live Neo4j knowledge graph.
3. **[`backend/app/services/simulation_runner.py`](./backend/app/services/simulation_runner.py)** & **[`backend/app/services/oasis_profile_generator.py`](./backend/app/services/oasis_profile_generator.py)**
   - The core backend orchestration was modified to intercept the standard "generate random agents" flow. It now delegates agent creation to our demographic `neo4j_importer`, ensuring the swarm uses our realistic Czech profiles.
4. **[`frontend/src/views/Process.vue`](./frontend/src/views/Process.vue)**
   - The frontend UI was updated to allow the user to specify the exact number of demographic agents to sample and inject when initiating the swarm.

---

## Scope

**Implemented:**
* **Precomputed Demographic Tree (`precompute_demographics.py`)**: An ETL script that parses hundreds of megabytes of raw 2021 Czech Statistical Office (ČSÚ) CSVs to build an $O(1)$ hierarchical sampling JSON tree for age, gender, education, religion, and economic activity.
* **Graph Injector (`neo4j_importer.py`)**: A robust, PEP8-compliant script that generates unique individualized citizens. It uses `faker` for identity generation, blends real-world election data with sociological demographic modifiers, and injects the resulting `Entity:Person` nodes directly into the live Neo4j knowledge graph.
* **Data Pipeline (`data_pipeline.py`)**: Synthesizes qualitative regional archetypes.

## Manual Execution Guide (Alternative to Makefile)

If you prefer not to use the `Makefile`, you can run the steps manually:

1. **Precompute Demographic and Election Data**
```bash
python precompute_demographics.py --raw-dir "data/raw/csu_census" --output "data/processed/demographic_distributions.json"
```

2. **Build the Regional Registry**
```bash
python data_pipeline.py --data-dir "data/raw" --output-file "data/processed/personas_registry.json"
```

3. **Launch MiroFish Backend and Frontend**
Ensure your Neo4j database is running and your `.env` is configured. Then launch the Flask backend (`python backend/run.py`) and Vue frontend (`npm run dev`).
*(Graph injection happens automatically via the UI at http://localhost:3000)*

## Sample Output
A successful graph injection produces mathematically accurate persona JSONs. A sample representation can be found in `data/processed/election_2025_distributions.json` or within the Neo4j database as:

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
