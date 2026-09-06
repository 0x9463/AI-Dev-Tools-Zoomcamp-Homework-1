# AI Dev Tools Zoomcamp 2026 — Homework 1

Homework 1 for the AI Dev Tools Zoomcamp 2026.

Project: shared household chores management application.

The project specification is available in `_docs/plan.md`.

## Local development

Prerequisite: install [uv](https://docs.astral.sh/uv/getting-started/installation/).
The project uses Python 3.14; uv can download it if it is not installed.

From the repository root:

```sh
uv sync --locked
uv run python manage.py migrate
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/ to see Django's default welcome page.
Stop the server with Ctrl+C. No virtual environment activation is needed.

## Bootstrap structure

- `config/`: Django project settings, URLs, and ASGI/WSGI entry points.
- `chores/`: registered Django application scaffold for future product work.
- `manage.py`: Django management command entry point.
- `pyproject.toml` and `uv.lock`: dependency requirements and exact resolved versions.
- `.python-version`: Python version used by uv.

Django is constrained to the 5.2 LTS series. SQLite keeps local setup self-contained;
`migrate` initializes Django's built-in tables in the ignored `db.sqlite3` file.
The generated settings are for local development, with `DEBUG=True` and a
development-only secret key. Language and time zone retain Django's defaults.

This step contains only the Django scaffold. Product models, views, templates,
and workflows from the specification have not been implemented.

## Verify the setup

```sh
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```
