import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "validate_catalog.py"
spec = importlib.util.spec_from_file_location("validate_catalog", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)

DIGEST = "a" * 64


def raw_doc():
    return {
        "schema_version": 1,
        "source": {
            "id": "CED_C_P1000",
            "file": "C_p1000.pdf",
            "sha256": DIGEST,
            "title": "P1000 channel",
            "pages_used": [1, 2],
        },
        "extraction": {
            "method": "manual transcription",
            "status": "reviewed",
            "records": [{"id": "P1000", "page": 1}],
        },
    }


def profiles_doc():
    return {
        "schema_version": 1,
        "profiles": [
            {
                "id": "P1000",
                "family": "1-5/8 x 1-5/8",
                "gauge": 12,
                "geometry": {
                    "width": {"in": 1.625, "mm": 41.3},
                    "height": {"in": 1.625, "mm": 41.3},
                    "thickness": {"in": 0.105, "mm": 2.7},
                    "piercing": {"series": None, "template": None, "overrides": {}},
                    "profile_spec": {
                        "kind": "u_channel_lipped",
                        "t": {"in": 0.105, "mm": 2.7},
                        "lip_return": {"in": 0.375, "mm": 9.5},
                    },
                },
                "finishes": ["PL", "GR"],
                "standard_lengths": {"ft": [10.0, 20.0], "m": [3.05, 6.1]},
                "provenance": {
                    "source_id": "CED_C_P1000",
                    "source_file": "C_p1000.pdf",
                    "source_sha256": DIGEST,
                    "source_pages": [1, 2],
                },
            }
        ],
    }


class CatalogValidatorTests(unittest.TestCase):
    def write_catalog(self, root, profiles=None, raw=None):
        data = Path(root) / "Mod" / "UnistrutWB" / "data"
        (data / "raw" / "ced").mkdir(parents=True)
        (data / "profiles.json").write_text(json.dumps(profiles or profiles_doc()), encoding="utf-8")
        if raw is not False:
            (data / "raw" / "ced" / "P1000.json").write_text(json.dumps(raw or raw_doc()), encoding="utf-8")
        return data

    def test_valid_catalog_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.write_catalog(temp)
            findings = module.Validator(data).validate()
            self.assertEqual([], [f for f in findings if f.level == "error"])

    def test_missing_geometry_field_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            profiles = profiles_doc()
            del profiles["profiles"][0]["geometry"]["thickness"]
            data = self.write_catalog(temp, profiles=profiles)
            findings = module.Validator(data).validate()
            self.assertTrue(any("geometry.thickness" in f.path for f in findings if f.level == "error"))

    def test_duplicate_profile_id_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            profiles = profiles_doc()
            profiles["profiles"].append(dict(profiles["profiles"][0]))
            data = self.write_catalog(temp, profiles=profiles)
            findings = module.Validator(data).validate()
            self.assertTrue(any("duplicate id 'P1000'" in f.message for f in findings))

    def test_missing_raw_provenance_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.write_catalog(temp, raw=False)
            findings = module.Validator(data).validate()
            self.assertTrue(any("missing raw source" in f.message for f in findings))

    def test_unit_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            profiles = profiles_doc()
            profiles["profiles"][0]["geometry"]["width"]["mm"] = 99.0
            data = self.write_catalog(temp, profiles=profiles)
            findings = module.Validator(data).validate()
            self.assertTrue(any("unit mismatch" in f.message for f in findings))


if __name__ == "__main__":
    unittest.main()
