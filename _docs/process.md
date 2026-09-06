# Development process

- GitHub Issues are the canonical active backlog; [backlog.md](backlog.md) is an index of links.
- Work on one issue at a time. Read its current description and acceptance criteria before starting; confirm that its prerequisites exist.
- Read only the additional project documents relevant to the task, using the document map in [AGENTS.md](../AGENTS.md).
- When an issue requires product clarification, use the [Product Manager role](../team/pm.md) before implementation. The PM rewrites the GitHub issue itself using the [task-grooming template](task_grooming_template.md); the issue remains the canonical task. Resolve questions that affect expected behavior or acceptance criteria before implementation. The PM does not implement or test the feature.
- Use the [Software Engineer role](../team/software-engineer.md) to implement one groomed issue at a time according to its acceptance criteria and documented constraints, without changing the criteria. If a criterion is contradictory, impossible, or unclear after grooming, comment on the issue explaining the problem and stop the affected implementation until clarified.
- Do not silently expand scope. Raise missing requirements or additional work explicitly before including them in the current issue.
- Commit regularly after meaningful changes, keeping commits focused on the issue and excluding unrelated work.
- Run the tests and checks appropriate to the change and complete the issue's required workflow. Record validation results and any remaining limitations.
- The Engineer leaves the issue open, including after implementation and validation are complete, and adds an issue comment summarizing what was implemented or reused, tests/checks and results, commit reference(s), and any remaining limitation. Follow the role's definition of done before reporting completion.
