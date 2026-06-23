import argparse
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_bucket_5y_str(age_int: int) -> str:
    """
    Map an exact age integer to a 5-year bracket string matching the census format.
    
    Args:
        age_int: The exact age of the individual.
        
    Returns:
        The string representing the 5-year bucket (e.g., '25 - 29 let').
    """
    if age_int < 5:
        return "0 - 4 roky"
    elif age_int < 10:
        return "5 - 9 let"
    elif age_int < 15:
        return "10 - 14 let"
    elif age_int < 20:
        return "15 - 19 let"
    elif age_int < 25:
        return "20 - 24 let"
    elif age_int < 30:
        return "25 - 29 let"
    elif age_int < 35:
        return "30 - 34 let"
    elif age_int < 40:
        return "35 - 39 let"
    elif age_int < 45:
        return "40 - 44 let"
    elif age_int < 50:
        return "45 - 49 let"
    elif age_int < 55:
        return "50 - 54 let"
    elif age_int < 60:
        return "55 - 59 let"
    elif age_int < 65:
        return "60 - 64 let"
    elif age_int < 70:
        return "65 - 69 let"
    elif age_int < 75:
        return "70 - 74 let"
    elif age_int < 80:
        return "75 - 79 let"
    elif age_int < 85:
        return "80 - 84 let"
    elif age_int < 90:
        return "85 - 89 let"
    elif age_int < 95:
        return "90 - 94 let"
    elif age_int < 100:
        return "95 - 99 let"
    else:
        return "100 a více let"


def get_bucket_act_str(age_int: int) -> str:
    """
    Map an exact age integer to an economic activity bracket matching census format.
    
    Args:
        age_int: The exact age.
        
    Returns:
        The string representing the activity age bracket.
    """
    if age_int <= 14:
        return "0 - 14 let"
    elif 15 <= age_int <= 64:
        return "15 - 64 let"
    else:
        return "65 a více let"


def parse_exact_age(vek_str: Any) -> Optional[int]:
    """
    Parse the exact integer age from a census age string.
    
    Args:
        vek_str: The age string from the CSV.
        
    Returns:
        The extracted integer age, or None if it cannot be parsed.
    """
    if "více" in str(vek_str):
        return 100
    try:
        nums = re.findall(r'\d+', str(vek_str))
        if nums:
            return int(nums[0])
    except Exception as e:
        logging.debug(f"Failed to parse age from {vek_str}: {e}")
    return None


def precompute_distributions(raw_dir: Path, output_file: Path) -> None:
    """
    Parse census CSV datasets and build a hierarchical probability tree.
    
    Args:
        raw_dir: The directory containing the raw census CSV files.
        output_file: The path to save the precomputed JSON output.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.info("Loading CSVs...")
    df_edu = pd.read_csv(raw_dir / "sldb2021_vzdelani_vek_pohlavi.csv", 
                         usecols=['hodnota', 'uzemi_txt', 'vek_txt', 'pohlavi_txt', 'vzdelani_txt'], 
                         sep=',', encoding="utf-8")
    df_vira = pd.read_csv(raw_dir / "sldb2021_vira_vek_pohlavi.csv", 
                          usecols=['hodnota', 'uzemi_txt', 'vek_txt', 'pohlavi_txt', 'vira_txt'], 
                          sep=',', encoding="utf-8")
    df_act = pd.read_csv(raw_dir / "sldb2021_aktivita_vek_pohlavi.csv", 
                         usecols=['hodnota', 'uzemi_txt', 'vek_txt', 'pohlavi_txt', 'aktivita_txt'], 
                         sep=',', encoding="utf-8")
    
    regions = [
        "Hlavní město Praha", "Středočeský kraj", "Jihočeský kraj", "Plzeňský kraj",
        "Karlovarský kraj", "Ústecký kraj", "Liberecký kraj", "Královéhradecký kraj",
        "Pardubický kraj", "Kraj Vysočina", "Jihomoravský kraj", "Olomoucký kraj",
        "Zlínský kraj", "Moravskoslezský kraj"
    ]
    
    genders = ["muž", "žena"]
    
    df_edu = df_edu[df_edu['uzemi_txt'].isin(regions) & df_edu['pohlavi_txt'].isin(genders)].dropna(subset=['vzdelani_txt'])
    df_vira = df_vira[df_vira['uzemi_txt'].isin(regions) & df_vira['pohlavi_txt'].isin(genders)].dropna(subset=['vira_txt'])
    df_act = df_act[df_act['uzemi_txt'].isin(regions) & df_act['pohlavi_txt'].isin(genders)].dropna(subset=['aktivita_txt'])
    
    top_level_vira = ['Bez náboženské víry', 'Věřící', 'Neuvedeno']
    df_vira = df_vira[df_vira['vira_txt'].isin(top_level_vira)]
    
    tree: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
    
    logging.info("Building Age and Education distribution...")
    edu_grouped = df_edu.groupby(['uzemi_txt', 'pohlavi_txt', 'vek_txt'])
    
    for (region, gender, age_str), group in edu_grouped:
        age_int = parse_exact_age(age_str)
        if age_int is None or age_int < 15:
            continue
            
        if region not in tree:
            tree[region] = {}
        if gender not in tree[region]:
            tree[region][gender] = {}
            
        age_str_mapped = str(age_int)
        if age_str_mapped not in tree[region][gender]:
            tree[region][gender][age_str_mapped] = {
                "age_weight": 0,
                "education": {},
                "religion": {},
                "activity": {}
            }
            
        edu_dict = group.groupby('vzdelani_txt')['hodnota'].sum().to_dict()
        total_age_weight = sum(edu_dict.values())
        
        tree[region][gender][age_str_mapped]["age_weight"] = total_age_weight
        tree[region][gender][age_str_mapped]["education"] = edu_dict
        
    logging.info("Injecting Religion distributions...")
    vira_dict = df_vira.groupby(['uzemi_txt', 'pohlavi_txt', 'vek_txt', 'vira_txt'])['hodnota'].sum().to_dict()
    
    def get_vira(r: str, g: str, a_int: int) -> Dict[str, int]:
        bucket = get_bucket_5y_str(a_int)
        res = {}
        for k in top_level_vira:
            val = vira_dict.get((r, g, bucket, k), 0)
            if val > 0:
                res[k] = val
        return res
        
    logging.info("Injecting Activity distributions...")
    act_dict = df_act.groupby(['uzemi_txt', 'pohlavi_txt', 'vek_txt', 'aktivita_txt'])['hodnota'].sum().to_dict()
    unique_acts = df_act['aktivita_txt'].unique()
    
    def get_act(r: str, g: str, a_int: int) -> Dict[str, int]:
        bucket = get_bucket_act_str(a_int)
        res = {}
        for k in unique_acts:
            val = act_dict.get((r, g, bucket, k), 0)
            if val > 0:
                res[k] = val
        return res

    for r in tree:
        for g in tree[r]:
            for age_s in tree[r][g]:
                age_integer = int(age_s)
                tree[r][g][age_s]["religion"] = get_vira(r, g, age_integer)
                tree[r][g][age_s]["activity"] = get_act(r, g, age_integer)
                
    logging.info("Saving to JSON...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    
    logging.info("Done!")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Precompute demographic probabilities.")
    parser.add_argument("--raw-dir", type=str, default="data/raw/csu_census", help="Path to raw census data")
    parser.add_argument("--output", type=str, default="data/processed/demographic_distributions.json", help="Path to save output JSON")
    args = parser.parse_args()
    
    raw_path = Path(args.raw_dir)
    out_path = Path(args.output)
    precompute_distributions(raw_path, out_path)


if __name__ == "__main__":
    main()
