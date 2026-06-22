import os
import subprocess
import sys
import time
import json

models = [
    "mistral-medium-3.5"
]

backend_dir = os.path.dirname(os.path.abspath(__file__))

print("Starting FULL PIPELINE Benchmarking for the Top 3 Cerit-SC Models...")

for model in models:
    print(f"\n==========================================")
    print(f"FULL PIPELINE Benchmarking: {model}")
    print(f"==========================================")
    
    # 1. Shutdown Docker
    print(f"[{model}] Stopping Docker...")
    subprocess.run(["docker", "compose", "down"], cwd=os.path.dirname(backend_dir), check=True)
    
    # 2. Start Docker with the specific swarm generation model
    print(f"[{model}] Starting Docker with {model} as the Swarm Generator...")
    docker_env = os.environ.copy()
    docker_env["LLM_MODEL_NAME"] = model
    subprocess.run(["docker", "compose", "up", "-d"], env=docker_env, cwd=os.path.dirname(backend_dir), check=True)
    
    # 3. Wait for Flask to fully boot up
    print(f"[{model}] Waiting 30 seconds for Flask backend to initialize...")
    time.sleep(30)
    
    # 4. Run the benchmark, explicitly setting DeepSeek as the Judge
    print(f"[{model}] Running benchmark pipeline with deepseek-v4-pro as the Judge...")
    benchmark_env = os.environ.copy()
    benchmark_env["LLM_MODEL_NAME"] = "deepseek-v4-pro"  # HARDCODED JUDGE
    benchmark_env["EXTRACTION_MODEL"] = "deepseek-v4-pro"
    benchmark_env["REPORT_MODEL"] = "deepseek-v4-pro"
    benchmark_env["LLM_BASE_URL"] = "https://llm.ai.e-infra.cz/v1"
    benchmark_env["OPENAI_API_BASE_URL"] = "https://llm.ai.e-infra.cz/v1"
    benchmark_env["LLM_API_KEY"] = "sk-00ef62621e5d4d028b63130760f40a88"
    benchmark_env["OPENAI_API_KEY"] = "sk-00ef62621e5d4d028b63130760f40a88"
    
    cmd = [sys.executable, "benchmark_full_pipeline.py"]
    try:
        subprocess.run(cmd, env=benchmark_env, cwd=backend_dir, check=True)
    except subprocess.CalledProcessError:
        print(f"Warning: Full Pipeline Benchmark failed for {model}. Moving to next.")
        
    print(f"[{model}] Completed. Saving results...")
    time.sleep(5)

print("\n\nAll Top 3 Full Pipeline Benchmarks completed!")
