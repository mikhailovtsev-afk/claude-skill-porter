# Mapping Matrix

## Purpose

This document is the compatibility map for moving skills from Claude Code to Codex. It is intentionally conservative. If a feature is not clearly supported in Codex in this workspace, treat it as `manual` instead of assuming parity.

## Migration Status Labels

- `portable`: safe to carry over automatically in the MVP converter
- `partial`: can be copied only in a reduced or simplified form
- `manual`: must be rewritten, downgraded, or explicitly approved by a human

## High-Level Model

The shared foundation between Claude Code and Codex is the Agent Skills shape:

- skill folder
- `SKILL.md`
- optional `scripts/`
- optional `references/`
- optional `assets/`

The biggest migration problems come from Claude-specific runtime behavior, not from the folder shape itself.

## Directory-Level Mapping

| Claude source | Codex target | Status | Notes |
| --- | --- | --- | --- |
| `.claude/skills/<skill>/SKILL.md` | `skills/<skill>/SKILL.md` or `~/.codex/skills/<skill>/SKILL.md` | `portable` | Folder shape maps well. |
| `.claude/commands/<name>.md` | `skills/<name>/SKILL.md` | `partial` | Commands should be wrapped as skills. |
| `scripts/` | `scripts/` | `portable` | Copy as-is, then test. |
| `references/` | `references/` | `portable` | Copy as-is. |
| `assets/` | `assets/` | `portable` | Copy as-is. |
| `.claude/agents/` | none | `manual` | Custom Claude subagents are not directly represented by a Codex skill. |

## Frontmatter Mapping

| Claude field | Codex handling | Status | Why |
| --- | --- | --- | --- |
| `name` | copy | `portable` | Core skill identity. |
| `description` | copy and polish if needed | `portable` | Core trigger text in both systems. |
| `argument-hint` | copy when simple | `portable` | Seen in local Codex skills in this environment. |
| `allowed-tools` with bare tool names | copy carefully | `partial` | Works only for simple names; not for command patterns. |
| `allowed-tools` with `Bash(...)` patterns | report only | `manual` | Tool grammar likely differs. |
| `disable-model-invocation` | report only | `manual` | No confirmed Codex equivalent here. |
| `user-invocable` | report only | `manual` | No confirmed Codex equivalent here. |
| `context: fork` | rewrite as workflow guidance | `manual` | Claude runs isolated work through a subagent. |
| `agent` | report only | `manual` | Claude subagent type is platform-specific. |
| `hooks` | report only | `manual` | Hooks are Claude lifecycle behavior. |
| `paths` | report only | `manual` | Path-scoped activation is Claude-specific. |
| `model` | report only | `manual` | Per-skill model override is not assumed portable. |
| `effort` | report only | `manual` | Per-skill effort override is not assumed portable. |
| `shell` | report only | `manual` | Claude shell selection is tied to its injection model. |
| unknown custom fields | preserve in report | `manual` | Do not silently discard. |

## Body-Level Pattern Mapping

| Claude pattern | Codex handling | Status | Notes |
| --- | --- | --- | --- |
| Plain markdown instructions | copy | `portable` | This is the easiest case. |
| Relative file references like `scripts/foo.py` | copy | `portable` | Still valid if structure is preserved. |
| `$ARGUMENTS` | replace or document | `manual` | Needs a Codex-native way to receive inputs. |
| `$ARGUMENTS[N]` or `$0` | replace or document | `manual` | Same issue as above. |
| `${CLAUDE_SESSION_ID}` | report only | `manual` | Claude runtime variable. |
| `${CLAUDE_SKILL_DIR}` | usually rewrite to explicit path guidance | `manual` | Runtime variable is Claude-specific. |
| Inline shell injection `!` | convert to explicit step or helper script | `manual` | Claude preprocesses command output before model execution. |
| Fenced shell injection blocks starting with ````!` | convert to explicit step or helper script | `manual` | Same issue at larger scale. |
| "ultrathink" hints | ignore or rewrite as plain instruction | `manual` | Claude-specific trigger wording. |

## Behavioral Gaps That Matter Most

### 1. Invocation Control

Claude can hide a skill from the model, hide it from the user, or allow both. In Codex, that behavior is not safely assumed from a migrated `SKILL.md`.

### 2. Subagent Execution

Claude can run a skill with `context: fork` and bind it to an `agent` type. That is not just text; it changes execution context and permissions. This is a design gap, not a formatting gap.

### 3. Dynamic Context Injection

Claude can run shell commands and insert the output before the skill body reaches the model. Codex skills in this project should instead:

- tell the agent to run a script explicitly
- or bundle a helper script and reference it from the workflow

### 4. Tool Permission Semantics

Even when both systems mention `allowed-tools`, the grammar and enforcement are not guaranteed to match. Treat complex allowlists as policy, not as plain metadata.

## Recommended MVP Output Contract

Every migrated skill should contain:

- `SKILL.md`
- `agents/openai.yaml`
- `references/migration-report.md`
- `references/migration-manifest.json`
- `references/original-frontmatter.md`

The migration report should always answer:

- What was copied automatically?
- What was downgraded?
- What was left for manual work?
- Why is that risky?
- Can automation or CI detect that risk without reading markdown by hand?

## What The MVP Converter Is Allowed To Do

- copy plain content
- normalize the skill name
- preserve simple metadata
- copy bundled folders
- emit a detailed report

## What The MVP Converter Must Not Pretend To Do

- guarantee feature parity
- emulate Claude hooks automatically
- emulate Claude subagent behavior automatically
- silently resolve placeholders like `$ARGUMENTS`
- silently execute embedded Claude shell injections

## Recommended Human Review Checklist

1. Read the migrated `SKILL.md` without the source open.
2. Check whether the instructions still make sense without Claude-only runtime features.
3. Open `references/migration-report.md`.
4. Rewrite every `manual` item before using the migrated skill in production.
5. Test the migrated skill on one real task and compare the behavior to the original intent.
