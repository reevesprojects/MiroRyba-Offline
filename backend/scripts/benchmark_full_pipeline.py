"""
MiroRyba Full-Pipeline Prompt & Settings Benchmark
Orchestrates the entire backend pipeline to evaluate swarm outputs against a rigorous editorial rubric.
"""

import os
import sys
import time
import json
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List

# Define API Base
API_BASE = "http://localhost:5001"
OLLAMA_BASE = "http://localhost:11434/api/generate"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(BASE_DIR, "scripts", "benchmark_articles")
SIMULATIONS_DIR = os.path.join(BASE_DIR, "uploads", "simulations")
PROGRESS_FILE = os.path.join(BASE_DIR, "scripts", "benchmark_progress.json")

# 4 Test Articles
ARTICLES = ["sugar_tax.txt", "ai_regulation.txt", "football.txt", "healthcare.txt"]

# 4 Prompt & Settings Configurations
CONFIGS = {
    "control_low": {
        "description": "Standard prompt, low temperature",
        "system_instruction": "Simulace diskuse. Agenti se vyjadřují jako běžní lidé na internetu. Reaguj přirozeně.",
        "temp": 0.5,
    },
    "social_high": {
        "description": "Social media native, high creativity",
        "system_instruction": "Simulace sociálních sítí. Vyjadřuj se extrémně a emotivně. Najdi v článku to, co autor naschvál zamlčel, a křič o tom. Každý agent má zcela jiný, vyhraněný názor. Silně ukotvi své argumenty v české každodenní realitě a kultuře.",
        "temp": 0.8,
    },
    "debate_high": {
        "description": "Argumentative debater, high creativity",
        "system_instruction": "Ostrá debatní simulace. Jsi vysoce kritický čtenář. Okamžitě útoč na slabá místa a novinářskou zaujatost (framing) článku. Zaujmi striktně kontrariánský postoj – nesouhlas s ostatními. Všechny argumenty spojuj se specifickou českou politickou a společenskou situací.",
        "temp": 0.8,
    },
    "journalist_low": {
        "description": "Analytical commentator, low temperature",
        "system_instruction": "Simulace expertní zpětné vazby. Sloužíš jako nelítostný editor pro autora článku. Věcně analyzuj slepá místa, logické díry a chybějící kontext. Vysvětli, jak článek selhává v pochopení českého lokálního kontextu. Tvé příspěvky musí poskytnout jasnou inspiraci pro přepsání článku.",
        "temp": 0.4,
    }
}

MAX_ROUNDS = 20

# Global state for dashboard
state = {
    "started_at": time.time(),
    "completed_runs": [],
    "current_run": None,
    "total_runs": len(ARTICLES) * len(CONFIGS),
    "completed_count": 0
}

def update_progress_file():
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        elapsed = int(time.time() - state["started_at"])
        mins, secs = divmod(elapsed, 60)
        
        pct = (state["completed_count"] / state["total_runs"]) * 100 if state["total_runs"] else 0
        
        html = f"""
        <html><head><meta http-equiv="refresh" content="5">
        <style>
            body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
            .box {{ border: 1px solid #4a4a4a; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
            h2 {{ color: #569cd6; margin-top: 0; }}
            .bar {{ background: #333; width: 100%; height: 20px; border-radius: 10px; overflow: hidden; }}
            .fill {{ background: #4caf50; height: 100%; width: {pct}%; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #4a4a4a; padding: 8px; text-align: left; }}
            th {{ background: #2d2d2d; }}
        </style></head><body>
        
        <div class="box">
            <h2>MiroRyba Full-Pipeline Benchmark Monitor</h2>
            <div>Elapsed Time: {mins}m {secs}s</div>
            <div style="margin: 10px 0;">Overall Progress: {state["completed_count"]}/{state["total_runs"]} ({pct:.1f}%)</div>
            <div class="bar"><div class="fill"></div></div>
        </div>
        """
        
        if state["current_run"]:
            cr = state["current_run"]
            metrics_html = ""
            if "live_metrics" in cr:
                lm = cr["live_metrics"]
                prep_status = f"<br/><br/> <span style='color: #4caf50;'>[Stage 4 Progress]: {lm['prep_msg']}</span>" if "prep_msg" in lm else ""
                metrics_html = f"<div style='margin-top: 10px; padding: 10px; background: #2d2d2d; border-radius: 5px;'><b>Total Pipeline Tokens: {lm['tokens']}</b> <br/> <small>Prep Stage (Ontology+Profiles): {lm['stage_tokens']['prep']} tokens | Swarm Stage: {lm['stage_tokens']['swarm']} tokens (~{lm['tps']} tokens/sec)</small> {prep_status} <br/><br/> <b>Swarm Actions:</b> {lm['posts']} posts | {lm['comments']} comments</div>"
                
            html += f"""
            <div class="box">
                <h3 style="color: #ce9178;">Current Run: {cr['config_id']} × {cr['article']}</h3>
                <div>Stage: {cr['stage']}</div>
                {metrics_html}
            </div>
            """
            
        html += """
        <div class="box">
            <h3>Completed Runs</h3>
            <table><tr><th>Config</th><th>Article</th><th>Fidelity</th><th>Facts</th><th>Actionability</th><th>Distinctness</th><th>Total</th><th>Time</th></tr>
        """
        for run in state["completed_runs"]:
            html += f"<tr><td>{run['config']}</td><td>{run['article']}</td><td>{run['scores']['fidelity']}/5</td><td>{run['scores']['facts']}/3</td><td>{run['scores']['actionability']}/5</td><td>{run['scores']['distinctness']}/5</td><td>{run['total_score']}/18</td><td>{run['time_taken']}s</td></tr>"
            
        html += "</table></div></body></html>"
        self.wfile.write(html.encode('utf-8'))

def start_dashboard():
    server = HTTPServer(('0.0.0.0', 8099), DashboardHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print("Live dashboard running at http://localhost:8099")

def set_current_stage(stage: str):
    if state["current_run"]:
        state["current_run"]["stage"] = stage
        print(f"[{state['current_run']['config_id']} x {state['current_run']['article']}] Stage: {stage}")
        update_progress_file()

def wait_for_task(task_id: str, timeout_sec: int = 1800):
    start = time.time()
    while time.time() - start < timeout_sec:
        res = requests.get(f"{API_BASE}/api/graph/task/{task_id}").json()
        if res.get('data', {}).get('status') == 'completed':
            return res['data']
        if res.get('data', {}).get('status') == 'failed':
            raise Exception(f"Task failed: {res['data'].get('error')}")
        time.sleep(2)
    raise Exception("Task timeout")

def wait_for_prepare(task_id: str, sim_id: str, timeout_sec: int = 1800):
    start = time.time()
    while time.time() - start < timeout_sec:
        res = requests.post(f"{API_BASE}/api/simulation/prepare/status", json={"task_id": task_id, "simulation_id": sim_id}).json()
        data = res.get('data', {})
        
        # Display live progress during Stage 4
        if state["current_run"]:
            pct = data.get('progress', 0)
            msg = data.get('message', 'Generating agent personas...')
            
            # Initialize live metrics block if missing
            if "live_metrics" not in state["current_run"]:
                state["current_run"]["live_metrics"] = {
                    "posts": 0, "comments": 0, "tokens": 0, "tps": 0,
                    "stage_tokens": {"prep": 0, "swarm": 0}
                }
            
            state["current_run"]["live_metrics"]["prep_msg"] = f"{pct}% - {msg}"
            update_progress_file()

        if data.get('already_prepared') or data.get('status') == 'ready':
            return True
        time.sleep(5)
    raise Exception("Prepare timeout")

def wait_for_simulation(sim_id: str, accumulated_tokens: int, timeout_sec: int = 2400):
    start = time.time()
    total_tokens = accumulated_tokens
    
    while time.time() - start < timeout_sec:
        # Check status
        res = requests.get(f"{API_BASE}/api/simulation/{sim_id}/run-status").json()
        data = res.get('data', {})
        
        # Fetch posts/comments to calculate live metrics
        try:
            posts = requests.get(f"{API_BASE}/api/simulation/{sim_id}/posts?platform=reddit&limit=1000").json().get('data', {}).get('posts', [])
            comments = requests.get(f"{API_BASE}/api/simulation/{sim_id}/comments?limit=1000").json().get('data', {}).get('comments', [])
            
            # Rough token estimate: 1 word ~ 1.33 tokens
            text_content = " ".join([p.get('content', '') for p in posts] + [c.get('content', '') for c in comments])
            word_count = len(text_content.split())
            swarm_tokens = int(word_count * 1.33)
            current_total = accumulated_tokens + swarm_tokens
            
            elapsed = time.time() - start
            tps = swarm_tokens / elapsed if elapsed > 0 else 0
            
            if state["current_run"]:
                state["current_run"]["live_metrics"] = {
                    "posts": len(posts),
                    "comments": len(comments),
                    "tokens": current_total,
                    "tps": round(tps, 1),
                    "stage_tokens": {
                        "prep": accumulated_tokens,
                        "swarm": swarm_tokens
                    }
                }
                update_progress_file()
                
        except Exception as e:
            pass # Ignore fetch errors during polling
            
        if data.get('runner_status') in ['completed', 'stopped', 'failed', 'none']:
            return True
            
        time.sleep(5)
        
    raise Exception("Simulation timeout")

def evaluate_with_llm_judge(posts: list, comments: list) -> dict:
    if not posts and not comments:
        return {"fidelity": 1, "facts": 1, "actionability": 1, "distinctness": 1}
        
    # Compile output summary
    output_text = "=== POSTS ===\n"
    for p in posts[:10]:
        output_text += f"[{p.get('agent_name', 'Unknown')}]: {p.get('content', '')}\n"
    output_text += "\n=== COMMENTS ===\n"
    for c in comments[:20]:
        output_text += f"[{c.get('agent_name', 'Unknown')}]: {c.get('content', '')}\n"
        
    prompt = f"""You are a ruthless senior editor judging an AI swarm simulation of a social media discussion.
Review the following discussion outputs generated by the simulation:

{output_text}

Rate the simulation strictly out of the following criteria. Return ONLY a valid JSON object.

CRITERIA:
1. "fidelity" (1-5): Persona Fidelity & Linguistic Realism. Do they sound authentically Czech? (1=generic robot, 5=flawless demographic nuance).
2. "facts" (1 or 3): Strict Factual Guardrailing. Did they hallucinate? (3=passed, only discussed article facts. 1=failed, invented laws/events).
3. "actionability" (1-5): Editorial Actionability. Did they point out specific textual triggers and blind spots useful for a journalist? (1=generic whining, 5=highly actionable specific critique).
4. "distinctness" (1-5): Swarm Distinctness. Did the agents offer fundamentally different angles or just homogenize? (1=echo chamber, 5=high ideological variance).

Output Format exactly:
{{
  "fidelity": [score],
  "facts": [score],
  "actionability": [score],
  "distinctness": [score],
  "justification": "Brief 1-sentence reason"
}}
"""
    for attempt in range(3):
        try:
            response = requests.post(f"{os.environ.get('OPENAI_API_BASE_URL', 'https://llm.ai.e-infra.cz/v1')}/chat/completions", 
                headers={"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', 'sk-00ef62621e5d4d028b63130760f40a88')}"},
                json={
                    "model": os.environ.get("LLM_MODEL_NAME", "Qwen3.5-122b"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                },
                timeout=120
            )
            res_json = json.loads(response.json()['choices'][0]['message']['content'])
            return {
                "fidelity": int(res_json.get("fidelity", 1)),
                "facts": int(res_json.get("facts", 1)),
                "actionability": int(res_json.get("actionability", 1)),
                "distinctness": int(res_json.get("distinctness", 1)),
                "justification": res_json.get("justification", "")
            }
        except Exception as e:
            if attempt == 2:
                print(f"LLM Judge failed after 3 attempts: {e}")
                return {"fidelity": 0, "facts": 0, "actionability": 0, "distinctness": 0, "justification": str(e)}
            print(f"LLM Judge timeout/error, retrying ({attempt+1}/3)...")
            time.sleep(10)
        print(f"LLM Judge failed: {e}")
        return {"fidelity": 1, "facts": 1, "actionability": 1, "distinctness": 1, "justification": "Failed to parse judge output"}

def run_pipeline(article_file: str, config_id: str, config_data: dict):
    run_start = time.time()
    accumulated_tokens = 0
    
    # 1. Upload & Ontology
    set_current_stage("1. Uploading Article & Generating Ontology")
    file_path = os.path.join(ARTICLES_DIR, article_file)
    with open(file_path, 'rb') as f:
        files = {'files': (article_file, f, 'text/plain')}
        data = {'simulation_requirement': config_data['system_instruction']}
        res = requests.post(f"{API_BASE}/api/graph/ontology/generate", files=files, data=data)
        
    res_data = res.json()
    if not res_data.get('success'):
        raise Exception(f"Ontology failed: {res_data}")
    project_id = res_data['data']['project_id']
    
    # Count ontology tokens
    try:
        onto_path = os.path.join(BASE_DIR, "uploads", "projects", project_id, "ontology.json")
        if os.path.exists(onto_path):
            with open(onto_path, 'r', encoding='utf-8') as f:
                onto_text = f.read()
                accumulated_tokens += int(len(onto_text.split()) * 1.33)
    except: pass
    
    try:
        # 2. Build Graph
        set_current_stage("2. Building Neo4j Graph")
        res = requests.post(f"{API_BASE}/api/graph/build", json={"project_id": project_id}).json()
        task_info = wait_for_task(res['data']['task_id'])
        graph_id = task_info['result']['graph_id']
        
        # 3. Create Simulation
        set_current_stage("3. Creating Simulation")
        res = requests.post(f"{API_BASE}/api/simulation/create", json={"project_id": project_id, "graph_id": graph_id}).json()
        sim_id = res['data']['simulation_id']
        
        # 4. Prepare Simulation
        set_current_stage("4. Preparing Personas & Config")
        res = requests.post(f"{API_BASE}/api/simulation/prepare", json={"simulation_id": sim_id}).json()
        if not res['data'].get('already_prepared'):
            wait_for_prepare(res['data']['task_id'], sim_id)
            
        # Count profile tokens
        try:
            prof_path = os.path.join(SIMULATIONS_DIR, sim_id, "reddit_profiles.json")
            if os.path.exists(prof_path):
                with open(prof_path, 'r', encoding='utf-8') as f:
                    prof_text = f.read()
                    accumulated_tokens += int(len(prof_text.split()) * 1.33)
        except: pass
            
        # 5. Inject Temperature into simulation config
        set_current_stage("5. Injecting Temperature Config")
        config_path = os.path.join(SIMULATIONS_DIR, sim_id, "simulation_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                sim_config = json.load(f)
            sim_config["temperature"] = config_data["temp"]
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(sim_config, f, ensure_ascii=False, indent=2)
                
        # 6. Start Simulation
        set_current_stage("6. Running Swarm Simulation")
        requests.post(f"{API_BASE}/api/simulation/start", json={"simulation_id": sim_id, "platform": "reddit", "max_rounds": MAX_ROUNDS, "force": True})
        wait_for_simulation(sim_id, accumulated_tokens, timeout_sec=900)  # Up to 15 mins
        
        # 7. Harvest Outputs
        set_current_stage("7. Harvesting Posts")
        posts = requests.get(f"{API_BASE}/api/simulation/{sim_id}/posts?platform=reddit&limit=100").json().get('data', {}).get('posts', [])
        comments = requests.get(f"{API_BASE}/api/simulation/{sim_id}/comments?limit=200").json().get('data', {}).get('comments', [])
        
        # 8. Evaluate
        set_current_stage("8. LLM Judge Evaluation")
        scores = evaluate_with_llm_judge(posts, comments)
        
    finally:
        # Cleanup
        set_current_stage("9. Cleanup")
        try:
            requests.delete(f"{API_BASE}/api/graph/delete/{graph_id}")
        except: pass
        try:
            requests.delete(f"{API_BASE}/api/graph/project/{project_id}")
        except: pass

    time_taken = int(time.time() - run_start)
    total_score = scores['fidelity'] + scores['facts'] + scores['actionability'] + scores['distinctness']
    
    return {
        "config": config_id,
        "article": article_file,
        "scores": scores,
        "total_score": total_score,
        "time_taken": time_taken,
        "post_count": len(posts) + len(comments)
    }

def main():
    print("Starting Benchmark Harness...")
    start_dashboard()
    
    for config_id, config_data in CONFIGS.items():
        for article in ARTICLES:
            state["current_run"] = {"config_id": config_id, "article": article, "stage": "Starting"}
            update_progress_file()
            
            success = False
            for attempt in range(3):
                try:
                    result = run_pipeline(article, config_id, config_data)
                    state["completed_runs"].append(result)
                    success = True
                    break
                except Exception as e:
                    print(f"Run failed for {config_id} x {article} (Attempt {attempt+1}/3): {e}")
                    time.sleep(20) # Wait 20 seconds before retrying if rate limited
                    
            if not success:
                print(f"Completely failed {config_id} x {article} after 3 attempts.")
                state["completed_runs"].append({
                    "config": config_id,
                    "article": article,
                    "scores": {"fidelity": 0, "facts": 0, "actionability": 0, "distinctness": 0},
                    "total_score": 0,
                    "time_taken": 0,
                    "error": str(e)
                })
            
            # Prevent rate limiting on the university cluster between runs
            print("Sleeping for 15 seconds to respect rate limits...")
            time.sleep(15)
            
            state["completed_count"] += 1
            update_progress_file()
            
    print("\nBENCHMARK COMPLETE!")
    
    model_name = os.environ.get("LLM_MODEL_NAME", "default_model").replace(':', '-')
    output_file = os.path.join(BASE_DIR, f"full_benchmark_results_{model_name}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(state["completed_runs"], f, ensure_ascii=False, indent=2)
        
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
