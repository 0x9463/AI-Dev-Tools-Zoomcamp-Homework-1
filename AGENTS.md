# Repository guidance

## Commands

Run from the repository root:

- Install/sync dependencies: `uv sync --locked`
- Start Django: `uv run python manage.py runserver`
- Run tests: `uv run python manage.py test`
- Check Django configuration: `uv run python manage.py check`
- Check for missing migrations without writing files: `uv run python manage.py makemigrations --check --dry-run`

## Rules

- Follow the issue workflow in [_docs/process.md](_docs/process.md).
- Manage dependencies with uv through `pyproject.toml` and `uv.lock`; keep both consistent when dependencies change.
- Keep changes within the current issue; do not silently expand scope.
- Preserve migration history and existing data unless the task explicitly requires otherwise.
- Inspect the working tree before editing and preserve unrelated changes.

## Documents

- [_docs/process.md](_docs/process.md): how work is organized.
- [_docs/plan.md](_docs/plan.md): product specification.
- [_docs/arch.md](_docs/arch.md): architecture and technical decisions.
- [_docs/backlog.md](_docs/backlog.md): backlog index; GitHub Issues are the canonical active tasks.
