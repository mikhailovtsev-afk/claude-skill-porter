---
name: claude-skill-porter
description: Convert Claude Code skills or legacy `.claude/commands/*.md` files into Codex-ready skills. Use when a repo contains `.claude/skills/*/SKILL.md`, when a team is migrating from Claude Code to Codex, or when you need a compatibility review, migration plan, and risk report before porting a skill.
---

# Claude Skill Porter

## Overview

This skill helps migrate reusable automation from Claude Code into Codex without pretending the two systems are identical. The goal is to preserve the portable parts, flag the dangerous gaps, and leave a Codex-ready skill plus a migration report that explains what still needs manual review.

## When To Use It

Use this skill when at least one of these is true:

- The source repo contains `.claude/skills/<skill-name>/SKILL.md`.
- The source repo still uses legacy `.claude/commands/*.md` files.
- A team wants a migration plan before moving from Claude Code to Codex.
- The source skill uses Claude-only features and you need a written risk report instead of a blind copy.

Do not use this skill when the user only wants a normal Codex skill from scratch with no Claude Code source. In that case, use a regular skill authoring workflow instead of a migration workflow.

## Core Promise

For each source skill or command, produce:

- A Codex-ready skill directory.
- A `references/migration-report.md` file that states exactly what was preserved, downgraded, or left for manual work.
- A `references/original-frontmatter.md` snapshot so no source metadata is silently lost.

## Migration Workflow

1. Inspect the source.
   - Accept either a Claude skill directory or a legacy command markdown file.
   - Identify whether the source is a true skill or an old command that should become a skill folder.
2. Read the compatibility docs before making assumptions.
   - Use [references/mapping-matrix.md](references/mapping-matrix.md) for field-by-field compatibility.
   - Use [references/risk-register.md](references/risk-register.md) for migration dangers and mitigations.
   - Use [references/implementation-roadmap.md](references/implementation-roadmap.md) for scope and rollout guidance.
3. Run the converter for deterministic work.
   - Use `scripts/convert_claude_skill.py` to copy portable structure and emit the report.
   - The converter now performs safe auto-rewrites for common Claude-only body patterns such as `$ARGUMENTS`, common `${CLAUDE_*}` path variables, and simple shell injection syntax.
   - Use `--strict` when you want publication or CI to fail on unresolved incompatibilities.
   - Use `--batch` when you want to migrate a whole repo or `.claude` directory in one pass.
4. Review the generated migration report.
   - Classify findings as `portable`, `partial`, or `manual`.
   - Never claim feature parity when the report says otherwise.
5. Polish the result.
   - Rewrite Claude-only placeholders into plain Codex instructions if needed.
   - Tighten descriptions so the migrated skill triggers correctly in Codex.
6. Validate the outcome.
   - Ensure the generated skill has a readable `SKILL.md`, `agents/openai.yaml`, and the two report files.
   - If the source used unsupported Claude-only behavior, call that out in the final answer.

## What Usually Transfers Cleanly

- Skill folder structure
- `name`
- `description`
- Markdown body instructions
- `scripts/`, `references/`, and `assets/` folders
- Simple `argument-hint` metadata
- Simple `allowed-tools` lists when they only contain bare tool names

## What Needs Caution

- `allowed-tools` entries with command patterns like `Bash(git *)`
- Legacy `.claude/commands/*.md` files
- Skills that depend on `$ARGUMENTS`, `$0`, or `${CLAUDE_*}` placeholders
- Skills that inject shell output with `!` commands

## What Is Never Safe To Pretend Is Portable

- `context: fork`
- `agent`
- `hooks`
- `paths`
- `model`
- `effort`
- Claude-specific invocation control such as `disable-model-invocation` and `user-invocable`

If any of these appear, preserve the evidence in the report and explain the downgrade in plain language.

## Converter Usage

Run the converter from this skill folder or by absolute path:

```bash
python3 scripts/convert_claude_skill.py <source-path> <output-root>
python3 scripts/convert_claude_skill.py <source-path> <output-root> --strict
python3 scripts/convert_claude_skill.py <repo-root> <output-root> --batch
```

Examples:

```bash
python3 scripts/convert_claude_skill.py /path/to/repo/.claude/skills/my-skill /tmp/migrated-skills
python3 scripts/convert_claude_skill.py /path/to/repo/.claude/commands/deploy.md /tmp/migrated-skills
python3 scripts/convert_claude_skill.py /path/to/repo /tmp/migrated-skills --batch --strict
```

The converter writes a folder under `<output-root>/<normalized-skill-name>/` with:

- `SKILL.md`
- `agents/openai.yaml`
- `references/migration-report.md`
- `references/migration-manifest.json`
- `references/original-frontmatter.md`
- copied `scripts/`, `references/`, and `assets/` directories when present

When `--batch` is used, it also writes:

- `batch-migration-report.md`
- `batch-migration-manifest.json`

## Output Rules

- Never delete or mutate the source skill.
- Never silently drop unsupported behavior.
- Prefer a safe downgrade plus a clear report over a misleading "successful" conversion.
- Safe rewrites are allowed only for low-risk textual cases; anything behavior-heavy must still surface as manual follow-up.
- Before GitHub or team-wide sharing, prefer `--strict` so unresolved incompatibilities fail loudly.
- Keep the migrated `SKILL.md` usable on its own; move long explanations into `references/`.
- If parsing fails, stop and explain the failure instead of guessing.

## Resources

- [scripts/convert_claude_skill.py](scripts/convert_claude_skill.py): deterministic MVP converter
- [references/mapping-matrix.md](references/mapping-matrix.md): exact feature mapping between Claude Code and Codex
- [references/risk-register.md](references/risk-register.md): migration risks, impact, and mitigations
- [references/implementation-roadmap.md](references/implementation-roadmap.md): architecture, rollout phases, and validation plan
- [references/community-critique-ru.md](references/community-critique-ru.md): likely community criticism and how this skill addresses it
