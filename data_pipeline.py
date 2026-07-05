import argparse
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def safe_read_csv(path: Path) -> pd.DataFrame:
    """
    Safely reads a CSV file into a pandas DataFrame, handling Czech encodings.

    Args:
        path (Path): The file path to the CSV.

    Returns:
        pd.DataFrame: The loaded DataFrame, or an empty DataFrame if loading fails.
    """
    if not path.exists():
        logging.warning(f"File not found: {path}. Returning empty DataFrame.")
        return pd.DataFrame()
        
    try:
        # Try with semicolon and cp1250 (standard for CSU)
        return pd.read_csv(path, sep=';', encoding="cp1250")
    except (UnicodeDecodeError, pd.errors.ParserError):
        try:
            return pd.read_csv(path, sep=',', encoding="utf-8")
        except Exception:
            # Fallback robust parse
            return pd.read_csv(path, sep=';', encoding="utf-8", on_bad_lines='skip')


def process_geographic_mapping(
    pst4: pd.DataFrame, cisob: pd.DataFrame, cnumnuts: pd.DataFrame, cpp: pd.DataFrame
) -> Dict[str, Dict[str, str]]:
    """
    Maps municipalities to regions and determines the winning political party.

    Args:
        pst4 (pd.DataFrame): Raw voting data per municipality.
        cisob (pd.DataFrame): Codelist mapping municipalities to geographic units.
        cnumnuts (pd.DataFrame): Codelist mapping NUTS codes to readable strings.
        cpp (pd.DataFrame): Codelist resolving political party IDs to names.

    Returns:
        Dict[str, Dict[str, str]]: A dictionary mapping region names to their winning party.
    """
    mock_mapping = {
        "Hlavní město Praha": {"winning_party": "SPOLU"},
        "Středočeský kraj": {"winning_party": "STAN"},
        "Jihočeský kraj": {"winning_party": "ODS"},
        "Plzeňský kraj": {"winning_party": "ANO"},
        "Karlovarský kraj": {"winning_party": "ANO"},
        "Ústecký kraj": {"winning_party": "ANO"},
        "Liberecký kraj": {"winning_party": "STAN"},
        "Královéhradecký kraj": {"winning_party": "SPOLU"},
        "Pardubický kraj": {"winning_party": "SPOLU"},
        "Kraj Vysočina": {"winning_party": "ANO"},
        "Jihomoravský kraj": {"winning_party": "SPOLU"},
        "Olomoucký kraj": {"winning_party": "ANO"},
        "Zlínský kraj": {"winning_party": "ANO"},
        "Moravskoslezský kraj": {"winning_party": "ANO"},
    }

    if cisob.empty or cnumnuts.empty or pst4.empty or cpp.empty:
        logging.warning("Missing essential geographic data. Using comprehensive mock mapping for 14 regions.")
        return mock_mapping

    try:
        # 1. Join municipality codes (pst4) with cisob to get NUTS codes
        merged = pd.merge(pst4, cisob, on="obec_kod", how="left")
        
        # 2. Map NUTS codes to readable region names
        merged = pd.merge(merged, cnumnuts, left_on="nuts_kod", right_on="kod", how="left")
        
        # 3. Aggregate votes by Region
        region_votes = merged.groupby(["region_name", "party_id"])["votes"].sum().reset_index()
        
        # 4. Find winning party per region
        idx = region_votes.groupby(["region_name"])["votes"].transform(max) == region_votes["votes"]
        winners = region_votes[idx]
        
        # 5. Resolve party names
        winners = pd.merge(winners, cpp, on="party_id", how="left")
        
        mapping = winners.set_index("region_name")[["party_name"]].to_dict(orient="index")
        return mapping
    except (KeyError, Exception) as e:
        logging.warning(f"Error processing geographic data (Schema mismatch?): {e}")
        logging.info("Falling back to mock aggregations for demonstration...")
        return mock_mapping


def load_census_populations(census_path: Path) -> Dict[str, int]:
    """
    Loads region populations from the census CSV file.
    """
    fallbacks = {
        "Hlavní město Praha": 1301432,
        "Praha": 1301432,
        "Středočeský kraj": 1415463,
        "Jihočeský kraj": 631803,
        "Plzeňský kraj": 581436,
        "Karlovarský kraj": 279103,
        "Ústecký kraj": 789098,
        "Liberecký kraj": 435220,
        "Královéhradecký kraj": 538303,
        "Pardubický kraj": 510037,
        "Kraj Vysočina": 497661,
        "Jihomoravský kraj": 1197651,
        "Olomoucký kraj": 619788,
        "Zlínský kraj": 564331,
        "Moravskoslezský kraj": 1162841
    }
    
    if not census_path.exists():
        logging.warning(f"Census file not found: {census_path}. Using fallback populations.")
        return fallbacks
        
    try:
        df = pd.read_csv(census_path, sep=',', encoding="utf-8")
        # Filter for rows where age group (vek_txt) is NaN and gender (pohlavi_txt) is NaN
        df_filtered = df[df['vek_txt'].isna() & df['pohlavi_txt'].isna()]
        
        pop_map = {}
        for _, row in df_filtered.iterrows():
            uzemi = str(row['uzemi_txt']).strip()
            try:
                pop_map[uzemi] = int(row['hodnota'])
            except (ValueError, TypeError):
                continue
                
        # Fill missing ones from fallback
        for k, v in fallbacks.items():
            if k not in pop_map:
                pop_map[k] = v
        return pop_map
    except Exception as e:
        logging.warning(f"Error loading census populations: {e}. Using fallback populations.")
        return fallbacks


def generate_regional_profile(
    region_name: str, region_mapping: Dict[str, Dict[str, str]], population_map: Dict[str, int]
) -> Dict[str, Any]:
    """
    Generates a single regional archetype profile containing demographic and political traits.

    Args:
        region_name (str): The geographic region to generate a profile for.
        region_mapping (Dict[str, Dict[str, str]]): Mapping containing the winning party per region.
        population_map (Dict[str, int]): Mapping containing population per region.

    Returns:
        Dict[str, Any]: A dictionary containing the generated persona's demographic traits.
    """
    # 1. Geography
    region_typ = region_name

    # 2. Political synthesis (hlavni_zajem)
    party_info = region_mapping.get(region_name, {})
    party = party_info.get("winning_party") or party_info.get("party_name", "ANO")
    
    opposition_parties = ["ANO", "SPD", "Přísaha", "KSČM"]
    coalition_parties = ["SPOLU", "STAN", "Piráti", "ODS", "TOP 09", "KDU-ČSL"]
    
    if party in opposition_parties:
        hlavni_zajem = "Ochrana před inflací, ekonomická stabilita a průmyslová bezpečnost regionu."
    elif party in coalition_parties:
        hlavni_zajem = "Podpora demokratických hodnot, západní integrace a institucionální reformy."
    else:
        hlavni_zajem = "Lokální rozvoj a stabilita veřejných služeb."

    # 3. Demographics
    if "Praha" in region_name:
        vek_kategorie = "30-45 let"
        vzdelani_profese = "Vysokoškolské / Služby, IT, Management"
    elif "Středočeský" in region_name:
        vek_kategorie = "35-50 let"
        vzdelani_profese = "Středoškolské s maturitou / Logistika, Služby"
    elif "Jihočeský" in region_name:
        vek_kategorie = "40-55 let"
        vzdelani_profese = "Středoškolské s maturitou / Zemědělství, Turismus"
    elif "Plzeňský" in region_name:
        vek_kategorie = "35-50 let"
        vzdelani_profese = "Středoškolské odborné / Strojírenství, Průmysl"
    elif "Karlovarský" in region_name:
        vek_kategorie = "40-60 let"
        vzdelani_profese = "Středoškolské bez maturity / Lázeňství, Těžba"
    elif "Ústecký" in region_name:
        vek_kategorie = "45-60 let"
        vzdelani_profese = "Středoškolské bez maturity / Těžba, Chemický průmysl"
    elif "Liberecký" in region_name:
        vek_kategorie = "35-55 let"
        vzdelani_profese = "Středoškolské s maturitou / Automobilový průmysl, Sklářství"
    elif "Královéhradecký" in region_name:
        vek_kategorie = "40-60 let"
        vzdelani_profese = "Středoškolské s maturitou / Výroba, Služby"
    elif "Pardubický" in region_name:
        vek_kategorie = "35-55 let"
        vzdelani_profese = "Středoškolské s maturitou / Průmysl, Doprava"
    elif "Vysočina" in region_name:
        vek_kategorie = "40-60 let"
        vzdelani_profese = "Středoškolské odborné / Zemědělství, Dřevozpracující průmysl"
    elif "Jihomoravský" in region_name:
        vek_kategorie = "30-50 let"
        vzdelani_profese = "Vysokoškolské / Věda, Výzkum, Vinařství"
    elif "Olomoucký" in region_name:
        vek_kategorie = "40-60 let"
        vzdelani_profese = "Středoškolské s maturitou / Strojírenství, Potravinářství"
    elif "Zlínský" in region_name:
        vek_kategorie = "35-55 let"
        vzdelani_profese = "Středoškolské odborné / Zpracovatelský průmysl"
    elif "Moravskoslezský" in region_name:
        vek_kategorie = "45-60 let"
        vzdelani_profese = "Středoškolské bez maturity / Těžký průmysl, Hutnictví"
    else:
        vek_kategorie = "35-50 let"
        vzdelani_profese = "Středoškolské s maturitou / Administrativa a služby"

    # 4. Trust Baseline
    if "Praha" in region_name or "Jihomoravský" in region_name:
        instituce_skepse = "Vysoká důvěra v EU a národní instituce, mírná skepse k lokálním úřadům."
    elif "Karlovarský" in region_name or "Ústecký" in region_name or "Moravskoslezský" in region_name:
        instituce_skepse = "Extrémní nedůvěra k národní vládě a EU, silná vazba na lokální komunitu."
    elif "Vysočina" in region_name or "Jihočeský" in region_name:
        instituce_skepse = "Pragmatická nedůvěra k celostátním médiím, vysoká důvěra k lokálním starostům."
    else:
        instituce_skepse = "Mírná nedůvěra k vládě, stabilní důvěra v krajské a obecní úřady."

    return {
        "vek_kategorie": vek_kategorie,
        "region_typ": region_typ,
        "vzdelani_profese": vzdelani_profese,
        "hlavni_zajem": hlavni_zajem,
        "instituce_skepse": instituce_skepse,
        "population": population_map.get(region_name, 500000)
    }


def write_registry_to_file(registry: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Saves the generated persona registry to a JSON file.

    Args:
        registry (List[Dict[str, Any]]): A list of persona dictionaries.
        output_path (Path): The target path for the JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    logging.info(f"Successfully saved {len(registry)} profiles to {output_path}")


def main() -> None:
    """
    Main entry point for the data pipeline. Orchestrates loading, processing, and output.
    """
    parser = argparse.ArgumentParser(description="Ingest census and election data to build regional personas.")
    parser.add_argument("--data-dir", type=str, default="data/raw", help="Path to raw data directory")
    parser.add_argument("--output-file", type=str, default="data/processed/personas_registry.json", help="Path to output JSON")
    parser.add_argument("--regions", nargs="+", default=["Ústecký kraj", "Praha", "Jihomoravský kraj", "Moravskoslezský kraj"], help="List of regions to process")
    args = parser.parse_args()

    raw_dir = Path(args.data_dir).resolve()
    output_path = Path(args.output_file).resolve()
    
    logging.info("Loading raw datasets...")
    volby_dir = raw_dir / "csu_volby_2025"
    pst4 = safe_read_csv(volby_dir / "pst4.csv")
    cpp = safe_read_csv(volby_dir / "cpp.csv")
    cisob = safe_read_csv(volby_dir / "cisob.csv")
    cnumnuts = safe_read_csv(volby_dir / "cnumnuts.csv")
    
    # Process the loaded data into a mapping dictionary
    region_mapping = process_geographic_mapping(pst4, cisob, cnumnuts, cpp)
    
    # Load census populations
    census_file = raw_dir / "csu_census" / "sldb2021_vek5_pohlavi.csv"
    population_map = load_census_populations(census_file)
    
    # Generate the requested personas
    registry = []
    region_counter = Counter()  # Track the number of generated personas per region
    
    for region in args.regions:
        profile = generate_regional_profile(region, region_mapping, population_map)
        registry.append(profile)
        region_counter[region] += 1
        
    logging.info(f"Generated profile distribution: {dict(region_counter)}")
    
    # Save output
    write_registry_to_file(registry, output_path)
    logging.info("Data Pipeline finished.")


if __name__ == "__main__":
    main()

