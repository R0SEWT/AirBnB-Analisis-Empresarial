# airbnb-analytics — AI Agent Instructions

## Project

Academic analytics project for Airbnb.

The project connects strategic business analysis with data architecture, analytical initiatives, dashboards, and reports.

Core frame:

> Airbnb should evolve from a growth-and-conversion marketplace into a trust-governed analytical platform.

## Source of Truth

Use these sources in order:

1. `CLAUDE.md` for agent behavior.
2. `.beads/` for current tasks, status, decisions, and work tracking.
3. `docs/architecture.md` for stable technical grounding.
4. `README.md` for human-facing project usage.

Do not create extra planning markdown files unless explicitly requested.

## Repository Strategy

Branches are temporary work streams, not permanent folders.

Main branches:

- `main`: stable deliverable.
- `dev`: integration branch.

Feature branches:

- `feature/data-medallion`
- `feature/analytics`
- `feature/models`
- `feature/dashboard`
- `feature/app-demo`
- `feature/tb2-report`

Completed work follows:

```text
feature/* → dev → main
```

Rules:

- Keep `main` stable and deliverable-ready.
- Integrate work in `dev` before merging to `main`.
- Do not use branches as permanent project folders.
- Prefer short-lived branches with narrow scope.

## Data Architecture

Use the medallion architecture described in `docs/architecture.md`:

```text
raw → bronze → silver → gold
```

Do not commit large data files.

Version code, schemas, configuration, report sources, dashboard definitions, and small samples only.

## Analytical Frame

Classify analytical initiatives as:

```text
descriptive → diagnostic → predictive → prescriptive
```

Every analytical artifact must connect to a business question or decision.

Preferred Airbnb analytical themes:

- marketplace trust
- listing quality
- guest experience
- host alignment
- dispute reduction
- regulatory readiness
- marketplace liquidity
- revenue optimization

## Beads

Use Beads for all task tracking.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete
```

## Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files


## Development Workflow

Before work:

```bash
git status
bd ready
git checkout dev
git pull --rebase
```

For new work:

```bash
git checkout -b feature/<short-name>
```

Before finishing a code task:

```bash
uv run ruff check src/
uv run pytest tests/
git add .
git commit -m "<clear message>"
```

Then merge back:

```bash
git checkout dev
git pull --rebase
git merge feature/<short-name>
```

## Reports

Report writing and LaTeX generation are manual unless explicitly requested.

The agent may:
- organize report folders,
- check whether referenced figures exist,
- suggest structure,
- review text,
- identify formatting risks.

The agent must not:
- create `.tex` files automatically,
- generate PDFs automatically,
- rewrite full reports unless explicitly instructed,
- modify final report sources without a specific task.


## Quality Gates

Run when code changes:

```bash
uv sync
uv run ruff check src/
uv run pytest tests/
```

Run when reports change:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error reports/tb2/main.tex
```

If a gate is not applicable, state why in the Beads issue or session handoff.

## Session Completion

Before ending a session:

```bash
git status
bd dolt status
bd dolt push
git pull --rebase
git push
git status
```

Work is not complete until relevant changes are committed and pushed.

Final `git status` should be clean or explicitly explain remaining uncommitted files.

## Critical Rules

- Do not invent data sources.
- Do not claim model performance without evaluation.
- Do not commit large datasets.
- Do not use branches as permanent project folders.
- Do not mix raw cleaning logic with gold-layer business logic.
- Do not produce dashboards without business recommendations.
- Do not reference missing figures in LaTeX.
- Do not close Beads issues without committed deliverables.
- Do not merge to `main` unless the project is stable.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
