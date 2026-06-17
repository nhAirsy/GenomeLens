---
name: genomelens-developer
description: GenomeLens project-only developer role workflow for feature work, content updates, tests, docs, and isolated implementation branches in nhAirsy/GenomeLens. Use when the user asks Codex to act as the project's ordinary developer, implement a feature branch, update project content, or continue the repository-specific feature development workflow.
---

# GenomeLens Developer

## Scope

Use this skill only for the `nhAirsy/GenomeLens` repository and only while acting as the project's ordinary developer. First verify the current repo remote or path matches GenomeLens. If it does not, stop using this skill and follow normal instructions instead.

Prefer the current Codex worktree assigned to the task. Do not edit the user's main worktree unless the user explicitly points the task there.

## Baseline Sync

At the start of every developer task:

1. Check the current branch and worktree state with `git status --short --branch`.
2. Treat `origin/main` or the current release baseline as the preferred source for new feature work unless the user names another base.
3. Preserve user changes. If the worktree is dirty, identify whether those changes belong to the current task before editing.
4. Read the relevant docs and tests before changing behavior.

## Branch Policy

Use one feature branch per coherent change:

```powershell
git switch -c feature/<short-topic>
```

Use `feature/` for new behavior and content updates. Reserve `fix/` for the dedicated fixer role and issue repair workflow.

## Implementation Loop

For each feature or content update:

1. Understand the existing contract before adding a new one.
2. Keep changes scoped to the requested behavior.
3. Prefer project-owned code under `platform/`, `engines/jcvi/src/jcvi_genomelens/`, `integrations/`, `docs/`, and `.codex/skills/`.
4. Avoid modifying vendored JCVI code under `engines/jcvi/src/jcvi/` unless the feature explicitly requires upstream behavior changes.
5. Add or update tests with the implementation when behavior changes.
6. Commit with Conventional Commits, for example `feat(local_synteny): highlight target genes in local blocks`.

## Validation

Choose the smallest relevant tests first, then broaden based on risk. Before committing, run:

```powershell
git status --short --branch
git diff --check
```

For CI parity, prefer Python 3.12 and use the relevant subset of:

```powershell
python -m ruff check platform/src platform/tests engines/jcvi/src/jcvi_genomelens engines/jcvi/tests integrations/haiant_plugin/src integrations/haiant_plugin/tests
python -m ruff format --check platform/src platform/tests engines/jcvi/src/jcvi_genomelens engines/jcvi/tests integrations/haiant_plugin/src integrations/haiant_plugin/tests
python -m pytest platform/tests
python -m pytest engines/jcvi/tests
python -m pytest integrations/haiant_plugin/tests
```

If an engine integration test needs BLAST+ or another external toolchain locally, record the caveat and do not stage temporary downloads or junctions.

## Delivery

Final developer status should include:

- Branch name and commit SHA when committed.
- What changed.
- Tests run and any skipped validation.
- Any follow-up work that remains.
