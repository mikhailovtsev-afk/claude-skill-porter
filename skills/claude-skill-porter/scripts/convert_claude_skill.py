#!/usr/bin/env python3
"""Convert Claude Code skills or commands into Codex-ready skills.

The converter is intentionally conservative:
- portable parts are copied automatically
- common low-risk Claude patterns are rewritten into plain Codex instructions
- unsupported behavior is preserved in reports instead of being hidden
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


SUPPORTED_FRONTMATTER_KEYS = ("name", "description", "argument-hint", "allowed-tools")
UNSUPPORTED_FRONTMATTER_REASONS = {
    "disable-model-invocation": "Codex does not expose a confirmed equivalent auto-invocation gate in this project.",
    "user-invocable": "Codex does not expose a confirmed menu visibility flag in this project.",
    "context": "Claude can run a skill inside a forked context. Treat as manual redesign in Codex.",
    "agent": "Claude can bind a skill to a subagent type. Treat as manual redesign in Codex.",
    "hooks": "Claude skill lifecycle hooks do not have a confirmed Codex skill equivalent here.",
    "paths": "Claude can path-scope activation. Treat as manual logic in Codex.",
    "model": "Claude can override the model per skill. Do not assume Codex parity.",
    "effort": "Claude can override effort per skill. Do not assume Codex parity.",
    "shell": "Claude can pick the shell for skill-time injection. Do not assume Codex parity.",
}
SIMPLE_ALLOWED_TOOL = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
ARGUMENT_INDEX_RE = re.compile(r"\$ARGUMENTS\[(\d+)\]")
ARGUMENTS_RE = re.compile(r"\$ARGUMENTS\b")
POSITIONAL_ARG_RE = re.compile(r"\$(\d+)\b")
KNOWN_CLAUDE_VARS = {
    "SKILL_DIR": "the current skill directory",
    "PROJECT_DIR": "the current project directory",
    "FILE_PATH": "the current file path",
    "CURRENT_FILE": "the current file path",
}
KNOWN_CLAUDE_VAR_RE = re.compile(
    r"\$\{CLAUDE_(" + "|".join(sorted(KNOWN_CLAUDE_VARS)) + r")\}"
)
REMAINING_CLAUDE_VAR_RE = re.compile(r"\$\{CLAUDE_[A-Z0-9_]+\}")
INLINE_SHELL_INJECTION_RE = re.compile(r"!\`([^`]+)\`")
RUN_PREFIX_INLINE_SHELL_INJECTION_RE = re.compile(r"\b([Rr]un)\s+!\`([^`]+)\`")
BLOCK_SHELL_INJECTION_RE = re.compile(r"```!\s*\n(.*?)\n```", re.DOTALL)
BODY_PATTERN_RULES = (
    (
        re.compile(r"\$ARGUMENTS(?:\[\d+\])?|\$\d+\b"),
        "Claude argument placeholders were found. Replace with plain Codex instructions or a helper script.",
    ),
    (
        REMAINING_CLAUDE_VAR_RE,
        "Claude runtime variables were found. Codex may not provide the same variables.",
    ),
    (
        INLINE_SHELL_INJECTION_RE,
        "Claude shell injection syntax was found. Convert it into an explicit step or helper script.",
    ),
    (
        BLOCK_SHELL_INJECTION_RE,
        "Claude shell-injection code blocks were found. Convert them into an explicit step or helper script.",
    ),
)


@dataclass
class SourceDocument:
    source_path: Path
    source_type: str
    raw_frontmatter: str
    frontmatter: dict[str, Any]
    body: str
    bundled_dirs: list[str]


@dataclass
class ConversionResult:
    source_path: Path
    source_type: str
    destination_dir: Path
    skill_name: str
    codex_frontmatter: dict[str, str]
    rewritten_body: str
    status: str
    portable_notes: list[str]
    rewrite_notes: list[str]
    manual_notes: list[str]
    body_findings: list[str]
    bundled_dirs: list[str]
    raw_frontmatter: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Claude Code skill, command, or repo into Codex-ready skills."
    )
    parser.add_argument(
        "source",
        help="Path to a Claude skill directory, a legacy .claude/commands/*.md file, or a repo root when --batch is used.",
    )
    parser.add_argument(
        "output_root",
        help="Directory where the migrated skill folder or batch output should be created.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing destination skill directory or batch output.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with a non-zero status if manual follow-up or Claude-only findings are detected.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Scan a repo or .claude directory and migrate every skill and legacy command found.",
    )
    return parser.parse_args()


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        return "", text

    return match.group(1).strip(), match.group(2).lstrip("\n")


def parse_simple_frontmatter(raw_frontmatter: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    active_list_key: str | None = None

    for raw_line in raw_frontmatter.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        list_item = re.match(r"^\s*-\s+(.*)$", line)
        if list_item and active_list_key:
            data.setdefault(active_list_key, []).append(strip_quotes(list_item.group(1).strip()))
            continue

        key_only = re.match(r"^([A-Za-z0-9_-]+):\s*$", line)
        if key_only:
            active_list_key = key_only.group(1)
            data[active_list_key] = []
            continue

        key_value = re.match(r"^([A-Za-z0-9_-]+):\s*(.+)$", line)
        if key_value:
            active_list_key = None
            key = key_value.group(1)
            value = strip_quotes(key_value.group(2).strip())
            if value.lower() == "true":
                data[key] = True
            elif value.lower() == "false":
                data[key] = False
            else:
                data[key] = value

    return data


def parse_frontmatter(raw_frontmatter: str) -> dict[str, Any]:
    if not raw_frontmatter.strip():
        return {}

    if yaml is not None:
        parsed = yaml.safe_load(raw_frontmatter)
        if isinstance(parsed, dict):
            return parsed

    return parse_simple_frontmatter(raw_frontmatter)


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_source(source_path: Path) -> SourceDocument:
    if source_path.is_dir():
        skill_file = source_path / "SKILL.md"
        if not skill_file.exists():
            raise FileNotFoundError(f"Expected {skill_file} inside the source directory.")
        raw_text = skill_file.read_text(encoding="utf-8")
        raw_frontmatter, body = split_frontmatter(raw_text)
        bundled_dirs = [name for name in ("scripts", "references", "assets") if (source_path / name).exists()]
        return SourceDocument(
            source_path=source_path,
            source_type="skill",
            raw_frontmatter=raw_frontmatter,
            frontmatter=parse_frontmatter(raw_frontmatter),
            body=body.rstrip() + "\n",
            bundled_dirs=bundled_dirs,
        )

    if source_path.is_file():
        raw_text = source_path.read_text(encoding="utf-8")
        raw_frontmatter, body = split_frontmatter(raw_text)
        return SourceDocument(
            source_path=source_path,
            source_type="command",
            raw_frontmatter=raw_frontmatter,
            frontmatter=parse_frontmatter(raw_frontmatter),
            body=body.rstrip() + "\n",
            bundled_dirs=[],
        )

    raise FileNotFoundError(f"Source path does not exist: {source_path}")


def normalize_skill_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized or "migrated-skill"


def derive_skill_name(source: SourceDocument) -> str:
    raw_name = str(source.frontmatter.get("name") or source.source_path.stem)
    return normalize_skill_name(raw_name)


def derive_description(source: SourceDocument) -> str:
    description = source.frontmatter.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()

    first_nonempty_line = next((normalize_summary_line(line) for line in source.body.splitlines() if line.strip()), "")
    if first_nonempty_line:
        return (
            "Migrated from Claude Code. Manual review recommended because the source description was missing. "
            + first_nonempty_line[:200]
        )
    return "Migrated from Claude Code. Manual review recommended."


def normalize_summary_line(line: str) -> str:
    normalized = re.sub(r"^#+\s*", "", line.strip())
    return normalized


def classify_allowed_tools(raw_value: Any) -> tuple[str | None, str | None]:
    if raw_value is None:
        return None, None

    if isinstance(raw_value, list):
        tokens = [str(item).strip() for item in raw_value if str(item).strip()]
    elif isinstance(raw_value, str):
        if "(" in raw_value or ")" in raw_value or "*" in raw_value or ":" in raw_value:
            return None, "Complex Claude allowed-tools syntax was detected and must be reviewed manually."
        if "," in raw_value:
            tokens = [part.strip() for part in raw_value.split(",") if part.strip()]
        else:
            tokens = [part.strip() for part in raw_value.split() if part.strip()]
    else:
        return None, "The allowed-tools field uses an unsupported data type and must be reviewed manually."

    if not tokens:
        return None, None

    if not all(SIMPLE_ALLOWED_TOOL.match(token) for token in tokens):
        return None, "Only bare tool names are carried over automatically. Complex tool rules need manual review."

    return ", ".join(tokens), None


def build_codex_frontmatter(source: SourceDocument) -> tuple[dict[str, str], list[str], list[str]]:
    frontmatter: dict[str, str] = {
        "name": derive_skill_name(source),
        "description": derive_description(source),
    }
    portable_notes = ["Copied `name` and `description` into the Codex skill."]
    manual_notes: list[str] = []

    argument_hint = source.frontmatter.get("argument-hint")
    if isinstance(argument_hint, str) and argument_hint.strip():
        frontmatter["argument-hint"] = argument_hint.strip()
        portable_notes.append("Copied a simple `argument-hint` field.")

    normalized_allowed_tools, tools_warning = classify_allowed_tools(source.frontmatter.get("allowed-tools"))
    if normalized_allowed_tools:
        frontmatter["allowed-tools"] = normalized_allowed_tools
        portable_notes.append("Copied a simple `allowed-tools` list.")
    elif tools_warning:
        manual_notes.append(f"`allowed-tools`: {tools_warning}")

    for key, reason in UNSUPPORTED_FRONTMATTER_REASONS.items():
        if key in source.frontmatter:
            manual_notes.append(f"`{key}`: {reason}")

    for key in source.frontmatter:
        if key not in SUPPORTED_FRONTMATTER_KEYS and key not in UNSUPPORTED_FRONTMATTER_REASONS:
            manual_notes.append(
                f"`{key}`: This field is not part of the conservative MVP mapping and should be reviewed manually."
            )

    return frontmatter, portable_notes, manual_notes


def ordinal(index: int) -> str:
    known = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
    }
    return known.get(index, f"{index}th")


def rewrite_body(body: str) -> tuple[str, list[str]]:
    rewrite_notes: list[str] = []
    note_set: set[str] = set()

    def remember(note: str) -> None:
        if note not in note_set:
            note_set.add(note)
            rewrite_notes.append(note)

    def replace_block_shell(match: re.Match[str]) -> str:
        remember("Converted Claude shell-injection code blocks into explicit bash steps.")
        command = match.group(1).strip()
        return "Run this command and use the output before continuing:\n\n```bash\n" + command + "\n```"

    body = BLOCK_SHELL_INJECTION_RE.sub(replace_block_shell, body)

    def replace_inline_shell(match: re.Match[str]) -> str:
        remember("Converted inline Claude shell injections into explicit run instructions.")
        command = match.group(1).strip()
        return f"the result of `{command}`"

    def replace_run_prefixed_inline_shell(match: re.Match[str]) -> str:
        remember("Converted inline Claude shell injections into explicit run instructions.")
        verb = match.group(1)
        command = match.group(2).strip()
        return f"{verb} `{command}` and use the output"

    body = RUN_PREFIX_INLINE_SHELL_INJECTION_RE.sub(replace_run_prefixed_inline_shell, body)
    body = INLINE_SHELL_INJECTION_RE.sub(replace_inline_shell, body)

    def replace_indexed_arguments(match: re.Match[str]) -> str:
        remember("Rewrote indexed Claude argument placeholders into plain request-language guidance.")
        zero_based_index = int(match.group(1))
        return f"the {ordinal(zero_based_index + 1)} user-provided argument from the request"

    body = ARGUMENT_INDEX_RE.sub(replace_indexed_arguments, body)

    if ARGUMENTS_RE.search(body):
        remember("Rewrote `$ARGUMENTS` into plain request-language guidance.")
        body = ARGUMENTS_RE.sub("the user-provided arguments from the request", body)

    def replace_positional_arg(match: re.Match[str]) -> str:
        raw_index = int(match.group(1))
        remember("Rewrote Claude positional placeholders into plain request-language guidance.")
        if raw_index == 0:
            return "the original command name"
        return f"the {ordinal(raw_index)} user-provided argument from the request"

    body = POSITIONAL_ARG_RE.sub(replace_positional_arg, body)

    def replace_known_var(match: re.Match[str]) -> str:
        remember("Rewrote common Claude runtime variables into plain path guidance.")
        return KNOWN_CLAUDE_VARS[match.group(1)]

    body = KNOWN_CLAUDE_VAR_RE.sub(replace_known_var, body)
    return body, rewrite_notes


def detect_body_findings(body: str) -> list[str]:
    findings: list[str] = []
    for pattern, message in BODY_PATTERN_RULES:
        if pattern.search(body):
            findings.append(message)
    return findings


def render_frontmatter(frontmatter: dict[str, str]) -> str:
    ordered_keys = ("name", "description", "allowed-tools", "argument-hint")
    lines = ["---"]

    for key in ordered_keys:
        if key in frontmatter:
            escaped_value = frontmatter[key].replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key}: "{escaped_value}"')

    lines.append("---")
    return "\n".join(lines) + "\n\n"


def build_openai_yaml(skill_name: str, description: str) -> str:
    display_name = " ".join(part.capitalize() for part in skill_name.split("-"))
    short_description = description.split(".")[0].strip()
    if len(short_description) > 90:
        short_description = short_description[:87].rstrip() + "..."
    default_prompt = (
        f"Use the {skill_name} skill for this task, preserve any portable parts, "
        "and clearly call out manual follow-up."
    )
    return (
        "interface:\n"
        f'  display_name: "{display_name}"\n'
        f'  short_description: "{escape_yaml_string(short_description)}"\n'
        f'  default_prompt: "{escape_yaml_string(default_prompt)}"\n'
    )


def escape_yaml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def determine_status(manual_notes: list[str], body_findings: list[str]) -> str:
    if manual_notes or body_findings:
        return "manual_follow_up_required"
    return "ready_with_review"


def ensure_destination(destination_dir: Path, force: bool) -> None:
    if destination_dir.exists():
        if not force:
            raise FileExistsError(
                f"Destination already exists: {destination_dir}\n"
                "Re-run with --force if you want to overwrite files inside it."
            )
        shutil.rmtree(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)


def copy_bundled_dirs(source: SourceDocument, destination_dir: Path) -> list[str]:
    copied: list[str] = []
    if source.source_type != "skill":
        return copied

    for directory_name in source.bundled_dirs:
        source_dir = source.source_path / directory_name
        target_dir = destination_dir / directory_name
        shutil.copytree(source_dir, target_dir)
        copied.append(directory_name)
    return copied


def build_manifest(result: ConversionResult) -> dict[str, Any]:
    return {
        "source_path": str(result.source_path),
        "source_type": result.source_type,
        "generated_on": date.today().isoformat(),
        "output_path": str(result.destination_dir),
        "status": result.status,
        "portable_items_copied": len(result.portable_notes),
        "rewrite_items_applied": len(result.rewrite_notes),
        "manual_follow_up_items": len(result.manual_notes) + len(result.body_findings),
        "portable_notes": result.portable_notes,
        "rewrite_notes": result.rewrite_notes,
        "manual_notes": result.manual_notes,
        "body_findings": result.body_findings,
        "bundled_directories": result.bundled_dirs,
    }


def build_migration_report(result: ConversionResult) -> str:
    report_lines = [
        "# Migration Report",
        "",
        "## Source",
        f"- Source path: `{result.source_path}`",
        f"- Source type: `{result.source_type}`",
        f"- Generated on: `{date.today().isoformat()}`",
        f"- Output path: `{result.destination_dir}`",
        "",
        "## Verdict",
        f"- Status: `{result.status}`",
        f"- Portable items copied: `{len(result.portable_notes)}`",
        f"- Auto-rewrites applied: `{len(result.rewrite_notes)}`",
        f"- Manual follow-up items: `{len(result.manual_notes) + len(result.body_findings)}`",
        "",
        "## Copied Automatically",
    ]

    if result.portable_notes:
        report_lines.extend(f"- {note}" for note in result.portable_notes)
    else:
        report_lines.append("- No frontmatter fields were copied automatically beyond the required minimum.")

    report_lines.extend(["", "## Auto-Rewrites Applied"])
    if result.rewrite_notes:
        report_lines.extend(f"- {note}" for note in result.rewrite_notes)
    else:
        report_lines.append("- No safe auto-rewrites were applied.")

    report_lines.extend(["", "## Manual Review Required"])
    if result.manual_notes:
        report_lines.extend(f"- {note}" for note in result.manual_notes)
    else:
        report_lines.append("- No unsupported frontmatter fields were detected.")

    report_lines.extend(["", "## Remaining Claude-Specific Patterns In Body"])
    if result.body_findings:
        report_lines.extend(f"- {note}" for note in result.body_findings)
    else:
        report_lines.append("- No unresolved Claude-only placeholders or shell-injection patterns were detected.")

    report_lines.extend(["", "## Bundled Directories"])
    if result.bundled_dirs:
        report_lines.extend(f"- `{name}/` copied" for name in result.bundled_dirs)
    else:
        report_lines.append("- No bundled directories were present in the source.")

    report_lines.extend(
        [
            "",
            "## Recommended Next Steps",
            "- Read this report before trusting the migrated skill in production.",
            "- Review the rewritten body to confirm the new wording still reflects the original intent.",
            "- Rewrite any remaining Claude-only placeholders into plain Codex instructions or helper scripts.",
            "- Re-test the migrated skill on a real task and check whether the description still triggers correctly.",
        ]
    )
    return "\n".join(report_lines) + "\n"


def write_conversion_output(result: ConversionResult) -> None:
    (result.destination_dir / "references").mkdir(exist_ok=True)
    (result.destination_dir / "agents").mkdir(exist_ok=True)

    skill_contents = render_frontmatter(result.codex_frontmatter) + result.rewritten_body
    (result.destination_dir / "SKILL.md").write_text(skill_contents, encoding="utf-8")
    (result.destination_dir / "agents" / "openai.yaml").write_text(
        build_openai_yaml(result.skill_name, result.codex_frontmatter["description"]),
        encoding="utf-8",
    )
    (result.destination_dir / "references" / "original-frontmatter.md").write_text(
        "# Original Frontmatter\n\n```yaml\n"
        + (result.raw_frontmatter.strip() or "# no frontmatter found")
        + "\n```\n",
        encoding="utf-8",
    )
    (result.destination_dir / "references" / "migration-report.md").write_text(
        build_migration_report(result),
        encoding="utf-8",
    )
    (result.destination_dir / "references" / "migration-manifest.json").write_text(
        json.dumps(build_manifest(result), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def convert_source(source_path: Path, output_root: Path, force: bool) -> ConversionResult:
    source = load_source(source_path)
    skill_name = derive_skill_name(source)
    destination_dir = output_root / skill_name
    ensure_destination(destination_dir, force=force)

    codex_frontmatter, portable_notes, manual_notes = build_codex_frontmatter(source)
    rewritten_body, rewrite_notes = rewrite_body(source.body)
    body_findings = detect_body_findings(rewritten_body)
    copied_dirs = copy_bundled_dirs(source, destination_dir)
    if copied_dirs:
        portable_notes.append("Copied bundled directories: " + ", ".join(f"`{name}/`" for name in copied_dirs) + ".")

    result = ConversionResult(
        source_path=source.source_path,
        source_type=source.source_type,
        destination_dir=destination_dir,
        skill_name=skill_name,
        codex_frontmatter=codex_frontmatter,
        rewritten_body=rewritten_body,
        status=determine_status(manual_notes, body_findings),
        portable_notes=portable_notes,
        rewrite_notes=rewrite_notes,
        manual_notes=manual_notes,
        body_findings=body_findings,
        bundled_dirs=copied_dirs,
        raw_frontmatter=source.raw_frontmatter,
    )
    write_conversion_output(result)
    return result


def resolve_batch_root(source_root: Path) -> Path:
    claude_root = source_root / ".claude"
    if claude_root.exists():
        return claude_root
    return source_root


def discover_batch_sources(source_root: Path) -> list[Path]:
    claude_root = resolve_batch_root(source_root)
    discovered: list[Path] = []

    skills_root = claude_root / "skills"
    if skills_root.exists():
        for skill_file in sorted(skills_root.glob("*/SKILL.md")):
            discovered.append(skill_file.parent)

    commands_root = claude_root / "commands"
    if commands_root.exists():
        for command_file in sorted(commands_root.glob("*.md")):
            discovered.append(command_file)

    return discovered


def build_batch_manifest(source_root: Path, output_root: Path, results: list[ConversionResult]) -> dict[str, Any]:
    return {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "generated_on": date.today().isoformat(),
        "items_total": len(results),
        "items_ready_with_review": sum(result.status == "ready_with_review" for result in results),
        "items_manual_follow_up_required": sum(result.status == "manual_follow_up_required" for result in results),
        "items": [
            {
                "source_path": str(result.source_path),
                "source_type": result.source_type,
                "skill_name": result.skill_name,
                "status": result.status,
                "output_path": str(result.destination_dir),
                "manual_follow_up_items": len(result.manual_notes) + len(result.body_findings),
                "rewrite_items_applied": len(result.rewrite_notes),
            }
            for result in results
        ],
    }


def build_batch_report(source_root: Path, results: list[ConversionResult]) -> str:
    lines = [
        "# Batch Migration Report",
        "",
        "## Source",
        f"- Source root: `{source_root}`",
        f"- Generated on: `{date.today().isoformat()}`",
        "",
        "## Summary",
        f"- Total items: `{len(results)}`",
        f"- Ready with review: `{sum(result.status == 'ready_with_review' for result in results)}`",
        f"- Manual follow-up required: `{sum(result.status == 'manual_follow_up_required' for result in results)}`",
        "",
        "## Items",
    ]

    for result in results:
        lines.extend(
            [
                f"### `{result.skill_name}`",
                f"- Source: `{result.source_path}`",
                f"- Type: `{result.source_type}`",
                f"- Status: `{result.status}`",
                f"- Auto-rewrites: `{len(result.rewrite_notes)}`",
                f"- Manual follow-up items: `{len(result.manual_notes) + len(result.body_findings)}`",
                f"- Output: `{result.destination_dir}`",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def write_batch_output(source_root: Path, output_root: Path, results: list[ConversionResult]) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "batch-migration-report.md").write_text(
        build_batch_report(source_root, results),
        encoding="utf-8",
    )
    (output_root / "batch-migration-manifest.json").write_text(
        json.dumps(build_batch_manifest(source_root, output_root, results), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_batch(source_root: Path, output_root: Path, force: bool) -> list[ConversionResult]:
    sources = discover_batch_sources(source_root)
    if not sources:
        raise FileNotFoundError(
            "No Claude skills or legacy commands were found. Expected .claude/skills/* or .claude/commands/*.md."
        )

    output_root.mkdir(parents=True, exist_ok=True)
    results = [convert_source(source, output_root, force=force) for source in sources]
    write_batch_output(source_root, output_root, results)
    return results


def print_single_summary(result: ConversionResult) -> None:
    print(f"[OK] Migrated {result.source_path} -> {result.destination_dir}")


def print_batch_summary(output_root: Path, results: list[ConversionResult]) -> None:
    print(
        "[OK] Batch migration completed: "
        f"{len(results)} item(s) -> {output_root} "
        f"({sum(result.status == 'manual_follow_up_required' for result in results)} manual-follow-up)"
    )


def main() -> int:
    args = parse_args()
    source_path = Path(args.source).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()

    try:
        if args.batch:
            results = run_batch(source_path, output_root, force=args.force)
            print_batch_summary(output_root, results)
            if args.strict and any(result.status == "manual_follow_up_required" for result in results):
                print(
                    "[WARN] Strict mode failed because one or more migrated items still require manual follow-up. "
                    f"See {output_root / 'batch-migration-report.md'}",
                    file=sys.stderr,
                )
                return 2
            return 0

        result = convert_source(source_path, output_root, force=args.force)
        print_single_summary(result)
        if args.strict and result.status == "manual_follow_up_required":
            print(
                "[WARN] Strict mode failed because manual follow-up items were detected. "
                f"See {result.destination_dir / 'references' / 'migration-report.md'}",
                file=sys.stderr,
            )
            return 2
        return 0
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
