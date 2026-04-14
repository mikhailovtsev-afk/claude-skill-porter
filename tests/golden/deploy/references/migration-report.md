# Migration Report

## Source
- Source path: `/Users/liisengineering/Downloads/Claud migration/tests/fixtures/legacy-command/deploy.md`
- Source type: `command`
- Generated on: `2026-04-14`
- Output path: `/Users/liisengineering/Downloads/Claud migration/tests/golden/deploy`

## Verdict
- Status: `ready_with_review`
- Portable items copied: `1`
- Auto-rewrites applied: `1`
- Manual follow-up items: `0`

## Copied Automatically
- Copied `name` and `description` into the Codex skill.

## Auto-Rewrites Applied
- Converted inline Claude shell injections into explicit run instructions.

## Manual Review Required
- No unsupported frontmatter fields were detected.

## Remaining Claude-Specific Patterns In Body
- No unresolved Claude-only placeholders or shell-injection patterns were detected.

## Bundled Directories
- No bundled directories were present in the source.

## Recommended Next Steps
- Read this report before trusting the migrated skill in production.
- Review the rewritten body to confirm the new wording still reflects the original intent.
- Rewrite any remaining Claude-only placeholders into plain Codex instructions or helper scripts.
- Re-test the migrated skill on a real task and check whether the description still triggers correctly.
