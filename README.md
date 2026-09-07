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
Basic task creation, household task lists/details, and atomic creation history are
also implemented (#6). Completion reviews, task editing/cancellation, scheduling,
and engagement features remain future work.

## Try the onboarding flow

After running migrations, provision a product administrator:

```sh
uv run python manage.py create_administrator admin@example.com --name Alex
```

The command prompts twice for a password without echoing it. It applies Django's
password validators and refuses duplicate emails; it does not grant staff or
superuser privileges or overwrite existing users.

Use an interactive terminal that supports hidden password entry; the command
refuses to continue if hidden input is unavailable. Email addresses are
case-insensitive, so `ADMIN@example.com` identifies the same account as
`admin@example.com`. Invalid email, mismatched passwords, and passwords rejected
by the configured validators leave no new account.

To exercise authentication alone, open http://127.0.0.1:8000/login/ and sign in
with the provisioned email and password. The protected home page is available
immediately, without creating a household. Choose **Sign out** in the navigation
bar to end the session and return to the shared sign-in page. Visiting
http://127.0.0.1:8000/ again redirects to sign-in. A product administrator cannot
access Django admin unless maintenance privileges are granted separately.

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

## Create and read household tasks

After applying migrations and inviting a member who has joined, choose **View
tasks** from the household home, then **Create task** as the administrator. Enter
a title, optionally a description, and choose an active household member. A
successful creation opens the task detail with its assignee, creation time, and
Pending status; the task and its creation-history event are stored together.

All active household members can read the household list and every task detail,
including assignments to other members. Only the administrator can create tasks.
An empty household list shows **No tasks yet**; the creation form explains when
there are no eligible members. Apply the additive migration with
`uv run python manage.py migrate`; existing households and memberships are retained.

Run focused task checks with `uv run python manage.py test chores.test_tasks`.

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

### Issue #2 verification (2026-09-06)

Reused the email backend, Django session views, shared Bootstrap templates,
account provisioning service, and existing identity migrations. Product pages
now require a linked Account even for users signed in through Django admin;
provisioning refuses password entry when the terminal cannot suppress echo.

- `uv run python manage.py test chores.test_authentication` passed all 8 focused
  tests, including actual migration execution against the temporary test database.
- `uv run python manage.py check` reported no issues.
- `uv run python manage.py makemigrations --check --dry-run` detected no changes.
- `uv run python manage.py test` passed all 34 tests.
- `git diff --check` passed.

No remaining issue #2 limitations. Existing data and migration history are
preserved; no new migration or dependency is needed.
