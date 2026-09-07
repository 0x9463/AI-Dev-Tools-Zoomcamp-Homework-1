# ChoreHub — Shared Household Chores Manager

## 1. Objective

Build an application for a single household/family group, in which an administrator organizes household chores, assigns members, tracks deadlines and recurrence, validates completions, and maintains a simple points and ranking system.

The MVP must prioritize operational clarity, administrator control, and a simple workflow for members.

---

## 2. Roles

### 2.1 Administrator

The administrator is responsible for:

- creating and managing the household;
- inviting members;
- creating, editing, deleting, and reassigning tasks;
- setting priority, category, deadline, recurrence, and points;
- approving or rejecting tasks marked as completed;
- tracking Pending, Overdue, and Awaiting approval tasks;
- viewing history and rankings.

### 2.2 Member

A member can:

- view all household tasks;
- modify only tasks assigned to them;
- mark their tasks as completed;
- attach an optional photo;
- comment on their tasks;
- request an assignee swap with a justification;
- track their own calendar;
- view rankings.

---

## 3. Accounts and access

### 3.1 Household structure

- Each administrator account manages only one household.
- The administrator is solely responsible for adding members.
- Members join only through an invitation sent by email.

### 3.2 Member signup

An invited member can create an account using:

- email and password; or
- social login.

### 3.3 Added critical rule

To simplify the MVP:

- a member cannot join another household while linked to the current household;
- members cannot leave the household on their own in the MVP;
- only the administrator can remove them.

**Rationale:** this avoids conflicts involving ownership, history, points, and permissions in the first version.

---

## 4. Tasks

### 4.1 Creation

Only the administrator can create tasks.

Each task must have:

- a title;
- an optional description;
- an assignee;
- a category;
- a priority;
- points;
- an optional deadline;
- optional recurrence;
- a creation date;
- a status.

### 4.2 Priority

Available values:

- Low
- Medium
- High
- Urgent

### 4.3 Categories

The system must offer initial categories, for example:

- Cleaning
- Kitchen
- Shopping
- Organization

The administrator can also create new categories.

### 4.4 Deadline

The deadline is optional.

A task with a deadline that passes its due date/time without completion must automatically be marked as **Overdue**.

### 4.5 Recurrence

The MVP must support:

- daily;
- weekly;
- monthly;
- specific days of the week.

### 4.6 Added critical rule for recurrence

Each recurring occurrence must generate its own task instance.

Example:

> “Wash the dishes — every Monday”

Each Monday generates a new, independent occurrence, preserving the history of previous ones.

**Rationale:** repeatedly editing the same task would destroy its history and undermine the rankings.

---

## 5. Task statuses

The MVP must use the following statuses:

1. **Pending** — created and not yet completed;
2. **Overdue** — deadline passed without completion;
3. **Awaiting approval** — member reported completion;
4. **Completed** — administrator approved;
5. **Canceled** — administrator canceled the task.

### 5.1 Completion rejection

When the administrator rejects a completion:

- a comment is required;
- the task returns to **Pending**;
- the comment is recorded in the history.

If the original deadline has already passed, it returns as **Overdue**.

---

## 6. Completion workflow

1. The member performs the task.
2. They can add a comment.
3. They can attach an optional photo.
4. They mark the task as completed.
5. The status changes to **Awaiting approval**.
6. The administrator reviews it.
7. The administrator can:
   - approve; or
   - reject with a required comment.
8. Points are credited only after approval.

---

## 7. Editing and reassignment

The administrator can edit any task field at any time.

They can also reassign the task to another member at any time.

### 7.1 Added critical rule

Every relevant change must record:

- who made the change;
- date/time;
- previous value;
- new value.

This applies especially to:

- assignee;
- deadline;
- priority;
- points;
- status.

**Rationale:** because the administrator can edit tasks even after assignment, a small change history prevents inconsistencies and disputes.

---

## 8. Swap requests

A member can ask the administrator for a task swap.

The request must contain:

- task;
- requesting member;
- required justification;
- request date;
- request status.

Possible statuses:

- Pending
- Accepted
- Declined

Only the administrator decides whether the swap will take place.

---

## 9. Comments and attachments

### 9.1 Comments

The following can comment:

- administrator;
- member assigned to the task.

Other members can view the task but cannot comment.

### 9.2 Photos

The assignee can attach an optional photo as evidence of the work performed.

### 9.3 Suggested MVP limitation

Allow at most one image per completion submission.

**Rationale:** this reduces storage and interface complexity without preventing the main use case.

---

## 10. Points

Each task has a point value.

The system suggests an initial point value based on priority:

| Priority | Suggested points |
|---|---:|
| Low | 5 |
| Medium | 10 |
| High | 20 |
| Urgent | 30 |

The administrator can change the suggested value before or after creating the task.

Points are credited only when the task is approved.

### 10.1 Added critical rule

After a task is approved, the points recorded for that completion are frozen for historical purposes.

Future changes to the recurring task's default value affect only new occurrences.

**Rationale:** this prevents retroactive changes to rankings that have already been calculated.

---

## 11. Rankings

The system must display:

- weekly rankings;
- monthly rankings;
- overall cumulative rankings.

Rankings are based exclusively on points from approved tasks.

There are no rewards or point redemptions in the MVP.

### 11.1 Suggested tie-break rule

When points are tied:

1. the greater number of approved tasks takes precedence;
2. if the tie remains, both occupy the same position.

---

## 12. Task views

All members can view all household tasks.

However:

- members can modify only tasks assigned to them;
- the administrator can modify any task.

### 12.1 Administrator filters

The administrator can filter by:

- status;
- assignee;
- priority;
- category.

---

## 13. Calendar

### Administrator

Can view all tasks in a calendar with:

- daily views;
- weekly views;
- monthly views.

### Member

Sees only their own tasks in the calendar.

The calendar must show tasks:

- with deadlines;
- with recurrence.

---

## 14. Administrator dashboard

The administrator dashboard must display at least:

- number of Pending tasks;
- number of Overdue tasks;
- number Awaiting approval;
- list of tasks requiring approval;
- upcoming tasks with deadlines.

Advanced charts and performance indicators are outside the MVP scope.

---

## 15. History

The administrator can view a complete history containing:

- completed tasks;
- rejected tasks;
- overdue tasks;
- assignees;
- completion and approval dates;
- points awarded;
- rejection comments;
- relevant changes.

### Added critical rule

Completed tasks must not be physically deleted by the system.

When necessary, they remain recorded in the history.

**Rationale:** history and rankings depend on these records.

---

## 16. Notifications

The MVP must generate notifications when:

- a task is assigned to a member;
- a deadline is approaching.

### Suggested rule for approaching deadlines

Treat “approaching the deadline” as **24 hours beforehand**.

For tasks due less than 24 hours after creation, send only the assignment notification.

### Suggested technical scope

In the MVP, notifications can be internal to the application itself.

Email, push notifications, and WhatsApp are left for future versions.

**Rationale:** this reduces external dependencies and keeps the focus on the main workflow.

---

## 17. Minimum screens

### Public

1. Login
2. Invitation-based signup
3. Password recovery

### Administrator

4. Dashboard
5. Task list
6. Create/edit task
7. Task details
8. Pending approvals
9. Calendar
10. Household members
11. Categories
12. Rankings
13. History

### Member

14. My Tasks
15. Task details
16. Submit completion
17. Request swap
18. My calendar
19. Rankings
20. Notifications

---

## 18. Main entities

A minimal data structure can contain:

### User

- id
- name
- email
- password/auth_provider
- role
- created_at

### Household

- id
- name
- admin_id

### HouseholdMember

- household_id
- user_id
- joined_at
- active

### Task

- id
- household_id
- title
- description
- category_id
- priority
- assigned_user_id
- due_at
- recurrence_type
- recurrence_config
- suggested_points
- points
- status
- created_at
- updated_at

### TaskCompletion

- id
- task_id
- submitted_by
- submitted_at
- comment
- attachment
- approval_status
- reviewed_by
- reviewed_at
- rejection_comment
- awarded_points

### Category

- id
- household_id
- name
- is_default

### Comment

- id
- task_id
- user_id
- content
- created_at

### SwapRequest

- id
- task_id
- requested_by
- justification
- status
- reviewed_by
- reviewed_at

### Notification

- id
- user_id
- type
- message
- read
- created_at

### TaskHistory

- id
- task_id
- changed_by
- event_type
- previous_value
- new_value
- created_at

---

## 19. Permission rules summary

| Action | Administrator | Assigned member | Other member |
|---|:---:|:---:|:---:|
| View task | ✓ | ✓ | ✓ |
| Create task | ✓ | ✗ | ✗ |
| Edit task | ✓ | Limited | ✗ |
| Delete/cancel task | ✓ | ✗ | ✗ |
| Reassign task | ✓ | ✗ | ✗ |
| Mark as completed | ✓ | ✓ | ✗ |
| Approve completion | ✓ | ✗ | ✗ |
| Reject completion | ✓ | ✗ | ✗ |
| Comment | ✓ | ✓ | ✗ |
| Request swap | ✗ | ✓ | ✗ |
| View rankings | ✓ | ✓ | ✓ |

---

## 20. Outside the MVP scope

To keep the work manageable, the following are explicitly outside the first version:

- multiple households per user;
- members participating in multiple households;
- direct task swaps between members;
- private chat;
- rewards for points;
- badges/achievements;
- artificial intelligence for task assignment;
- automatic assignment;
- geolocation;
- integration with external calendars;
- WhatsApp/SMS notifications;
- advanced analytics;
- productivity charts;
- multiple attachments per completion;
- task dependencies;
- subtasks;
- rewards marketplace;
- payments.

---

## 21. MVP success criteria

The MVP can be considered functional when this scenario can be carried out in full:

1. The administrator creates a household.
2. Invites a member by email.
3. The member creates an account and joins the household.
4. The administrator creates a task and assigns it to the member.
5. Sets priority, category, points, and deadline.
6. The member receives the task.
7. The member marks the task as completed and optionally submits a photo/comment.
8. The administrator receives the completion for validation.
9. The administrator approves or rejects it.
10. If approved, the points count toward the rankings.
11. If rejected, the task returns for another attempt with the justification recorded.
12. The administrator can view the history.
13. Recurring tasks generate new occurrences correctly.
14. The calendar and notifications reflect the relevant deadlines.

---

## 22. Implementation priority

### P0 — Essential workflow

- authentication;
- household and members;
- invitations;
- task CRUD;
- assignment;
- statuses;
- completion;
- approval/rejection;
- basic history.

### P1 — Organization

- categories;
- priorities;
- deadlines;
- recurrence;
- filters;
- calendar.

### P2 — Engagement

- points;
- rankings;
- comments;
- evidence photo;
- swap requests;
- internal notifications.

---

## 23. Product summary

The product is a household management application centered on the administrator. The administrator organizes and assigns tasks, while members perform them and submit their completions for validation.

The main difference from an ordinary task list is the combination of:

- individual responsibility;
- validation of the work performed;
- auditable history;
- recurring tasks;
- calendar;
- points and rankings.

This combination is sufficient to produce a demonstrable MVP without introducing unnecessary complexity such as multiple households, intelligent assignment, rewards, or external integrations.
