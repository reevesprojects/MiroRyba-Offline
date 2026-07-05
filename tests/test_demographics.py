import unittest
import json
import tempfile
from pathlib import Path
from neo4j_importer import PrecomputedSampler

class TestPrecomputedSampler(unittest.TestCase):
    def setUp(self):
        self.mock_data = {
            "Hlavní město Praha": {
                "muž": {
                    "30": {
                        "age_weight": 100,
                        "education": {"Vysokoškolské": 10},
                        "religion": {"Bez vyznání": 5},
                        "activity": {"Zaměstnaní": 20}
                    }
                }
            }
        }
        
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(self.mock_data, self.temp_file)
        self.temp_file.close()
        
        self.sampler = PrecomputedSampler(Path(self.temp_file.name))

    def tearDown(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_sample_gender(self):
        # Only 'muž' exists in the mock data for Praha
        gender = self.sampler.sample_gender("Hlavní město Praha")
        self.assertEqual(gender, "male")

    def test_sample_age(self):
        # Only age 30 exists
        age = self.sampler.sample_age("Hlavní město Praha", "male")
        self.assertEqual(age, 30)

    def test_sample_traits(self):
        religion, education, activity = self.sampler.sample_traits("Hlavní město Praha", "male", 30)
        self.assertEqual(religion, "Bez vyznání")
        self.assertEqual(education, "Vysokoškolské")
        self.assertEqual(activity, "Zaměstnaní")

    def test_fallback_unknown_region(self):
        # Should gracefully fall back to random choices if region is missing
        gender = self.sampler.sample_gender("Neznámý kraj")
        self.assertIn(gender, ["male", "female"])
        
        age = self.sampler.sample_age("Neznámý kraj", "female")
        self.assertTrue(18 <= age <= 65)

if __name__ == '__main__':
    unittest.main()
