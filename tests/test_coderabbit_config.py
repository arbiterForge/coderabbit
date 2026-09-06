import json
from pathlib import Path
import unittest

from ruamel.yaml import YAML

from tests.schema_snapshot import schema_bytes


REPO_ROOT = Path(__file__).resolve().parents[1]
class CodeRabbitConfigRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(schema_bytes())

    def test_live_config_respects_authoritative_tone_limit(self):
        fixture = YAML(typ="safe").load(
            (REPO_ROOT / "tests/fixtures/tone-instructions-426.yaml").read_text(
                encoding="utf-8"
            )
        )
        live_config = YAML(typ="safe").load(
            (REPO_ROOT / ".coderabbit.yaml").read_text(encoding="utf-8")
        )
        maximum = self.schema["properties"]["tone_instructions"]["maxLength"]

        self.assertEqual(len(fixture["tone_instructions"]), 426)
        self.assertEqual(maximum, 250)
        self.assertLessEqual(
            len(live_config["tone_instructions"]),
            maximum,
            "tone_instructions is "
            f"{len(live_config['tone_instructions'])} characters; "
            f"authoritative schema maxLength is {maximum}",
        )


if __name__ == "__main__":
    unittest.main()
