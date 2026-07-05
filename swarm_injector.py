import argparse
import asyncio
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

PROMPT_TEMPLATE = """
Role: V této simulaci představuješ specifického českého čtenáře s následujícím profilem:
* Věk: {vek_kategorie}
* Lokalita: {region_typ}
* Vzdělání/Profese: {vzdelani_profese}
* Klíčová priorita: {hlavni_zajem}
* Profil důvěry k institucím (CVVM 2026): {instituce_skepse}

Pravidla:
1. Nesmíš komentovat žádné širší vládní reformy, pokud nejsou VÝSLOVNĚ zmíněny v textu. Reaguj POUZE na události popsané v článku.
2. Hodnoť text výhradně optikou toho, jak popsané události ovlivní tvůj každodenní život, rodinný rozpočet nebo tvou lokální komunitu.
3. Uprav svůj slovník a úroveň formality tak, aby přirozeně odpovídaly tvému profilu.

Úkol: Přečti si následující text a vypracuj svou osobní reakci:
1. Okamžitá reakce: Napiš jeden krátký odstavec (max 50 slov) popisující tvou bezprostřední emocionální a praktickou reakci. Co tě zneklidňuje, nebo naopak uklidňuje?
2. Spouštěč nedůvěry: Identifikuj jedno konkrétní slovo nebo frázi v textu, které ti z pohledu tvého profilu a institucionální skepse přijde nejméně věrohodné, a jednou větou vysvětli proč.

Text článku:
{article_text}
"""


def load_registry(registry_path: Path) -> List[Dict[str, Any]]:
    """
    Loads the persona registry JSON file into a list of dictionaries.

    Args:
        registry_path (Path): Path to the persona registry JSON.

    Returns:
        List[Dict[str, Any]]: A list of persona dictionaries.
    """
    if not registry_path.exists():
        logging.error(f"Persona registry not found at {registry_path}.")
        return []

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            personas = json.load(f)
        logging.info(f"Loaded {len(personas)} personas.")
        return personas
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse registry JSON: {e}")
        return []


def build_prompt(persona: Dict[str, Any], article_text: str) -> str:
    """
    Injects persona attributes into the prompt template.

    Args:
        persona (Dict[str, Any]): Dictionary containing persona attributes.
        article_text (str): The raw news article string.

    Returns:
        str: The fully formatted prompt ready for LLM generation.
    """
    try:
        return PROMPT_TEMPLATE.format(
            vek_kategorie=persona["vek_kategorie"],
            region_typ=persona["region_typ"],
            vzdelani_profese=persona["vzdelani_profese"],
            hlavni_zajem=persona["hlavni_zajem"],
            instituce_skepse=persona["instituce_skepse"],
            article_text=article_text
        )
    except KeyError as e:
        logging.error(f"Persona missing required attribute: {e}")
        raise


async def mock_mirofish_worker(persona_id: str, prompt: str, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """
    Simulates an async call to an LLM endpoint or a local VRAM-heavy model.

    Args:
        persona_id (str): The unique identifier for the persona processing the prompt.
        prompt (str): The formatted prompt string.
        semaphore (asyncio.Semaphore): Concurrency limiter.

    Returns:
        Dict[str, Any]: The result of the generation containing persona ID and response.
    """
    async with semaphore:
        logging.info(f"[{persona_id}] Worker started processing...")
        
        # Simulate network latency or GPU generation time
        await asyncio.sleep(2.0)
        
        logging.info(f"[{persona_id}] Worker finished generating.")
        return {
            "persona_id": persona_id,
            "response": f"[Simulovaná odpověď pro {persona_id}]: Tohle je naprosto nepřijatelné, dotkne se to naší rodiny.",
            "raw_prompt_length": len(prompt)
        }


async def run_swarm(personas: List[Dict[str, Any]], article_text: str, max_concurrent: int) -> List[Dict[str, Any]]:
    """
    Dispatches tasks for all loaded personas asynchronously with throttling.

    Args:
        personas (List[Dict[str, Any]]): List of persona dictionaries.
        article_text (str): The article text to evaluate.
        max_concurrent (int): Maximum number of concurrent tasks.

    Returns:
        List[Dict[str, Any]]: A list of successful worker payloads.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []
    
    for i, persona in enumerate(personas):
        persona_id = f"{persona['region_typ'].replace(' ', '_')}_{i}"
        prompt = build_prompt(persona, article_text)
        task = asyncio.create_task(mock_mirofish_worker(persona_id, prompt, semaphore))
        tasks.append(task)
        
    logging.info(f"Awaiting {len(tasks)} worker payloads...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_output = []
    for res in results:
        if isinstance(res, Exception):
            logging.error(f"Worker task failed with exception: {res}")
        else:
            final_output.append(res)
            
    return final_output


def save_swarm_output(output: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Saves the aggregated swarm outputs to a JSON file.

    Args:
        output (List[Dict[str, Any]]): The aggregated worker results.
        output_path (Path): Destination path for the JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logging.info(f"Swarm simulation complete. Results saved to {output_path}")
    except IOError as e:
        logging.error(f"Failed to write swarm output: {e}")


def main() -> None:
    """
    Main entry point for the swarm injection engine.
    """
    parser = argparse.ArgumentParser(description="Inject personas into prompts and run a simulated async LLM swarm.")
    parser.add_argument("--registry-file", type=str, default="data/processed/personas_registry.json", help="Path to input registry JSON")
    parser.add_argument("--output-file", type=str, default="data/processed/swarm_output.json", help="Path to output JSON")
    parser.add_argument("--article", type=str, default="Vláda dnes oznámila novou metodiku pro výpočet energetických dotací.", help="Text of the news article")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximum concurrent LLM requests")
    args = parser.parse_args()

    registry_path = Path(args.registry_file).resolve()
    output_path = Path(args.output_file).resolve()
    
    # 1. Load data
    personas = load_registry(registry_path)
    if not personas:
        logging.error("No personas loaded. Exiting.")
        return
        
    # Collect statistics using Counter
    region_tally = Counter(p["region_typ"] for p in personas)
    logging.info(f"Dispatching swarm with region distribution: {dict(region_tally)}")

    # 2. Run async swarm
    results = asyncio.run(run_swarm(personas, args.article, args.max_workers))
    
    # 3. Save output
    save_swarm_output(results, output_path)


if __name__ == "__main__":
    main()

