import argparse
import json
import logging
from pathlib import Path
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def import_personas_to_neo4j(registry_path: Path, uri: str, user: str, password: str, graph_id: str) -> None:
    """
    Reads the dynamic JSON personas and integrates them directly into the live Neo4j knowledge graph backend.
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
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        def _create_persona_node(tx, persona, g_id):
            # Create an Entity node with the label 'Persona' and properties
            region = persona.get("region_typ", "Unknown")
            query = """
            MERGE (n:Entity:Persona {name_lower: toLower($region), graph_id: $graph_id})
            ON CREATE SET
                n.uuid = randomUUID(),
                n.name = $region,
                n.summary = $summary,
                n.attributes_json = $attributes_json,
                n.created_at = toString(datetime())
            ON MATCH SET
                n.summary = $summary,
                n.attributes_json = $attributes_json
            """
            summary = f"Persona archetype for {region}"
            attributes_json = json.dumps(persona, ensure_ascii=False)
            
            tx.run(query, region=region, graph_id=g_id, summary=summary, attributes_json=attributes_json)

        with driver.session() as session:
            for count, persona in enumerate(registry, 1):
                session.execute_write(_create_persona_node, persona, graph_id)
                logging.info(f"Imported persona {count}/{len(registry)}: {persona.get('region_typ')}")
                
        driver.close()
        logging.info("Successfully integrated dynamic JSON personas into Neo4j knowledge graph.")
        
    except Exception as e:
        logging.error(f"Failed to connect or write to Neo4j: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrate dynamic JSON personas into Neo4j.")
    parser.add_argument("--registry-file", type=str, default="data/processed/personas_registry.json", help="Path to input JSON")
    parser.add_argument("--neo4j-uri", type=str, default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--neo4j-user", type=str, default="neo4j", help="Neo4j User")
    parser.add_argument("--neo4j-password", type=str, default="password", help="Neo4j Password")
    parser.add_argument("--graph-id", type=str, default="default-personas-graph", help="Target graph ID in Neo4j")
    
    args = parser.parse_args()
    
    import_personas_to_neo4j(
        Path(args.registry_file).resolve(),
        args.neo4j_uri,
        args.neo4j_user,
        args.neo4j_password,
        args.graph_id
    )

if __name__ == "__main__":
    main()
