# ChoreHub — Shared Household Chores Manager

## Local development reference

Start with the [README quickstart](../README.md#quickstart). Python 3.14 and uv
manage the environment, Django is constrained to the 5.2 LTS series, and SQLite
requires no separate database service. Migrations initialize the ignored
`db.sqlite3`; retain it and apply additive migrations when updating the project.

The supplied settings use `DEBUG=True`, a development-only secret key, English,
and UTC. They are for local use; see the
[deployment boundaries](arch.md#development-and-deployment-boundaries) before hosting.

## Administrator provisioning and sign-in

After migrations, run:

```sh
uv run python manage.py create_administrator admin@example.com --name Alex
```

The command prompts twice without echoing the password and applies Django's
password validators. Use an interactive terminal that supports hidden input;
the command refuses to continue if it cannot hide the password. Invalid email,
duplicate email, mismatched passwords, or rejected passwords create no account.
Existing accounts are never overwritten or promoted.

Emails are case-insensitive: `ADMIN@example.com` and `admin@example.com` identify
the same product account. Visit `/login/` to sign in, then **Sign out** in the
navigation to end the session. The protected home is available before household
creation. A product administrator has no Django staff/superuser privileges;
`/admin/` retains its separate Django staff username login.

## Invitations and task assignments

Local invitation emails are printed to the server terminal. Open the acceptance
URL in a private browser window to try the member flow without replacing the
administrator's session. New members enter a name and matching passwords;
existing accounts sign in with the invited email and explicitly accept.

Invitations are single-use and fix the signup email and member role. A member
cannot join another household while an active membership exists. Administrator
accounts cannot accept member invitations.

At least one eligible member must join before the administrator can assign a
task. The creation form explains when none are available. All active household
members can read household tasks, including assignments to other members; only
the administrator creates or edits assignments. Follow the
[README user journey](../README.md#how-to-use) for completion and review.

## Invitation email configuration

Set environment variables before starting Django to deliver real invitations.
A `.env` file is not automatically loaded.

| Variable | Purpose / local default |
| --- | --- |
| `PUBLIC_BASE_URL` | Trusted invitation origin; `http://127.0.0.1:8000` |
| `EMAIL_BACKEND` | Console locally; use `django.core.mail.backends.smtp.EmailBackend` for SMTP |
| `DEFAULT_FROM_EMAIL` | Verified sender for SMTP; locally `household@example.com` |
| `EMAIL_HOST`, `EMAIL_PORT` | SMTP server and port; locally `localhost`, `25` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials; empty locally |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | Set the transport option required by the provider to `true`; both default to `false` and must not both be enabled |

The backend has a ten-second timeout. Failed delivery shows a retry message and
rolls back the invitation record. Email configuration alone does not make the
development settings suitable for deployment.

## Existing Django users and migrations

Django's default User table is retained. A linked product Account provides a
case-insensitive unique email and product role. Existing users with nonblank
emails receive member Account records during migration, preserving IDs,
usernames, passwords, and staff flags. Duplicate legacy emails stop that data
migration for manual resolution. Users without email keep their Django login
without receiving product access. No database reset is required.

## Assets and focused checks

Bootstrap 5.3.8 CSS is vendored with its MIT license in `chores/static/chores/`;
pages need no runtime CDN connection or Node build step.

Use the [standard validation commands](../README.md#testing) for the full project.
For focused development, pass a test module, for example:

```sh
uv run python manage.py test chores.test_tasks
```
