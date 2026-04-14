# Implementation Roadmap

## Goal

Build a practical Codex skill that helps move reusable automation from Claude Code into Codex while preserving trust. The skill should automate the safe, boring parts and force visibility for the risky parts.

## Current Baseline

The current version now includes:

- single-item migration
- batch migration for whole repos or `.claude` directories
- safe auto-rewrites for common low-risk Claude placeholders
- machine-readable manifests
- strict mode
- automated fixture-based tests with golden outputs
- root-level packaging for GitHub publication
- a release checklist and minimal CI

## Product Shape

This project is best framed as:

- one Codex skill: `claude-skill-porter`
- one deterministic helper script: `scripts/convert_claude_skill.py`
- several reference documents that explain compatibility, risk, and rollout

This is better than a prompt-only skill because migration has repeatable file operations and repeatable reporting logic.

## MVP Scope

The MVP should do these things well:

1. Accept a Claude skill directory or legacy command file.
2. Parse frontmatter conservatively.
3. Copy the portable structure into a new Codex-ready skill folder.
4. Generate a migration report that explains all non-portable features.
5. Preserve the original frontmatter for auditability.
6. Emit a machine-readable manifest for tooling and CI.
7. Support a strict mode that fails when unresolved incompatibilities are found.

The MVP should not try to:

- emulate Claude hooks
- emulate Claude subagents
- infer perfect replacements for dynamic shell injection
- guarantee exact permission parity

## Architecture

### Layer 1: Human-facing skill

`SKILL.md` explains:

- when to use the porter
- what it promises
- what it refuses to fake
- which references to read for deeper details

### Layer 2: Deterministic converter

`scripts/convert_claude_skill.py` handles:

- source detection
- frontmatter parsing
- name normalization
- bundled file copying
- report generation

### Layer 3: Decision support

Reference docs answer three different questions:

- `mapping-matrix.md`: what maps to what?
- `risk-register.md`: what can go wrong?
- `implementation-roadmap.md`: what should we build next?

## Recommended Conversion Algorithm

1. Detect source type.
   - If input is a directory, expect `SKILL.md`.
   - If input is a markdown file, treat it as a legacy command.
2. Parse the frontmatter.
   - Prefer a real YAML parser when available.
   - Fall back to a simple parser instead of crashing on ordinary files.
3. Classify fields.
   - `portable`
   - `partial`
   - `manual`
4. Copy content.
   - Write the new `SKILL.md`
   - Write `agents/openai.yaml`
   - Copy bundled directories
5. Write reports.
   - `migration-report.md`
   - `original-frontmatter.md`
6. Ask for human review when manual items exist.

## Why This Shape Is Safe

- It avoids silent loss of meaning.
- It keeps runtime instructions lean.
- It keeps risky interpretation decisions visible.
- It allows later phases to improve the converter without changing the basic skill contract.

## Suggested Next Phases

### Phase 1: MVP

Status target:

- converts basic skills
- wraps commands as skills
- reports incompatibilities

Success criteria:

- A simple Claude skill with plain markdown migrates cleanly.
- A legacy command becomes a valid skill folder.
- A complex Claude skill produces a clear red-flag report.
- A strict publish-oriented run fails loudly when manual follow-up still exists.

Current status:

- done

### Phase 2: Assisted rewrites

Add support for guided rewrites of:

- more complex `${CLAUDE_*}` variables
- richer shell injection patterns
- command bodies that need structural rewriting, not just textual replacement

This should still be conservative. The tool should propose rewrites, not pretend certainty.

### Phase 3: Batch migration

Support scanning an entire repo:

- already implemented for direct skill and command discovery
- next improvement is deeper discovery, better conflict handling, and richer repo-level summaries

### Phase 4: Validation suite

Add fixtures and golden outputs for:

- plain skill
- command file
- argument-heavy skill
- hook-heavy skill
- shell-injection-heavy skill

Status:

- done for the initial `v1` target

Current note:

- this project now has fixture-based tests and golden output snapshots for the core supported scenarios

## v1 Status

The project is now at a narrow but honest `v1` state:

- core migration behavior is automated
- major supported scenarios are covered by fixtures and golden outputs
- release steps are documented
- GitHub CI checks the converter and test suite

Future work should now focus on deeper compatibility and better ergonomics, not basic packaging.

## Acceptance Criteria

The project is useful when all of these are true:

- A non-programmer can read the report and understand the remaining risk.
- A developer can inspect the generated files and see what happened.
- The migrated folder is organized consistently every time.
- Unsupported Claude features are surfaced automatically.
- CI or a release script can read the manifest and stop a risky publish.

## Test Strategy

Test at three levels:

### 1. Parser sanity checks

- frontmatter with quoted values
- frontmatter with lists
- no frontmatter at all

### 2. Conversion scenarios

- basic skill directory
- legacy command markdown file
- skill with bundled folders

### 3. Safety scenarios

- skill using `$ARGUMENTS`
- skill using `context: fork`
- skill using `!` shell injection

The expected result in safety scenarios is not "perfect migration." The expected result is "clear warning plus preserved evidence."

Also test strict mode:

- it should return success for a clean case
- it should return non-zero for a risky case

## Open Questions

- Should Codex project-local skills live under `skills/` or be installed into `~/.codex/skills` as a separate publish step?
- Do we want a batch-report format like JSON in addition to markdown?
- Should the converter preserve some additional metadata fields if future Codex support becomes clearer?

## Recommended Decision

Start with a small, honest MVP. The key win is not magic conversion. The key win is reducing manual busywork while making incompatibilities obvious early.
