"""
MiroRyba Benchmark Comparison Tool
Scans for benchmark_results_*.json files and displays a side-by-side comparison.
"""

import os
import glob
import json


def compare_results():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pattern = os.path.join(backend_dir, "benchmark_results_*.json")
    files = glob.glob(pattern)

    if not files:
        print("No benchmark results found. Run `benchmark_llm.py` on your configured models first.")
        return

    all_data = []
    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.append(data)
        except Exception as e:
            print(f"Error reading {os.path.basename(file)}: {e}")

    # Sort by timestamp
    all_data.sort(key=lambda x: x.get("timestamp", 0))

    print("=" * 100)
    print("MIROFISH / MIRORYBA LLM MODEL COMPARISON REPORT")
    print("=" * 100)
    
    # Headers
    headers = [
        "Model Name", 
        "Avg Tech Latency", 
        "Avg Tech Speed", 
        "JSON Pass", 
        "CZ Lang Score", 
        "CZ Persona Score", 
        "CZ Coherence"
    ]
    
    print(f"{headers[0]:<25} | {headers[1]:<16} | {headers[2]:<14} | {headers[3]:<10} | {headers[4]:<13} | {headers[5]:<16} | {headers[6]:<12}")
    print("-" * 115)

    for data in all_data:
        model = data.get("model", "Unknown")
        workloads = data.get("workloads", [])
        swarm = data.get("swarm_evaluation", {})

        # Compute averages
        tech_times = []
        tech_speeds = []
        json_passes = []

        for wl in workloads:
            # Latency (strip 's')
            t_str = wl.get("avg_time", "0.00s").replace("s", "")
            tech_times.append(float(t_str))
            
            # Speed
            s_str = wl.get("avg_tps", "0.0")
            tech_speeds.append(float(s_str))
            
            # JSON Pass
            jp = wl.get("json_pass", "N/A")
            if jp != "N/A":
                json_passes.append(float(jp.replace("%", "")) / 100.0)

        avg_time = sum(tech_times) / len(tech_times) if tech_times else 0.0
        avg_speed = sum(tech_speeds) / len(tech_speeds) if tech_speeds else 0.0
        avg_json = sum(json_passes) / len(json_passes) if json_passes else 1.0

        # Swarm scores
        swarm_success = swarm.get("success", False)
        scores = swarm.get("scores", {})
        cz_lang = f"{scores.get('language_naturalness', 0)}/5" if swarm_success else "N/A"
        cz_pers = f"{scores.get('persona_consistency', 0)}/5" if swarm_success else "N/A"
        cz_cohe = f"{scores.get('interactive_coherence', 0)}/5" if swarm_success else "N/A"

        print(f"{model:<25} | {avg_time:.2f}s           | {avg_speed:.1f} t/s       | {avg_json * 100:.0f}%       | {cz_lang:<13} | {cz_pers:<16} | {cz_cohe:<12}")

    print("=" * 100)
    print("\nSAMPLE SWARM DIALOGUE BY MODEL:")
    for data in all_data:
        model = data.get("model", "Unknown")
        swarm = data.get("swarm_evaluation", {})
        if swarm.get("success"):
            print(f"\n--- Model: {model} ---")
            thread = swarm.get("thread", {})
            print(f"Tomáš (Praha): \"{thread.get('post')}\"")
            print(f"Marie (Ostrava): \"{thread.get('reply')}\"")
    print("=" * 100)


if __name__ == "__main__":
    compare_results()
