import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = ROOT / "skills" / "claude-skill-porter" / "scripts" / "convert_claude_skill.py"
FIXTURES_ROOT = ROOT / "tests" / "fixtures"
GOLDEN_ROOT = ROOT / "tests" / "golden"

SPEC = importlib.util.spec_from_file_location("claude_skill_porter_convert", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sanitize_report(text: str) -> str:
    cleaned_lines = []

    for line in text.splitlines():
        if line.startswith("- Source path:"):
            continue
        if line.startswith("- Generated on:"):
            continue
        if line.startswith("- Output path:"):
            continue
        if line.startswith("- Source root:"):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def sanitize_manifest(text: str) -> dict:
    data = json.loads(text)
    for key in ("source_path", "output_path", "generated_on", "source_root", "output_root"):
        data.pop(key, None)

    for item in data.get("items", []):
        item.pop("source_path", None)
        item.pop("output_path", None)

    return data


class ConvertClaudeSkillFixtureTests(unittest.TestCase):
    def compare_single_output_to_golden(self, output_dir: Path, golden_dir: Path) -> None:
        self.assertEqual(
            (output_dir / "SKILL.md").read_text(encoding="utf-8"),
            (golden_dir / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (output_dir / "agents" / "openai.yaml").read_text(encoding="utf-8"),
            (golden_dir / "agents" / "openai.yaml").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (output_dir / "references" / "original-frontmatter.md").read_text(encoding="utf-8"),
            (golden_dir / "references" / "original-frontmatter.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            sanitize_report((output_dir / "references" / "migration-report.md").read_text(encoding="utf-8")),
            sanitize_report((golden_dir / "references" / "migration-report.md").read_text(encoding="utf-8")),
        )
        self.assertEqual(
            sanitize_manifest((output_dir / "references" / "migration-manifest.json").read_text(encoding="utf-8")),
            sanitize_manifest((golden_dir / "references" / "migration-manifest.json").read_text(encoding="utf-8")),
        )

    def run_single_conversion_and_compare(self, source: Path, expected_skill_name: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "out"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(source), str(output_root)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.compare_single_output_to_golden(
                output_root / expected_skill_name,
                GOLDEN_ROOT / expected_skill_name,
            )

    def test_basic_skill_matches_golden(self) -> None:
        self.run_single_conversion_and_compare(
            FIXTURES_ROOT / "basic-skill",
            "basic-skill",
        )

    def test_legacy_command_matches_golden(self) -> None:
        self.run_single_conversion_and_compare(
            FIXTURES_ROOT / "legacy-command" / "deploy.md",
            "deploy",
        )

    def test_context_fork_matches_golden(self) -> None:
        self.run_single_conversion_and_compare(
            FIXTURES_ROOT / "context-fork",
            "context-fork",
        )

    def test_hooks_skill_matches_golden(self) -> None:
        self.run_single_conversion_and_compare(
            FIXTURES_ROOT / "hooks-skill",
            "hooks-skill",
        )

    def test_claude_vars_matches_golden(self) -> None:
        self.run_single_conversion_and_compare(
            FIXTURES_ROOT / "claude-vars",
            "claude-vars",
        )

    def test_mixed_rewrite_matches_golden(self) -> None:
        self.run_single_conversion_and_compare(
            FIXTURES_ROOT / "mixed-rewrite",
            "mixed-rewrite",
        )

    def test_batch_mode_builds_repo_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_root = tmp_path / "repo"
            skills_root = repo_root / ".claude" / "skills"
            commands_root = repo_root / ".claude" / "commands"

            shutil.copytree(FIXTURES_ROOT / "basic-skill", skills_root / "basic-skill")
            shutil.copytree(FIXTURES_ROOT / "context-fork", skills_root / "context-fork")
            commands_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FIXTURES_ROOT / "legacy-command" / "deploy.md", commands_root / "deploy.md")

            output_root = tmp_path / "batch-out"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(repo_root), str(output_root), "--batch"],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            manifest = sanitize_manifest((output_root / "batch-migration-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["items_total"], 3)
            self.assertEqual(manifest["items_manual_follow_up_required"], 1)
            self.assertTrue((output_root / "basic-skill" / "SKILL.md").exists())
            self.assertTrue((output_root / "context-fork" / "SKILL.md").exists())
            self.assertTrue((output_root / "deploy" / "SKILL.md").exists())

    def test_batch_strict_fails_when_any_item_needs_manual_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_root = tmp_path / "repo"
            skills_root = repo_root / ".claude" / "skills"
            commands_root = repo_root / ".claude" / "commands"

            shutil.copytree(FIXTURES_ROOT / "basic-skill", skills_root / "basic-skill")
            shutil.copytree(FIXTURES_ROOT / "context-fork", skills_root / "context-fork")
            commands_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FIXTURES_ROOT / "legacy-command" / "deploy.md", commands_root / "deploy.md")

            output_root = tmp_path / "batch-out"
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(repo_root), str(output_root), "--batch", "--strict"],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 2)
            self.assertIn("Strict mode failed", proc.stderr)


if __name__ == "__main__":
    unittest.main()
