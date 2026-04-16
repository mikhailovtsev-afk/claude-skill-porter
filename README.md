# Claude Skill Porter

Claude Skill Porter is a Codex skill and helper converter for migrating Claude Code skills into Codex-ready skills.

The project is intentionally conservative:

- it copies the portable parts automatically
- it applies safe rewrites for common low-risk Claude patterns
- it reports unsupported or risky behavior instead of pretending full compatibility

## What this project does

Claude Skill Porter helps migrate:

- Claude Code skills from `.claude/skills/*`
- legacy Claude commands from `.claude/commands/*.md`

It can:

- convert a single skill
- convert a single legacy command
- scan a whole repo in batch mode
- generate markdown and JSON migration reports
- fail loudly in strict mode when manual follow-up is still required

## What this project does not do

This project is not a full Claude Code compatibility layer.

It does not try to:

- emulate Claude hooks
- emulate Claude subagents
- guarantee 100% Claude Code to Codex parity
- silently rewrite every complex Claude-specific runtime behavior

If something is not safely portable, the tool should surface it as manual follow-up.

## Why this exists

Sometimes the right answer is to stay on Claude Code.

This project is useful when:

- a team is moving to Codex
- existing Claude skills need to be reused in Codex
- you want a safer and more transparent migration workflow
- you want a GitHub-friendly artifact with reports and tests

## Project structure

- `skills/claude-skill-porter/` - the Codex skill
- `skills/claude-skill-porter/scripts/convert_claude_skill.py` - the converter
- `skills/claude-skill-porter/references/` - docs, risks, roadmap, Russian guides
- `tests/fixtures/` - input examples
- `tests/golden/` - expected outputs
- `tests/test_convert_claude_skill.py` - fixture-based tests

## Quick start

### Convert one Claude skill

```bash
python3 skills/claude-skill-porter/scripts/convert_claude_skill.py /path/to/repo/.claude/skills/my-skill /tmp/migrated-skills
```

### Convert one legacy command

```bash
python3 skills/claude-skill-porter/scripts/convert_claude_skill.py /path/to/repo/.claude/commands/deploy.md /tmp/migrated-skills
```

### Convert a whole repo

```bash
python3 skills/claude-skill-porter/scripts/convert_claude_skill.py /path/to/repo /tmp/migrated-skills --batch
```

### Fail on unresolved incompatibilities

```bash
python3 skills/claude-skill-porter/scripts/convert_claude_skill.py /path/to/repo /tmp/migrated-skills --batch --strict
```

## Output

For each migrated item, the converter writes:

- `SKILL.md`
- `agents/openai.yaml`
- `references/migration-report.md`
- `references/migration-manifest.json`
- `references/original-frontmatter.md`

In batch mode, it also writes:

- `batch-migration-report.md`
- `batch-migration-manifest.json`

## Safe rewrites currently supported

The converter can safely rewrite some common low-risk patterns:

- `$ARGUMENTS`
- `$ARGUMENTS[n]`
- simple `$1`, `$2` style placeholders
- common `${CLAUDE_*}` path-like variables
- simple inline shell injection like `!` command usage

Anything more behavior-heavy should still be treated as manual follow-up.

## Running tests

### Validate the Codex skill locally

```bash
python3 /Users/liisengineering/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/claude-skill-porter
```

### Run automated tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Release mindset

Before publishing, you should check:

- skill validation
- automated tests
- smoke test of the converter
- strict mode behavior
- privacy review for copied references and scripts
- docs accuracy

## Additional docs

Important project docs live in `skills/claude-skill-porter/references/`, including:

- [Russian guide](GUIDE_RU.md)
- [Russian GitHub publishing guide](GITHUB_PUBLISHING_RU.md)
- community critique notes
- mapping matrix
- risk register
- implementation roadmap
- v1 checklist

If you want the project overview in Russian, start with `GUIDE_RU.md`.

## Positioning

The strongest honest framing for this project is:

> This is not a promise of full compatibility.
> It is a safe and transparent tool for migrating the portable part of Claude Code skills into Codex, with explicit reporting for anything that still needs manual work.
