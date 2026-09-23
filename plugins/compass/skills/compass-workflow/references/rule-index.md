# Rule selection

Classify a request using only the dimensions that affect the work. Read the matching section in operating-rules.md; read the relevant stack notes in stacks.md when code, build, or runtime behavior depends on a technology.

## Repository purpose

- Application: make or maintain a product or service.
- Compass package: change the reusable workflow, plugin, or its documentation.
- Documentation-only: edit guidance without changing product behavior.

## Work mode

- Investigation: inspect, explain, or compare without changing files.
- Documentation: write or update documentation.
- Implementation: change product or developer tooling.
- Delivery preparation: review the final diff and prepare a handoff. Git or remote actions still require the user's request.

## Lifecycle phase

- Requirements: clarify users, goals, constraints, and acceptance conditions.
- Prototype: explore an uncertain idea and label disposable work clearly.
- Design: settle interfaces, data flow, failure behavior, and acceptance checks before a broad change.
- Implementation: make a focused change.
- Test: verify the requested behavior.
- Review: compare the diff with the request, security expectations, and test evidence.
- Delivery: summarize what is ready and what remains.

## Task type

Choose the affected area, not every possible type:

- docs: documentation, examples, release notes.
- frontend: browser or desktop UI.
- backend: application logic, services, storage.
- api: public or internal API behavior.
- db: schema, migration, query, or data integrity.
- test: test design or verification.
- git: repository metadata, branches, commits, or hosted review.
- stack: build tools, runtime, or project conventions.
- security: authentication, secrets, permissions, or sensitive data.
- review: assess a change without making it.

## Stack selection

Inspect project files and the local profile before selecting a stack. A project may have more than one. Read only the matching notes in stacks.md. If no bundled note covers the stack, follow the project's own documentation and existing scripts; do not invent commands.

## Selection rule

Start with the request and the files it touches. Combine the selected task type, lifecycle phase, and stack notes. If the task crosses areas, include the one or two additional rule sections that cover the risk. Do not read the whole catalog for every request.
