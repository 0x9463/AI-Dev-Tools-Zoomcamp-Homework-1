# AI Dev Tools Zoomcamp 2026 — Homework 1

Homework 1 for the AI Dev Tools Zoomcamp 2026.

Project: shared household chores management application.

Project documentation: [product specification](_docs/plan.md),
[architecture](_docs/arch.md), and [backlog](_docs/backlog.md).

## Local development

Prerequisite: install [uv](https://docs.astral.sh/uv/getting-started/installation/).
The project uses Python 3.14; uv can download it if it is not installed.

From the repository root:

```sh
uv sync --locked
uv run python manage.py migrate
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/ to reach the email sign-in page.
Stop the server with Ctrl+C. No virtual environment activation is needed.

## Bootstrap structure

- `config/`: Django project settings, URLs, and ASGI/WSGI entry points.
- `chores/`: product accounts, households, memberships, invitations, forms, templates, and tests.
- `manage.py`: Django management command entry point.
- `pyproject.toml` and `uv.lock`: dependency requirements and exact resolved versions.
- `.python-version`: Python version used by uv.

Django is constrained to the 5.2 LTS series. SQLite keeps local setup self-contained;
`migrate` initializes Django's built-in and product tables in the ignored `db.sqlite3` file.
The generated settings are for local development, with `DEBUG=True` and a
development-only secret key. Language and time zone retain Django's defaults.

Implemented scope: backlog items #1–5 (bootstrap test, email authentication,
household creation, invitation sending, and invitation acceptance).
Chore management, completion reviews, scheduling, and engagement features remain future work.

## Try the onboarding flow

After running migrations, provision a product administrator:

```sh
uv run python manage.py create_administrator admin@example.com --name Alex
```

The command prompts twice for a password without echoing it. It applies Django's
password validators and refuses duplicate emails; it does not grant staff or
superuser privileges or overwrite existing users.

1. Run the server and sign in with that email and password.
2. Create a household, then choose **Invite a member** and enter a different email.
3. Copy the invitation URL printed in the server terminal by the console email backend.
4. Open it in a private browser window, enter a name and matching passwords, and join.
5. For an existing account, sign in with the invited email and explicitly accept the invitation.

Each invitation can be accepted once. Members cannot join a second household while
their membership is active, and the invite fixes the signup email and member role.
Administrator accounts cannot join households as members. The built-in `/admin/`
login remains separate and accepts Django staff usernames.

The project retains Django's default User table and uses a linked Account for
case-insensitive unique email identities and product roles. Existing users with
nonblank emails receive member Account records during migration, with IDs,
usernames, passwords, and staff flags preserved. Duplicate legacy emails stop the
data migration for manual resolution; users without email retain their existing
Django login but do not acquire product access. No database reset is required.

## Invitation email configuration

Local email is printed to the console. To send real invitations, set environment
variables before starting Django (a `.env` file is not automatically loaded):

| Variable | Purpose / local default |
|---|---|
| `PUBLIC_BASE_URL` | Trusted invitation origin; `http://127.0.0.1:8000` |
| `EMAIL_BACKEND` | Console locally; use `django.core.mail.backends.smtp.EmailBackend` for SMTP |
| `DEFAULT_FROM_EMAIL` | Verified sender for SMTP; locally `household@example.com` |
| `EMAIL_HOST`, `EMAIL_PORT` | SMTP server and port; locally `localhost`, `25` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials; empty locally |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | Set the transport option required by the provider to `true`; both default to `false` and must not both be enabled |

The backend has a ten-second timeout. Failed delivery shows a retry message and
rolls back the invitation record. The generated settings still target local
development; deployment requires the configuration described in [_docs/arch.md](_docs/arch.md).

Bootstrap 5.3.8 CSS is vendored in `chores/static/chores/` with its MIT license so
pages do not need a runtime CDN connection or Node build step.

## Verify the setup

```sh
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test
```

The suite includes the original database-free admin login smoke test plus tests
for email authentication, administrator provisioning, household isolation,
invitation delivery/signup, single-use acceptance, active membership constraints,
CSRF protection, and preservation of legacy accounts. Tests create their own data
in a separate temporary database and do not require manually provisioned users.

To run just the bootstrap smoke test from issue #1:

```sh
uv run python manage.py test chores.tests.ProjectSmokeTests
```

### Issue #1 verification (2026-09-06)

The existing scaffold already supplies the bootstrap requirements; later product
features and migrations are retained. Verified with Python 3.14.4 and Django 5.2.17:

- `uv sync --locked` completed successfully.
- `uv run python manage.py migrate` completed with no pending migrations.
- `uv run python manage.py check` reported no issues.
- `uv run python manage.py makemigrations --check --dry-run` detected no changes.
- `uv run python manage.py test` passed all 26 tests, including the admin login smoke test.
- `uv run python manage.py runserver 127.0.0.1:8011 --noreload` served
  `/admin/login/` with HTTP 200; the server was stopped after verification.
