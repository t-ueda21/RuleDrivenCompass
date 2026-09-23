# Repository guidance

This repository packages one shared Compass workflow for Claude Code and Codex. Keep the operating rules and their selection guide in one canonical skill directory under plugins/compass/skills/compass-workflow. Both marketplace manifests must continue to reference that same package.

The project setup skill may append only the marked Compass block and create a missing project-local profile. It must preserve existing instructions, settings, and hooks. Do not add executable hooks or copy private source histories, profiles, logs, generated scripts, or unrelated template files into this distribution.

Do not add a LICENSE or license metadata unless the rights holder supplies an explicit license. Keep store-submission status accurate and distinguish an available GitHub marketplace from an approved public directory listing.
