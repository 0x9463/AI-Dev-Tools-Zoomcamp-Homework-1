# ChoreHub — Shared Household Chores Manager

ChoreHub helps families and housemates coordinate shared chores. A household
administrator invites members, assigns tasks, and reviews completion; members
see household responsibilities, find their own tasks, and submit work for approval.

Built as **Homework 1 of the AI Dev Tools Zoomcamp 2026 by DataTalksClub**, using
Codex CLI and an AI-native development workflow.

[Course](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) ·
[Product specification](_docs/plan.md) · [Architecture](_docs/arch.md) ·
[GitHub Issues](https://github.com/0x9463/chorehub/issues) · [Backlog index](_docs/backlog.md)

## Problem

Shared chores become difficult to coordinate when assignments and progress are
scattered across conversations. ChoreHub gives a household one place to see who
is responsible and whether submitted work has been accepted or needs another attempt.

## Current Features

- Email/password sign-in and sign-out, with command-line administrator provisioning.
- Household creation and single-use invitations for member signup or acceptance
  by an existing account; members have one active household.
- Administrator task creation with a title, optional description, and active member assignment.
- Household task lists and details, plus a member's **My Tasks** view.
- Completion submission by the responsible member or administrator, followed by
  administrator approval or rejection with a required reason. Rejected tasks return
  to Pending and can be resubmitted.
- Completion attempts and review outcomes displayed on task details; task changes
  and history events saved atomically.
- Administrator task editing and reassignment, preserving workflow state and reviews.
- Server-side household isolation, role checks, and CSRF protection for changes.

**Testing evidence:** the latest recorded Engineer run passed **90 tests** at
revision `be93663f69cc3d3df0c93d605f2ea553ead73fd9` on September 7, 2026.
See [Testing](#testing) for provenance and commands.

## Demo

Screenshots will be added. Planned captures cover sign-in, household home,
member invitations, and task details, under `_docs/images/`.

## Quickstart

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The project
uses **Python 3.14, Django 5.2, and SQLite**; uv can download Python if needed.

```sh
git clone https://github.com/0x9463/chorehub.git
cd chorehub
uv sync --locked
uv run python manage.py migrate
uv run python manage.py create_administrator admin@example.com --name Alex
uv run python manage.py runserver
```

Provisioning prompts twice for a password in an interactive terminal. It creates
a product administrator without Django staff/superuser privileges. Open
[http://127.0.0.1:8000/](http://127.0.0.1:8000/) and sign in with that email and
password. No environment activation is needed; Ctrl+C stops the server.

SQLite uses the ignored `db.sqlite3`. Settings are for local development.
See [local development](_docs/local-development.md) for provisioning details,
email configuration, and existing-account migrations.

## How to use

1. Provision an administrator, sign in, and create a household.
2. Choose **Invite a member** and enter a different email. Locally, emails appear
   in the server terminal; copy the acceptance URL.
3. Open it in a private browser window. New members supply a name and password;
   existing accounts sign in with the invited email and explicitly accept.
4. As administrator, open **View tasks → Create task** and assign a chore to the
   member who joined. Inspect or edit it from task details.
5. As member, open **My Tasks**, inspect the chore, and choose **Submit completion**.
6. As administrator, open **Pending approvals**. Approval completes the task;
   rejection requires a reason and permits another attempt, retaining earlier reviews.

## Testing

```sh
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test
```

The [latest recorded Engineer verification](https://github.com/0x9463/chorehub/issues/11#issuecomment-5572918472)
reports **90 tests passed**, no Django configuration issues, and no missing
migrations at revision `be93663f69cc3d3df0c93d605f2ea553ead73fd9` on September 7,
2026. This documentation update does not rerun the suite.
[Issue #11](https://github.com/0x9463/chorehub/issues/11) remains open pending
independent QA; the recorded Engineer result is not a QA verdict.

Coverage includes authentication, legacy identity preservation, onboarding,
household isolation, task editing, completion/review transitions, repeated
requests, rollback, and CSRF enforcement. Tests create their own data in a
separate test database. Detailed implementation and independent QA evidence
remain in [GitHub Issues](https://github.com/0x9463/chorehub/issues?q=is%3Aissue).

## Architecture

A single Django application serves templates and forms with vendored Bootstrap
CSS. Views enforce household access; shared services apply business rules and
transactions; Django's ORM persists data in SQLite. No frontend build step or
runtime CDN connection is needed.

Django's default User handles passwords and sessions. A linked product `Account`
stores a case-insensitive unique email and role; product email login is separate
from Django admin's username login. uv manages the Python environment and locked
dependencies. See [architecture](_docs/arch.md) for details and planned extensions.

## Project Structure

```text
config/          Django settings, root URLs, ASGI/WSGI entry points
chores/          Models, services, forms, views, templates, assets, migrations, tests
_docs/           Specification, architecture, backlog, process, local setup
team/            PM, Software Engineer, QA, and Orchestrator agent role instructions
AGENTS.md        Repository guidance and context map for agents
manage.py        Django management entry point
pyproject.toml   Project metadata and dependency requirements
uv.lock          Exact dependency resolution
.python-version  Python version selected for uv
```

## AI-Native Development Workflow

This repository intentionally practices an AI-native workflow. ChatGPT served as
the learning/tutoring and brainstorming interface. Codex CLI was the coding agent
used to implement and evolve the application under human-directed requirements,
supervision, and validation. The human author directed product decisions, scope,
requirements, workflow design, supervision, validation, and learning throughout the project.

The initial idea became a product specification and GitHub Issues as the canonical
backlog. **Context engineering** stores persistent project knowledge in `AGENTS.md`,
`_docs/`, and `team/`. Product Manager grooming establishes acceptance criteria;
the Software Engineer implements them; independent QA validates those criteria.

The **Orchestrator** coordinates separate role agents and explicit handoffs.
**Loop engineering** is the Engineer → QA → correction → QA cycle until PASS or
a genuine blocker. **Graph engineering** connects readiness, PM clarification
when needed, implementation, QA, and escalation through explicit role transitions.
A QA PASS applies only to the exact reviewed revision; implementation alone is not considered completion.

See the [development process](_docs/process.md) and [role instructions](team/).
Open issues track remaining implementation and QA work.

## Key Decisions and Trade-offs

- **Django + SQLite:** reproducible local setup in one application; reconsider
  PostgreSQL if concurrency or deployment needs justify it.
- **Preserve working code and data:** reuse existing behavior and retain migration
  history, including legacy Django users.
- **Server-side permissions and transactions:** enforce household boundaries and
  commit task changes with their history.
- **Canonical issues and isolated roles:** keep requirements and evidence in GitHub,
  with QA independent of implementation and explicit handoffs.

These decisions are documented in the [architecture](_docs/arch.md) and
[development process](_docs/process.md).

## Current Limitations

The full product specification extends beyond the subset implemented for Homework 1.
Cancellation, member management, a full task-history screen, dashboard, and password
recovery remain planned. Categories, priorities, deadlines, recurrence, filters,
calendars, points/rankings, comments/photos, swaps, and internal notifications are
also future work.

The supplied configuration uses local development settings and console email;
no hosted deployment is provided. Member signup requires invitations. See the
[remaining GitHub Issues](https://github.com/0x9463/chorehub/issues) for roadmap
and QA status.

## Course / Homework Context

**AI Dev Tools Zoomcamp 2026 · DataTalksClub · Homework 1 — AI-Native Developer Workflow**

The homework started with the deliberately vague prompt:

> A tool for managing shared household chores

The exercise turned it into a specification, backlog, Django application, tests,
and an AI-native development workflow. Codex CLI was the selected coding agent.
See the [homework assignment](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/cohorts/2026/01-ai-native-workflow/homework.md).

## Documentation

- [Product specification](_docs/plan.md)
- [Architecture](_docs/arch.md)
- [Backlog index](_docs/backlog.md) and [GitHub Issues](https://github.com/0x9463/chorehub/issues)
- [Local development and email configuration](_docs/local-development.md)
- [Development process](_docs/process.md)
- [Repository agent guidance](AGENTS.md) and [Orchestrator role](team/orchestrator.md)
