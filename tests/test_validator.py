from contextlib import redirect_stderr
import importlib.util
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from tests.schema_snapshot import schema_bytes, schema_path as shared_schema_path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts/validate_coderabbit.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_coderabbit", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CodeRabbitValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema_path = shared_schema_path()

    def validate(self, config: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--schema-file",
                str(self.schema_path),
                str(config),
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def validate_text(self, config: str) -> subprocess.CompletedProcess[str]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", encoding="utf-8", delete=False
        ) as config_file:
            config_file.write(config)
            config_path = Path(config_file.name)
        try:
            return self.validate(config_path)
        finally:
            config_path.unlink(missing_ok=True)

    def test_rejects_preserved_426_character_folded_value(self):
        result = self.validate(
            REPO_ROOT / "tests/fixtures/tone-instructions-426.yaml"
        )
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 1, output)
        self.assertIn("tone_instructions", output)
        self.assertIn("is too long", output)

    def test_accepts_live_config(self):
        result = self.validate(REPO_ROOT / ".coderabbit.yaml")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_enforces_full_schema_outside_tone_instructions(self):
        result = self.validate_text("reviews:\n  profile: definitely-invalid\n")
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 1, output)
        self.assertIn("profile", output)
        self.assertIn("is not one of", output)

    def test_enforces_exact_tone_instruction_boundary(self):
        at_limit = self.validate_text(f"tone_instructions: {'x' * 250}\n")
        over_limit = self.validate_text(f"tone_instructions: {'x' * 251}\n")
        over_output = over_limit.stdout + over_limit.stderr

        self.assertEqual(at_limit.returncode, 0, at_limit.stdout + at_limit.stderr)
        self.assertEqual(over_limit.returncode, 1, over_output)
        self.assertIn("is too long", over_output)

    def test_rejects_non_finite_numbers_before_schema_validation(self):
        result = self.validate_text(
            "reviews:\n"
            "  pre_merge_checks:\n"
            "    docstrings:\n"
            "      threshold: .nan\n"
        )
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 1, output)
        self.assertIn("non-finite number", output)

    def test_schema_retrieval_failure_is_nonzero(self):
        validator = load_validator_module()
        stderr = StringIO()

        with (
            patch.object(
                validator.requests,
                "get",
                side_effect=validator.requests.ConnectionError("offline"),
            ),
            patch.object(sys, "argv", [str(VALIDATOR), str(REPO_ROOT / ".coderabbit.yaml")]),
            redirect_stderr(stderr),
        ):
            result = validator.main()

        self.assertEqual(result, 2)
        self.assertIn("could not retrieve authoritative schema", stderr.getvalue())

    def test_schema_digest_failure_is_nonzero(self):
        validator = load_validator_module()
        stderr = StringIO()
        response = Mock()
        response.content = schema_bytes()

        with (
            patch.object(validator, "SCHEMA_SHA256", "0" * 64),
            patch.object(validator.requests, "get", return_value=response),
            patch.object(sys, "argv", [str(VALIDATOR), str(REPO_ROOT / ".coderabbit.yaml")]),
            redirect_stderr(stderr),
        ):
            result = validator.main()

        self.assertEqual(result, 2)
        self.assertIn("authoritative schema SHA256 changed", stderr.getvalue())

    def test_supplied_schema_digest_failure_is_nonzero(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as schema_file:
            schema_file.write(b"{}")
            schema_path = Path(schema_file.name)
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--schema-file",
                    str(schema_path),
                    str(REPO_ROOT / ".coderabbit.yaml"),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            schema_path.unlink(missing_ok=True)

        self.assertEqual(result.returncode, 2)
        self.assertIn("authoritative schema SHA256 changed", result.stderr)


if __name__ == "__main__":
    unittest.main()
