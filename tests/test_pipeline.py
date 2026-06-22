import pandas as pd
from pathlib import Path
from data_pipeline import process_geographic_mapping, generate_regional_profile

def test_process_geographic_mapping_empty():
    """Test that the geographic mapping safely falls back to mocks if data is empty."""
    empty_df = pd.DataFrame()
    result = process_geographic_mapping(empty_df, empty_df, empty_df, empty_df)
    
    assert "Praha" in result
    assert result["Praha"]["winning_party"] == "SPOLU"


def test_generate_regional_profile_opposition():
    """Test that a region won by an opposition party correctly assigns an inflation-focused interest."""
    mock_mapping = {
        "Ústecký kraj": {"winning_party": "ANO"}
    }
    
    profile = generate_regional_profile("Ústecký kraj", mock_mapping)
    
    assert profile["region_typ"] == "Ústecký kraj"
    assert "inflac" in profile["hlavni_zajem"].lower()
    assert "Středoškolské" in profile["vzdelani_profese"]


def test_generate_regional_profile_coalition():
    """Test that a region won by a coalition party correctly assigns a democracy-focused interest."""
    mock_mapping = {
        "Praha": {"winning_party": "SPOLU"}
    }
    
    profile = generate_regional_profile("Praha", mock_mapping)
    
    assert profile["region_typ"] == "Praha"
    assert "demokratických" in profile["hlavni_zajem"].lower()
    assert "Vysokoškolské" in profile["vzdelani_profese"]
