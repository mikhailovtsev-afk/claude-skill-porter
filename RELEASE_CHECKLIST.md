# Release Checklist

Use this checklist before publishing Claude Skill Porter to GitHub or sharing it more widely.

## 1. Local validation

- [ ] Run Codex skill validation
- [ ] Run unit tests
- [ ] Run Python syntax check for the converter

## 2. Migration smoke test

- [ ] Convert one simple Claude skill
- [ ] Convert one legacy Claude command
- [ ] Run one batch migration against a temporary `.claude` repo
- [ ] Confirm reports and manifests are generated

## 3. Strict mode safety

- [ ] Run a clean case in normal mode
- [ ] Run a risky case in `--strict`
- [ ] Confirm risky migration exits non-zero

## 4. Privacy and content review

- [ ] Check copied `references/`, `scripts/`, and `assets/` for secrets or private content
- [ ] Confirm examples and fixtures are safe to publish
- [ ] Confirm generated manifests do not expose sensitive local data in committed files

## 5. Docs review

- [ ] README matches the current behavior
- [ ] Russian docs still match the product
- [ ] Non-goals and limitations are clearly stated
- [ ] Quick start commands still work

## 6. Repo cleanup

- [ ] Remove `.DS_Store`
- [ ] Remove `__pycache__`
- [ ] Confirm `.gitignore` covers common local noise
- [ ] Confirm `LICENSE` is present

## 7. GitHub readiness

- [ ] CI passes
- [ ] Root files are present: `README.md`, `LICENSE`, `.gitignore`
- [ ] Project description is honest and not overclaiming compatibility

## Suggested commands

```bash
python3 /Users/liisengineering/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/claude-skill-porter
python3 -m py_compile skills/claude-skill-porter/scripts/convert_claude_skill.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 skills/claude-skill-porter/scripts/convert_claude_skill.py tests/fixtures/basic-skill /tmp/claude-skill-porter-smoke --force
python3 skills/claude-skill-porter/scripts/convert_claude_skill.py tests/fixtures/context-fork /tmp/claude-skill-porter-strict --strict --force
```
