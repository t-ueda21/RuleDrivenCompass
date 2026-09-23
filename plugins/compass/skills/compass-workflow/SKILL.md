---
name: compass-workflow
description: Apply Compass to every development request in a Compass-enabled project. Use for feature work, bug fixes, investigation, planning, documentation, testing, review, and delivery preparation. Classify the task, select only relevant rules, and verify the result.
---

# Compass workflow

Use this skill for ordinary work after Compass has been enabled in a project.

1. Read the Compass-managed block in the project guidance and the project-local file .compass/plugin-config.json when present. Treat project files as the source of project-specific paths, stack choices, and checks.
2. Inspect the requested area and existing changes. Identify the repository purpose, current branch and branch policy when Git is present, work mode, lifecycle phase, task type, and affected technology stack. Keep the classification short and do not print a checklist for a trivial request.
3. Read the selection guide at references/rule-index.md. Open only the matching operating rules in references/operating-rules.md and the relevant stack guidance in references/stacks.md.
4. Find an existing specification, acceptance criteria, issue, test command, or project convention before inventing one. Ask only when an unresolved choice could change the result or make the change unsafe.
5. Make the smallest coherent change that satisfies the request. Preserve unrelated edits and existing project instructions, settings, and hooks. Do not create commits, push, merge, open a pull request, deploy, or change remote state unless the user asks.
6. Run the existing checks that cover the changed behavior. Do not claim an unrun check passed. If a check is unavailable, report that clearly and give the command the user can run.
7. Report the change and its purpose, the checks actually run, and any remaining uncertainty. For multi-step work, keep project decisions and work records in the project, not in the installed plugin.

The plugin's shared rules live next to this skill. Do not copy them into the target repository. The project setup skill adds a small managed pointer to this workflow and keeps project-specific settings in the project.
