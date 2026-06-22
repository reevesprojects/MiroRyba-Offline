"""
MiroFish / MiroRyba Combined LLM Benchmarking and Swarm Evaluation Utility
Contains:
1. Technical benchmarks (JSON validation, speed)
2. Czech journalism benchmarks (NER, Czech persona generation)
3. Swarm quality evaluation (LLM-as-a-Judge for simulated conversation threads)
"""

import os
import sys
import time
import json
import argparse
from typing import Dict, Any, List

# Add project path to resolve imports if run standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI


# Simple zero-dependency .env loader
def parse_env(env_path: str) -> Dict[str, str]:
    if not os.path.exists(env_path):
        return {}
    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                val = val.strip().strip('"').strip("'")
                env_vars[key.strip()] = val
    return env_vars


# Load config
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
env_config = parse_env(env_path)

LLM_API_KEY = os.environ.get('LLM_API_KEY') or env_config.get('LLM_API_KEY') or 'temp-key'
LLM_BASE_URL = os.environ.get('LLM_BASE_URL') or env_config.get('LLM_BASE_URL') or 'http://localhost:11434/v1'
LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME') or env_config.get('LLM_MODEL_NAME') or 'gemma2:9b'


WORKLOADS = {
    # -------------------------------------------------------------
    # PART 1: Technical & JSON Mechanics
    # -------------------------------------------------------------
    "tech_ner": {
        "category": "Technical Mechanics",
        "name": "English NER Extraction (JSON)",
        "messages": [
            {
                "role": "system",
                "content": "You are a Named Entity Recognition system. Extract entities. Return ONLY valid JSON with 'entities' list containing objects with 'name' and 'type'."
            },
            {
                "role": "user",
                "content": "Extract people and locations from: Elon Musk announced that Tesla will build a new factory in Berlin."
            }
        ],
        "expected_keys": ["entities"],
        "temp": 0.1
    },
    "tech_persona": {
        "category": "Technical Mechanics",
        "name": "English Persona Generation (JSON)",
        "messages": [
            {
                "role": "system",
                "content": "Generate a user profile. Return ONLY valid JSON with keys: name, age, bio, bias."
            },
            {
                "role": "user",
                "content": "Generate a profile for a 30-year-old software engineer who is enthusiastic about open-source projects."
            }
        ],
        "expected_keys": ["name", "age", "bio", "bias"],
        "temp": 0.7
    },

    # -------------------------------------------------------------
    # PART 2: Czech Journalism & Local Language Processing
    # -------------------------------------------------------------
    "cz_ner": {
        "category": "Czech Domain",
        "name": "Czech NER & Relation Extraction (JSON)",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Jsi pokročilý systém pro analýzu textu v češtině. Extrahuj entity (Osoba, Organizace, Místo) "
                    "a relace (vztahy). Odpověz POUZE ve formátu JSON s klíči 'entities' a 'relations'. "
                    "Relace musí obsahovat 'source', 'target', 'type' a 'fact' (popis vztahu v češtině)."
                )
            },
            {
                "role": "user",
                "content": (
                    "Extrahuj entity a vztahy z textu:\n\n"
                    "Prezident Petr Pavel včera navštívil Ostravu, kde se setkal s primátorem Janem Dohnalem. "
                    "Diskutovali o útlumu těžby uhlí v Moravskoslezském kraji a dopadech na zaměstnanost."
                )
            }
        ],
        "expected_keys": ["entities", "relations"],
        "temp": 0.1
    },
    "cz_persona_post": {
        "category": "Czech Domain",
        "name": "Czech Demographic Post Generation (Text)",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Jsi simulovaný český občan na sociální síti. Napiš krátký komentář (max 300 znaků) v češtině "
                    "reagující na zadanou zprávu. Tvá reakce musí přesně odpovídat tvému profilu a socioekonomickému zázemí."
                )
            },
            {
                "role": "user",
                "content": (
                    "Profil: Jaroslav, 58 let, bývalý horník z Karviné, obává se zdražování energií a ztráty práce v regionu.\n"
                    "Zpráva: Vláda schválila zrychlený plán na uzavření všech uhelných elektráren do roku 2030."
                )
            }
        ],
        "expected_keys": [],
        "temp": 0.7
    }
}


def evaluate_simulation_quality(client: OpenAI, model_name: str) -> Dict[str, Any]:
    """
    Simulates a mini 2-turn conversation thread in Czech between two contrasting personas
    reacting to a Czech news article. Then uses the model (or LLM Judge) to evaluate it.
    """
    print("\n" + "=" * 60)
    print("RUNNING SWARM SIMULATION QUALITY EVALUATION (Czech Thread)")
    print("=" * 60)

    article = (
        "Česká vláda včera oznámila plány na zavedení dodatečné spotřební daně na slazené nápoje. "
        "Podle ministra zdravotnictví to pomůže bojovat s obezitou a přinese 3 miliardy korun ročně do rozpočtu. "
        "Opozice a potravinářská komora plán ostře kritizují, varují před zdražením pro spotřebitele."
    )

    persona_a = {
        "name": "Tomáš (Praha)",
        "role": "28letý liberální IT specialista z Prahy, podporuje zdravý životní styl, ekologii a vládní reformy."
    }
    persona_b = {
        "name": "Marie (Ostrava)",
        "role": "54letá prodavačka z Ostravy, samoživitelka, každé zdražení potravin výrazně zatěžuje její rodinný rozpočet."
    }

    try:
        # Turn 1: Tomáš posts about the article
        prompt_tomas = f"Zpráva:\n{article}\n\nProfil: {persona_a['role']}\n\nNapiš krátký příspěvek na sociální síť reagující na tuto zprávu."
        resp_tomas = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt_tomas}],
            temperature=0.7,
            max_tokens=300
        ).choices[0].message.content.strip()
        print(f"\n[Post by {persona_a['name']}]:\n  \"{resp_tomas}\"")

        # Turn 2: Marie replies to Tomáš's post
        prompt_marie = (
            f"Původní zpráva:\n{article}\n\n"
            f"Příspěvek od uživatele {persona_a['name']}:\n\"{resp_tomas}\"\n\n"
            f"Tvůj profil: {persona_b['role']}\n\n"
            f"Napiš krátkou, přímou reakci (odpověď) na příspěvek uživatele {persona_a['name']}. Reaguj v češtině, zachovej svůj tón."
        )
        resp_marie = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt_marie}],
            temperature=0.7,
            max_tokens=300
        ).choices[0].message.content.strip()
        print(f"\n[Reply by {persona_b['name']}]:\n  \"{resp_marie}\"")

        # LLM-as-a-Judge evaluation prompt
        judge_prompt = f"""You are an expert evaluator of social media simulation swarms.
Evaluate the following generated Czech conversation thread based on a news article.

ARTICLE:
{article}

THREAD:
1. {persona_a['name']} ({persona_a['role']}):
   "{resp_tomas}"
2. {persona_b['name']} ({persona_b['role']}):
   "{resp_marie}"

Evaluate the thread on the following three criteria, giving a score from 1 to 5 for each, along with a 1-sentence justification.

CRITERIA:
1. Language Naturalness (Czech): Is the Czech language correct, colloquial where appropriate, and free of literal translation artifacts?
2. Persona Consistency: Do both agents stay fully in character matching their defined profiles and socio-economic biases?
3. Interactive Coherence: Does Marie's reply directly and logically address Tomáš's arguments?

Return ONLY valid JSON in this format:
{{
  "scores": {{
    "language_naturalness": 5,
    "persona_consistency": 5,
    "interactive_coherence": 5
  }},
  "justifications": {{
    "language_naturalness": "...",
    "persona_consistency": "...",
    "interactive_coherence": "..."
  }}
}}"""

        # Call judge (running on the same endpoint/model for ease of test, 
        # but user can configure another model if they wish)
        judge_response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0.1,
            max_tokens=1000
        ).choices[0].message.content.strip()

        # Parse evaluation
        cleaned_judge = judge_response
        if cleaned_judge.startswith("```"):
            cleaned_judge = "\n".join(cleaned_judge.split("\n")[1:-1])
        evaluation = json.loads(cleaned_judge)
        
        print("\n--- LLM Judge Scores ---")
        print(f"  Czech Language Naturalness: {evaluation['scores']['language_naturalness']}/5")
        print(f"  Persona Consistency:        {evaluation['scores']['persona_consistency']}/5")
        print(f"  Interactive Coherence:      {evaluation['scores']['interactive_coherence']}/5")
        print("\nJustifications:")
        for key, text in evaluation["justifications"].items():
            print(f"  - {key}: {text}")
            
        evaluation["thread"] = {
            "post": resp_tomas,
            "reply": resp_marie
        }
        evaluation["success"] = True
        return evaluation

    except Exception as e:
        print(f"\n[ERROR] Swarm evaluation failed: {e}")
        return {"success": False, "error": str(e)}


def run_benchmark(runs: int = 1):
    print("=" * 60)
    print("Combined MiroRyba LLM Benchmark & Swarm Evaluator")
    print(f"Endpoint:  {LLM_BASE_URL}")
    print(f"Model:     {LLM_MODEL_NAME}")
    print("=" * 60)

    client = OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        timeout=60.0
    )

    results = []

    for key, workload in WORKLOADS.items():
        print(f"\n[{workload['category']}] Running: {workload['name']}...")
        
        workload_runs = []
        for run_idx in range(runs):
            t0 = time.time()
            error = None
            json_valid = "N/A"
            prompt_tokens = 0
            completion_tokens = 0
            response_content = ""

            try:
                response = client.chat.completions.create(
                    model=LLM_MODEL_NAME,
                    messages=workload["messages"],
                    temperature=workload["temp"],
                    max_tokens=1000,
                )
                
                elapsed = time.time() - t0
                response_content = response.choices[0].message.content.strip()

                if response.usage:
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                else:
                    prompt_tokens = len(str(workload["messages"])) // 4
                    completion_tokens = len(response_content) // 4

                if workload["expected_keys"]:
                    try:
                        cleaned = response_content
                        if cleaned.startswith("```"):
                            cleaned = "\n".join(cleaned.split("\n")[1:-1])
                        parsed = json.loads(cleaned)
                        
                        missing_keys = [k for k in workload["expected_keys"] if k not in parsed]
                        json_valid = f"Missing: {missing_keys}" if missing_keys else "PASS"
                    except json.JSONDecodeError:
                        json_valid = "FAIL (Malformed)"

            except Exception as e:
                elapsed = time.time() - t0
                error = str(e)

            if not error:
                tps = completion_tokens / elapsed if elapsed > 0 else 0
                print(f"  Run {run_idx+1}: {elapsed:.2f}s | {tps:.1f} t/s | JSON: {json_valid}")
                workload_runs.append({
                    "elapsed": elapsed,
                    "tokens_per_sec": tps,
                    "json_valid": json_valid,
                    "success": True
                })
            else:
                print(f"  Run {run_idx+1}: [ERROR] {error}")
                workload_runs.append({
                    "elapsed": elapsed,
                    "tokens_per_sec": 0,
                    "json_valid": "FAIL",
                    "success": False
                })

        successes = [r for r in workload_runs if r["success"]]
        if successes:
            avg_time = sum(r["elapsed"] for r in successes) / len(successes)
            avg_tps = sum(r["tokens_per_sec"] for r in successes) / len(successes)
            pass_rate = sum(1 for r in successes if r["json_valid"] == "PASS") / len(successes) if workload["expected_keys"] else "N/A"
            
            results.append({
                "category": workload["category"],
                "workload_name": workload["name"],
                "avg_time": f"{avg_time:.2f}s",
                "avg_tps": f"{avg_tps:.1f}",
                "json_pass": f"{pass_rate * 100:.0f}%" if isinstance(pass_rate, float) else "N/A",
                "status": "OK"
            })
        else:
            results.append({
                "category": workload["category"],
                "workload_name": workload["name"],
                "avg_time": "0.00s",
                "avg_tps": "0.0",
                "json_pass": "0%",
                "status": "FAILED"
            })

    # Swarm Quality Evaluation
    swarm_eval = evaluate_simulation_quality(client, LLM_MODEL_NAME)

    # Printing unified report
    print("\n" + "=" * 80)
    print("UNIFIED BENCHMARK & EVALUATION SUMMARY REPORT")
    print("=" * 80)
    print(f"Endpoint: {LLM_BASE_URL}")
    print(f"Model:    {LLM_MODEL_NAME}\n")
    
    print(f"{'Category':<20} | {'Workload Name':<38} | {'Latency':<8} | {'Speed':<8} | {'JSON Pass'}")
    print("-" * 87)
    for res in results:
        print(f"{res['category']:<20} | {res['workload_name']:<38} | {res['avg_time']:<8} | {res['avg_tps']:<8} | {res['json_pass']}")
        
    if swarm_eval.get("success"):
        print("-" * 87)
        print("SWARM QUALITY SCORES (LLM-AS-A-JUDGE):")
        print(f"  - Czech Language Naturalness: {swarm_eval['scores']['language_naturalness']}/5")
        print(f"  - Persona Consistency:        {swarm_eval['scores']['persona_consistency']}/5")
        print(f"  - Interactive Coherence:      {swarm_eval['scores']['interactive_coherence']}/5")
    else:
        print("-" * 87)
        print("SWARM QUALITY SCORES: FAILED TO EVALUATE")
    print("=" * 80)

    # Save details
    safe_model_name = LLM_MODEL_NAME.replace(':', '_').replace('/', '_')
    benchmark_file = os.path.join(project_root, "backend", f"benchmark_results_{safe_model_name}.json")
    try:
        with open(benchmark_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "model": LLM_MODEL_NAME,
                "endpoint": LLM_BASE_URL,
                "workloads": results,
                "swarm_evaluation": swarm_eval
            }, f, indent=2, ensure_ascii=False)
        print(f"\nDetailed report saved to: {benchmark_file}")
    except Exception as e:
        print(f"Failed to save results file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MiroRyba Combined LLM Benchmark")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per workload to average")
    args = parser.parse_args()
    run_benchmark(args.runs)
