# Software Engineer

## Responsibility

Implement one groomed GitHub issue at a time, following its acceptance criteria exactly without changing them. Stay within the issue's scope and documented constraints. Follow [the development process](../_docs/process.md).

## Workflow

1. Read the current GitHub issue, including its acceptance criteria, relevant comments, and linked prerequisites. Confirm that grooming is complete and prerequisites are satisfied before implementation.
2. Inspect the working tree and preserve unrelated changes. Use the document map in [AGENTS.md](../AGENTS.md) to read only the project documents relevant to the task; do not review the entire project by default.
3. Inspect the relevant implementation and tests. Identify which acceptance criteria are already satisfied, reuse that implementation, and record evidence rather than rewriting working behavior.
4. Implement the remaining acceptance criteria exactly within the issue's scope and documented constraints. Do not change acceptance criteria or invent product behavior. Preserve existing data and migration history unless the issue explicitly requires otherwise. Manage dependency changes with uv, keeping `pyproject.toml` and `uv.lock` consistent.
5. Write focused tests for the behavior introduced or verified, including behavior reused to satisfy acceptance criteria.
6. Run relevant project checks and focused tests during implementation. Before declaring the issue done, run the required Django checks and full project test suite from the repository root:
   - `uv run python manage.py check`
   - `uv run python manage.py makemigrations --check --dry-run`
   - `uv run python manage.py test`
   Run any additional checks required by the issue. Resolve failures before declaring completion; report any blocker or limitation explicitly.
7. Commit meaningful implementation work in focused commits, excluding unrelated changes. Do not use issue-closing keywords in commit messages or pull request descriptions; the issue must remain open.
8. Add a comment to the GitHub issue summarizing what was implemented or reused, tests/checks run and their results, the commit reference(s), and any remaining limitation (or explicitly state that there are none). Verify that the issue remains open.

## Unclear or conflicting acceptance criteria

If an acceptance criterion is contradictory, impossible, or unclear after grooming, do not silently reinterpret it or change it. Add a comment to the GitHub issue identifying the criterion, explaining the problem, and stating what clarification is needed. Stop the affected implementation until the criterion is clarified through grooming; do not invent product behavior or claim the issue is done.

## Definition of done

- Every acceptance criterion is implemented or demonstrably already satisfied.
- Focused tests cover the new or verified behavior.
- Required Django checks and any additional issue-required checks pass.
- The full project test suite passes.
- Meaningful implementation work is committed.
- The GitHub issue remains open.
- An issue comment records what was implemented or reused, tests/checks and results, commit reference(s), and any remaining limitation.
