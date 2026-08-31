---
description: Commit, push, create PR, merge, and clean up after a feature is complete
allowed-tools: Read, Bash(git:*), mcp__github__create_pull_request, mcp__github__merge_pull_request
---

## Step 1 — Identify current branch

```bash
git branch --show-current
```

Store this as CURRENT_BRANCH. Abort if CURRENT_BRANCH is `main` — never ship from main.

## Step 2 — Inspect changes and spec

Run:

```bash
git status --short
git diff
git diff --staged
git log main..HEAD --oneline
```

Read `.claude/specs/` to find the spec for the current feature (e.g. `08-edit-expense.md`).

Use the spec overview and the diff to plan commit groups for Step 3.

## Step 3 — Create atomic commits (never a single `git add .` commit)

> **Why atomic:** one bulk `git add . && git commit -m "..."` mixes DB, route, UI, and test changes into a single hard-to-review commit. Split by logical concern so each commit is independently reviewable and revertable.

### 3a — Group files by concern

Inspect `git status --short` (includes untracked `??` files) and `git diff --stat`. Group into 2-5 commits:

| Group | Typical files | Commit prefix |
|---|---|---|
| DB layer | `db/db.py`, `db/queries.py` | `feat` or `feat(db)` |
| Routes / app logic | `app.py` | `feat` |
| UI — templates & styles | `templates/*.html`, `static/css/*.css` | `feat(ui)` |
| Tests | `tests/*.py` | `test` |
| Spec / docs | `.claude/specs/*.md`, `*.md` | `docs` or `feat` (specs are versioned — see `01ed9c5`) |

Rules for grouping:

- Each commit must contain only files from **one** group. Never mix unrelated concerns.
- Never use `git add .`, `git add -A`, or `git commit -a` when more than one group has changes. Even with a single group, prefer explicit `git add <files>`.
- Untracked files (`??` in `git status --short`) must be grouped too — `git add .` as a shortcut is forbidden.
- Keep commit messages Conventional Commits: `feat:`, `fix:`, `feat(ui):`, `test:`, `docs:`, `chore:` — lowercase, no period, < 72 chars, user-facing (Good: `feat: add delete expense button with confirmation dialog` / Bad: `feat: added DELETE route to app.py`).

### 3b — Commit each group separately

For each group, run explicit adds and a focused commit. Example for `feature/edit-expense`:

```bash
# 1 — DB helpers
git add db/db.py db/queries.py
git commit -m "feat(db): add update_expense helper and include id in recent transactions"

# 2 — Route/handler
git add app.py
git commit -m "feat: add edit expense route with validation and ownership check"

# 3 — UI
git add templates/edit_expense.html templates/profile.html static/css/edit_expense.css
git commit -m "feat(ui): add edit expense form and profile edit links"

# 4 — Tests
git add tests/test_edit_expense.py tests/test_backend_connection.py
git commit -m "test: add coverage for edit expense flow"

# 5 — Spec (if spec file is new/changed and tracked in this repo)
git add .claude/specs/08-edit-expense.md
git commit -m "docs: add spec for edit expense feature"
```

Adapt file lists to the actual `git status --short` output — the example above is illustrative, not prescriptive. If a group has no changes, skip it. If only one group changed, a single atomic commit is acceptable (still via explicit `git add <files>`).

### 3c — Verify

```bash
git log main..HEAD --oneline
git status --short
```

- `git log main..HEAD --oneline` should show 2-5 new commits (one per group), not a single bulk commit.
- `git status --short` should be clean (`nothing to commit, working tree clean`). If not, group and commit remaining files.

Report:

```
✓ Committed — <n> atomic commits:
  - <hash> <message 1>
  - <hash> <message 2>
  ...
```

## Step 4 — Push to feature branch

```bash
git push -u origin CURRENT_BRANCH
```

Do NOT use `gh` CLI — it is not installed in this environment (see Rules). Push via `git` only.

Report: "✓ Pushed — CURRENT_BRANCH"

## Step 5 — Create PR via GitHub MCP

Use the GitHub MCP server (`mcp__github__create_pull_request`) to create a pull request from CURRENT_BRANCH into `main`.

- Do NOT use `gh pr create` — `gh` CLI is not available (verified: `gh: term not recognized` on win32).
- If GitHub MCP is not connected, stop and say: "GitHub MCP is not connected. Run /mcp to check connection." Do not fall back to `gh`.

Title: plain English feature name, no conventional commit prefix
Example: "Add delete expense functionality"

Description:

```markdown
## What this PR does

<one paragraph from the spec overview section>

## Changes

<bullet list of every file changed with one line description each>

## Definition of done

<copy the definition of done checklist from the spec,
mark every item as checked [x]>

## How to test

1. Run python app.py
2. Log in as demo@spendly.com / demo123
3. <specific steps from the spec to verify this feature works>
```

Report: "✓ PR created — <PR URL>"

## Step 6 — Merge PR via GitHub MCP

Use the GitHub MCP server (`mcp__github__merge_pull_request`) to merge the pull request just created. Use **squash merge**.

- Do NOT use `gh pr merge`.

Report: "✓ PR merged to main"

## Step 7 — Delete remote branch via git

The GitHub MCP server (`https://api.githubcopilot.com/mcp/`) does **not** expose a `delete_branch` / `delete_ref` tool — calling `mcp__github__delete_branch` fails with `tool not found` after the PR is merged. Delete the remote branch with git instead.

```bash
git push origin --delete CURRENT_BRANCH
```

- Do NOT use `mcp__github__delete_branch` — it does not exist on this MCP server.
- Do NOT use `gh api` / `gh` CLI — `gh` is not installed (see Rules).
- If the branch was already auto-deleted by GitHub's "automatically delete head branches" setting, `git push` will report `remote ref does not exist` — treat that as success.

Report: "✓ Remote branch deleted"

## Step 8 — Switch to main and pull

```bash
git checkout main
git pull origin main
```

Report: "✓ Switched to main — up to date"

## Step 9 — Delete local feature branch

```bash
git branch -D CURRENT_BRANCH
```

Report: "✓ Local branch deleted"

## Final summary

Print:

```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
/ship-feature complete
✓ Committed — <n> atomic commits (<messages>)
✓ Pushed — <branch>
✓ PR created and merged
✓ Remote branch deleted
✓ Switched to main
✓ Local branch deleted
Next: run /create-spec for the next feature
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```

## Rules

- Never commit directly to main
- Always create **atomic commits** — one logical concern per commit, via explicit `git add <files>`. Never `git add .` + single commit when multiple concerns changed.
- Always use squash merge
- Always delete both remote and local branch after merge
- Never use `gh` CLI — it is not available in this environment. Use `git` for all local git operations and branch deletion (`git push origin --delete`), and GitHub MCP (`mcp__github__*`) only for PR create/merge. Do not attempt `gh --version`, `gh pr create`, `gh pr merge`, or `gh api`. Do not call `mcp__github__delete_branch` — it does not exist.
- If GitHub MCP is not connected stop and say: "GitHub MCP is not connected. Run /mcp to check connection."
- If push fails due to no upstream, use `git push -u origin CURRENT_BRANCH`
- Never proceed to merge if PR creation fails
