"""
MiroFish / MiroRyba Local Embedding Benchmarking Utility (Self-Contained)
Measures embedding latency, throughput, and dimensionality.
"""

import os
import sys
import time
from typing import List, Optional
import requests


# Simple zero-dependency .env loader to read active config
def parse_env(env_path: str) -> dict:
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


# Standalone Embedding Service implementation
class StandaloneEmbeddingService:
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self._embed_url = f"{self.base_url}/api/embed"
        self._dimension = None

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Detect dimensions dynamically
            vec = self._request_embeddings(["dim_check"])[0]
            self._dimension = len(vec)
        return self._dimension

    def embed(self, text: str) -> List[float]:
        return self._request_embeddings([text])[0]

    def embed_batch(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        results = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            results.extend(self._request_embeddings(batch))
        return results

    def _request_embeddings(self, texts: List[str]) -> List[List[float]]:
        payload = {
            "model": self.model,
            "input": texts,
        }
        response = requests.post(self._embed_url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("embeddings", [])


def run_embedding_benchmark():
    print("=" * 60)
    print("MiroRyba Text Embedding Benchmark (Self-Contained)")
    print("=" * 60)

    # Resolve active config from root .env
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(project_root, '.env')
    config = parse_env(env_path)

    model = config.get('EMBEDDING_MODEL', 'nomic-embed-text')
    base_url = config.get('EMBEDDING_BASE_URL', 'http://localhost:11434')

    try:
        service = StandaloneEmbeddingService(model, base_url)
        
        # 1. Verification and Dimension Check
        print("\n[1/3] Initializing and checking dimensions...")
        t0 = time.time()
        dimension = service.dimension
        init_time = time.time() - t0
        print(f"  Model Name: {service.model}")
        print(f"  Endpoint:   {service._embed_url}")
        print(f"  Dimensions: {dimension} (Expected: 1024 for bge-m3)")
        print(f"  Warm-up:    {init_time:.2f}s")

        # 2. Single-Text Latency Benchmarking
        print("\n[2/3] Benchmarking single-sentence latency...")
        test_sentences = [
            "Česká vláda schválila novou spotřební daň na slazené nápoje.",
            "IT specialista Tomáš z Prahy podporuje zdravý životní styl.",
            "Prodavačka Marie z Ostravy vyjadřuje obavy o rodinný rozpočet.",
            "Umělá inteligence pomáhá novinářům analyzovat veřejné mínění.",
            "Grafová databáze Neo4j uchovává vztahy mezi entitami z článků."
        ]

        latencies = []
        for i, sentence in enumerate(test_sentences):
            t0 = time.time()
            vector = service.embed(sentence)
            elapsed = time.time() - t0
            latencies.append(elapsed)
            print(f"  Sentence {i+1}: {elapsed * 1000:.1f}ms | Vector norm: {sum(v**2 for v in vector)**0.5:.4f}")

        avg_latency_ms = (sum(latencies) / len(latencies)) * 1000
        print(f"  Average Single Latency: {avg_latency_ms:.1f}ms")

        # 3. Batch Throughput Benchmarking
        print("\n[3/3] Benchmarking batch throughput (32 documents)...")
        batch_texts = [
            f"Tento vzorový dokument číslo {i} slouží pro zátěžové testování embedding serveru."
            for i in range(32)
        ]

        t0 = time.time()
        vectors = service.embed_batch(batch_texts, batch_size=16)
        batch_elapsed = time.time() - t0
        
        doc_per_sec = len(batch_texts) / batch_elapsed if batch_elapsed > 0 else 0
        print(f"  Processed {len(vectors)} documents in {batch_elapsed:.2f}s")
        print(f"  Throughput: {doc_per_sec:.1f} docs/sec")

        # Summary Report
        print("\n" + "=" * 60)
        print("EMBEDDING BENCHMARK SUMMARY REPORT")
        print("=" * 60)
        print(f"Embedding Model:   {service.model}")
        print(f"Vector Dimensions: {dimension}")
        print(f"Avg Single Latency: {avg_latency_ms:.1f}ms")
        print(f"Batch Throughput:   {doc_per_sec:.1f} docs/sec")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Embedding benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_embedding_benchmark()
