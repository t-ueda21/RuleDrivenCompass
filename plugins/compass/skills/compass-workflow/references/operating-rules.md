# Operating rules

## Safe work start

- Check the repository state and current edits before changing files.
- Preserve edits whose owner or purpose is unclear; do not stage, revert, or overwrite them.
- Follow an existing branch policy. If none is documented, do not force a branch model such as main/develop/prototype.
- If work is requested on a protected branch, use the project's documented route. Do not make up a branch or commit policy.
- Keep the requested app change separate from optional Compass improvements.

## Scope and design

- For a small, clear change, inspect the relevant code, make the change, and verify it.
- For a change with several components or unresolved product choices, first summarize the goal, scope, design, and acceptance checks. Resolve material uncertainty before changing files.
- Use the project's existing design specification and issue workflow when they apply. Do not add process documents just to satisfy Compass.
- Break larger work into reviewable pieces. Record decisions and progress in the project location configured by the maintainers.

## Implementation

- Follow the project's existing naming, architecture, formatting, runtime, package manager, and dependency conventions.
- Avoid unrelated refactoring and unnecessary dependencies.
- Do not replace or rewrite AGENTS.md, CLAUDE.md, IDE settings, tool configuration, or Git hooks as part of ordinary work.
- Do not copy Compass rule files into the project. Installed plugin content is the shared source; the project keeps its local profile and work records.

## Verification and review

- Tie checks to changed behavior and existing acceptance conditions.
- Prefer the narrowest meaningful existing test, lint, type check, or build command.
- For user-visible UI, inspect the changed state at relevant screen sizes and check keyboard access and error or empty states when applicable.
- Review the final diff for scope, secrets, generated files, and accidental changes.
- Report exact results. State why checks were skipped or could not run.

## Security and external state

- Do not expose, copy, or commit secrets, credentials, private records, or production data.
- Do not run a deployment, migration against live data, remote issue mutation, push, merge, or pull-request action unless requested.
- Distinguish a prepared command or draft from an operation that actually ran.
