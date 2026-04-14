# Risk Register

## How To Read This Document

Each risk is described in plain language so a non-programmer can still make a good go or no-go decision.

- `Likelihood`: how often this can realistically happen
- `Impact`: how painful the failure would be
- `Mitigation`: what we do to reduce the risk

## Risk 1: False sense of compatibility

- Likelihood: High
- Impact: High
- What can go wrong: The migration looks "successful" because files were copied, but the real behavior changed in subtle ways.
- Why it matters: This is the fastest path to broken trust. The team thinks the skill works when it only looks similar on disk.
- Mitigation: Always generate and read `references/migration-report.md`. Never claim full parity unless manual issues are zero.

## Risk 2: Claude-only runtime features disappear

- Likelihood: High
- Impact: High
- What can go wrong: The source skill depended on `context: fork`, `agent`, `hooks`, or shell injection, and the migrated skill no longer performs the hidden runtime work.
- Why it matters: These features change behavior, not just formatting.
- Mitigation: Treat those features as `manual`, not `portable`. Force the report to mention each one explicitly.

## Risk 3: Arguments stop working

- Likelihood: High
- Impact: Medium
- What can go wrong: The original Claude skill used `$ARGUMENTS`, `$ARGUMENTS[0]`, or `$0`, but Codex does not interpret them the same way.
- Why it matters: Skills that depend on arguments often become confusing or unusable after migration.
- Mitigation: Detect placeholders automatically and require a rewrite into plain instructions or helper scripts.

## Risk 4: Tool permissions become unsafe or misleading

- Likelihood: Medium
- Impact: High
- What can go wrong: A Claude `allowed-tools` rule is copied over even though Codex interprets permissions differently.
- Why it matters: Best case, the rule does nothing. Worst case, people trust an approval model that is no longer true.
- Mitigation: Auto-copy only simple tool-name lists. Send complex patterns to manual review.

## Risk 5: Path-scoped behavior is lost

- Likelihood: Medium
- Impact: Medium
- What can go wrong: The original skill only activated for certain files or directories, but the migrated version becomes globally triggerable.
- Why it matters: This can make a skill noisy or cause it to activate in the wrong context.
- Mitigation: Report `paths` as manual work and mention the likely trigger drift.

## Risk 6: Shell injection becomes stale or dangerous

- Likelihood: Medium
- Impact: High
- What can go wrong: Claude used `!command` syntax to inject live data before execution. If we copy the text without redesigning it, the skill may reference data that is never fetched.
- Why it matters: The migrated skill may look smart but operate on stale assumptions.
- Mitigation: Detect shell injection syntax and convert it into explicit workflow steps or helper scripts.

## Risk 7: Legacy commands are migrated too literally

- Likelihood: Medium
- Impact: Medium
- What can go wrong: A legacy `.claude/commands/*.md` file is copied over without re-framing it as a reusable Codex skill.
- Why it matters: Commands and skills overlap in Claude, but the destination model should be explicit and clean.
- Mitigation: Wrap commands as skills and state the source type in the migration report.

## Risk 8: Hidden dependencies are copied but never tested

- Likelihood: High
- Impact: Medium
- What can go wrong: Scripts, references, or assets are copied over, but the migrated skill still breaks because the scripts assume missing packages, shells, or environment variables.
- Why it matters: This creates a delayed failure that shows up only when someone finally uses the skill.
- Mitigation: After conversion, test at least one representative script or end-to-end run.

## Risk 9: Sensitive material is propagated unintentionally

- Likelihood: Medium
- Impact: High
- What can go wrong: References or scripts may contain internal URLs, tokens, or private company process details that should not be spread to new environments.
- Why it matters: Migration can accidentally become data leakage.
- Mitigation: Treat copied references as review material. Do not publish or share migrated skills before a privacy pass.

## Risk 10: Description drift hurts auto-triggering

- Likelihood: Medium
- Impact: Medium
- What can go wrong: The original description was tuned for Claude's matching behavior and no longer triggers well in Codex.
- Why it matters: A technically correct migration still feels broken if the skill never activates when expected.
- Mitigation: Rewrite descriptions after conversion to match Codex usage language and test with realistic prompts.

## Risk 11: Over-documentation bloats the main skill

- Likelihood: Medium
- Impact: Low
- What can go wrong: We stuff every migration note into the main `SKILL.md`, making the migrated skill noisy and less effective.
- Why it matters: The runtime instructions should stay focused.
- Mitigation: Keep the main skill lean and push heavy detail into `references/`.

## Risk 12: MVP scope quietly expands into a full platform emulator

- Likelihood: High
- Impact: High
- What can go wrong: The project tries to re-create Claude-only features like hooks, subagents, and shell preprocessing in one step.
- Why it matters: This will slow delivery and increase fragility.
- Mitigation: Keep the MVP narrow: copy portable parts, report incompatibilities, and require manual redesign where needed.

## Go / No-Go Guidance

Green light for MVP conversion:

- The source skill is mostly plain instructions.
- The source has simple or no frontmatter beyond `name` and `description`.
- The report shows few or no `manual` items.

Yellow light:

- The source uses arguments or a simple tool allowlist.
- The report has several `manual` items, but none are safety-critical.

Red light:

- The source depends on hooks, subagents, shell injection, or path-scoped activation.
- The team expects zero behavior drift.
- No one is available to review the migration report after conversion.

## Operational Rule

If a migration would mislead the next person into believing the skill is fully portable, stop and downgrade the claim. Honest partial migration is better than a confident broken one.

## Before Public Release

Before pushing this project to GitHub, require all of these:

- run structural validation on the skill itself
- run at least one smoke test of the converter
- review `migration-report.md`
- review `migration-manifest.json`
- do a privacy pass over copied references and scripts
- prefer `--strict` for any publish-oriented run
