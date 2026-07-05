import argparse
import json
import logging
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple, Callable

from neo4j import GraphDatabase
from faker import Faker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class PrecomputedSampler:
    """
    Loads a precomputed JSON hierarchical probability tree
    and provides O(1) sampling for demographic traits.
    """
    def __init__(self, json_path: Path):
        self.tree: Dict[str, Any] = {}
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                self.tree = json.load(f)
        else:
            logging.warning(f"Demographic distributions JSON not found at {json_path}. Using fallback randomization.")

    def _get_gender_str(self, gender: str) -> str:
        return "muž" if gender == "male" else "žena"

    def sample_gender(self, region: str) -> str:
        """Samples gender probabilistically based on regional distribution."""
        if region not in self.tree:
            return random.choice(["male", "female"])
        genders = list(self.tree[region].keys())
        weights = [sum(age_data.get("age_weight", 0) for age_data in self.tree[region][g].values()) for g in genders]
        if sum(weights) == 0:
            return random.choice(["male", "female"])
        sampled = random.choices(genders, weights=weights, k=1)[0]
        return "male" if sampled == "muž" else "female"

    def sample_age(self, region: str, gender: str) -> int:
        """Samples age probabilistically based on region and gender."""
        gender_str = self._get_gender_str(gender)
        if region not in self.tree or gender_str not in self.tree[region]:
            return random.randint(18, 65)
        ages = list(self.tree[region][gender_str].keys())
        weights = [self.tree[region][gender_str][age].get("age_weight", 0) for age in ages]
        if sum(weights) == 0:
            return random.randint(18, 65)
        return int(random.choices(ages, weights=weights, k=1)[0])

    def _sample_from_dict(self, d: Dict[str, int], default: str) -> str:
        """Helper to sample a key from a dictionary of weights."""
        if not d:
            return default
        keys = list(d.keys())
        weights = list(d.values())
        if sum(weights) == 0:
            return default
        return random.choices(keys, weights=weights, k=1)[0]

    def sample_traits(self, region: str, gender: str, age: int) -> Tuple[str, str, str]:
        """Samples religion, education, and activity probabilistically."""
        gender_str = self._get_gender_str(gender)
        age_str = str(age)
        node = self.tree.get(region, {}).get(gender_str, {}).get(age_str, {})
        
        religion = self._sample_from_dict(node.get("religion", {}), "Bez náboženské víry")
        education = self._sample_from_dict(node.get("education", {}), "Základní")
        activity = self._sample_from_dict(node.get("activity", {}), "Neznámé")
        
        return religion, education, activity


def distribute_proportionally(total_agents: int, items: List[Dict[str, Any]]) -> List[int]:
    """
    Distributes a total number of agents across regions proportionally based on population.
    
    Args:
        total_agents: Number of agents to spawn.
        items: List of regional personas containing 'population' keys.
        
    Returns:
        List of integer agent counts for each region.
    """
    weights = [item.get("population", 1) for item in items]
    total_weight = sum(weights)
    if total_weight == 0:
        return [total_agents // len(items) + (1 if idx < total_agents % len(items) else 0) for idx in range(len(items))]
    
    allocations = []
    remainders = []
    for idx, w in enumerate(weights):
        exact = (w / total_weight) * total_agents
        allocated = int(exact)
        allocations.append(allocated)
        remainders.append((exact - allocated, idx))
        
    allocated_sum = sum(allocations)
    remaining = total_agents - allocated_sum
    remainders.sort(reverse=True, key=lambda x: x[0])
    
    for j in range(remaining):
        _, idx = remainders[j]
        allocations[idx] += 1
        
    return allocations


def get_ideology_sampler(election_data: Dict[str, Dict[str, int]]) -> Callable[[str, int, str, str], str]:
    """
    Returns a closure that samples political ideology based on exact 2025 election data
    modified by sociological demographic curves.
    """
    def sample_ideology(region: str, age: int, education: str, gender: str) -> str:
        region_votes = election_data.get(region, {})
        if not region_votes:
            return "Nezávislý/Nešetřeno"
        
        parties = list(region_votes.keys())
        base_weights = list(region_votes.values())
        
        modified_weights = []
        for party, weight in zip(parties, base_weights):
            multiplier = 1.0
            
            if party in ["SPOLU", "Piráti", "STAN", "Zelení"]:
                if age < 35: multiplier *= 1.8
                if "vysokoškolské" in education.lower(): multiplier *= 2.0
                if age > 65: multiplier *= 0.5
            elif party in ["ANO", "SPD", "Stačilo! (KSČM)", "PRO", "Přísaha"]:
                if age > 60: multiplier *= 1.8
                if "základní" in education.lower() or "bez maturity" in education.lower(): multiplier *= 1.5
                if "vysokoškolské" in education.lower(): multiplier *= 0.4
            elif party == "Motoristé sobě":
                if gender == "male" and age < 45: multiplier *= 2.0
                
            modified_weights.append(weight * multiplier)
            
        return random.choices(parties, weights=modified_weights)[0]
    return sample_ideology


def _create_persona_node(
    tx: Any, 
    persona: Dict[str, Any], 
    g_id: str, 
    sampler: PrecomputedSampler, 
    election_data: Dict[str, Dict[str, int]],
    fake: Faker,
    all_hobbies: List[str]
) -> None:
    """
    Constructs a persona and executes a Neo4j Cypher query to inject the node.
    """
    region = persona.get("region_typ", "Unknown")
    
    gender = sampler.sample_gender(region)
    age = sampler.sample_age(region, gender)
    sampled_religion, sampled_education, sampled_activity = sampler.sample_traits(region, gender, age)
    
    if gender == "male":
        real_name = fake.name_male()
    else:
        real_name = fake.name_female()
        
    username = fake.user_name() + str(random.randint(10, 999))
    
    mbtis = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]
    mbti = random.choice(mbtis)
    
    hobbies = ", ".join(random.sample(all_hobbies, random.randint(2, 3)))
    
    ideology_sampler = get_ideology_sampler(election_data)
    ideology = ideology_sampler(region, age, sampled_education, gender)
    
    individualized_persona = {
        "realname": real_name,
        "username": username,
        "region_typ": region,
        "country": "Czech Republic",
        "age": age,
        "gender": gender,
        "mbti": mbti,
        "religion": sampled_religion,
        "education": sampled_education,
        "profession": sampled_education,
        "activity": sampled_activity,
        "hlavni_zajem": hobbies,
        "politicka_preference": ideology,
        "instituce_skepse": persona.get('instituce_skepse', ''),
        "bio": f"Obyvatel regionu {region}. Volí: {ideology}. Náboženství: {sampled_religion}. Vzdělání: {sampled_education}. Ekonomická aktivita: {sampled_activity}.",
        "persona": f"Jednotlivec z regionu {region}, věk {age} let. Zájmy: {hobbies}. Pohled na instituce: {persona.get('instituce_skepse', '')}"
    }
    
    node_name = f"{real_name} ({region})"
    
    query = """
    CREATE (n:Entity:Person {
        uuid: randomUUID(),
        name_lower: toLower($name),
        graph_id: $graph_id,
        name: $name,
        summary: $summary,
        attributes_json: $attributes_json,
        created_at: toString(datetime())
    })
    """
    summary = f"Citizen {real_name}, {age}yo {gender} from {region}. Education: {sampled_education}. Activity: {sampled_activity}. Religion: {sampled_religion}."
    attributes_json = json.dumps(individualized_persona, ensure_ascii=False)
    
    tx.run(query, name=node_name, graph_id=g_id, summary=summary, attributes_json=attributes_json)


def import_personas_to_neo4j(registry_path: Path, uri: str, user: str, password: str, graph_id: str, num_agents: int) -> None:
    """
    Reads the dynamic JSON personas and integrates them directly into the live Neo4j knowledge graph backend.
    
    Args:
        registry_path: Path to the generated archetypes JSON.
        uri: Neo4j connection URI.
        user: Neo4j username.
        password: Neo4j password.
        graph_id: Target graph scope identifier.
        num_agents: Total agents to spawn.
    """
    if not registry_path.exists():
        logging.error(f"Registry file not found: {registry_path}")
        return

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    if not registry:
        logging.warning("Registry is empty. Nothing to import.")
        return

    try:
        dist_path = registry_path.parent / "demographic_distributions.json"
        logging.info("Loading precomputed hierarchical census tree...")
        sampler = PrecomputedSampler(dist_path)
        logging.info("Census tree loaded. Beginning graph injection...")

        driver = GraphDatabase.driver(uri, auth=(user, password))
        fake = Faker('cs_CZ')
        
        election_path = registry_path.parent / "election_2025_distributions.json"
        try:
            with open(election_path, "r", encoding="utf-8") as f:
                election_data = json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load election data, fallback to empty: {e}")
            election_data = {}
        
        all_hobbies = [
            "Zahrádkářství", "Cyklistika", "Turistika", "Čtení knih", "Videohry", "Sledování politiky",
            "Sledování sportu (hokej/fotbal)", "Vaření a pečení", "Kutění (DIY)", "Cestování", "Houbaření",
            "Fotografování", "Domácí mazlíčci (psi)", "Domácí mazlíčci (kočky)", "Posilování/Fitness",
            "Běhání", "Plavání", "Kultura (divadlo, výstavy)", "Sběratelství", "Sledování seriálů a filmů",
            "Zimní sporty (lyžování)", "Rybářství", "Historie", "Technologie a IT", "Zpěv nebo hra na hudební nástroj",
            "Dobrovolnictví", "Zájmové spolky (Sokol, hasiči)", "Řemeslná výroba", "Motocykly", "Kempování"
        ]

        with driver.session() as session:
            # Clear old tests
            session.run("MATCH (n:Persona) DETACH DELETE n")
            
            allocations = distribute_proportionally(num_agents, registry)
            
            for idx, count in enumerate(allocations):
                persona = registry[idx]
                for _ in range(count):
                    session.execute_write(_create_persona_node, persona, graph_id, sampler, election_data, fake, all_hobbies)
                
            logging.info(f"Successfully injected {num_agents} individual 'Person' nodes into Neo4j knowledge graph.")
        
    except Exception as e:
        logging.error(f"Failed to connect or write to Neo4j: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Integrate dynamic JSON personas into Neo4j.")
    parser.add_argument("--registry-file", type=str, default="data/processed/personas_registry.json", help="Path to input JSON")
    parser.add_argument("--neo4j-uri", type=str, default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--neo4j-user", type=str, default="neo4j", help="Neo4j User")
    parser.add_argument("--neo4j-password", type=str, default="password", help="Neo4j Password")
    parser.add_argument("--graph-id", type=str, default="default-personas-graph", help="Target graph ID in Neo4j")
    parser.add_argument("--num-agents", type=int, default=28, help="Number of individual agents to spawn based on the demographics")
    
    args = parser.parse_args()
    
    import_personas_to_neo4j(
        Path(args.registry_file).resolve(),
        args.neo4j_uri,
        args.neo4j_user,
        args.neo4j_password,
        args.graph_id,
        args.num_agents
    )


if __name__ == "__main__":
    main()
