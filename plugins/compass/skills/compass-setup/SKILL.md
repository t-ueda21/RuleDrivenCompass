---
name: compass-setup
description: Install Compass guidance into the current project after the user asks to use, enable, or initialize Compass. Inspect the project, preserve existing instructions and hooks, and add only managed pointers plus a project-local profile when missing.
---

# Set up Compass in this project

Run only when the user asks to enable or initialize Compass in the current project. This setup enables both Codex and Claude Code, even when the user starts from only one of them.

1. Confirm the project root. Read existing AGENTS.md, CLAUDE.md, .compass files, README, package/build files, Git state, and existing test commands as needed to understand the project. Do not read secrets or private application data.
2. Identify the repository's purpose, current branch policy, technology stacks, established verification commands, and any existing project profile or Compass marker. Do not assume the source template's branch model or issue tracker.
3. Preserve existing files and settings. Do not rewrite AGENTS.md, CLAUDE.md, .claude/settings.json, IDE settings, Git configuration, hooks, CI, or unrelated files.
4. Ensure both product entry points can find the shared workflow:
   - AGENTS.md must contain one valid Compass managed block for Codex. Create the file only if absent.
   - CLAUDE.md must either contain one valid Compass managed block or already import AGENTS.md with a literal @AGENTS.md line. Create the file only if absent.
   - If CLAUDE.md is missing, create a short CLAUDE.md containing the same Compass managed block. Do this even when setup was invoked from Codex.
   - If CLAUDE.md has a literal @AGENTS.md import and AGENTS.md has the managed block, do not add a duplicate to CLAUDE.md.
   - In each file, append the block only when its exact markers are absent. If exactly one pair exists, replace only the text between that pair. If markers are duplicated, reversed, or incomplete, leave that file unchanged and explain the conflict. Preserve all content outside a valid block.

~~~markdown
<!-- COMPASS-PLUGIN:START -->
## Compass workflow

For every request in this project, follow the installed Compass plugin's compass-workflow skill. Before edits, identify the relevant repository purpose, branch policy, work mode, lifecycle phase, task type, and technology stack. Read only the selected shared rules. Preserve existing project instructions, settings, hooks, and unrelated changes. Verify changed behavior with the project's existing checks and report what actually ran. Keep project-specific settings and work records in this repository; shared Compass rules remain in the installed plugin.
<!-- COMPASS-PLUGIN:END -->
~~~

5. For project configuration, prefer the existing .compass/project-profile.json if present and leave it unchanged. Otherwise, use an existing .compass/plugin-config.json without rewriting it. If neither exists, create .compass/plugin-config.json with only observed values:

~~~json
{
  "schemaVersion": 1,
  "enabled": true,
  "projectName": "detected repository name",
  "branchPolicy": "inherit",
  "stacks": [],
  "verification": {
    "test": [],
    "lint": [],
    "typecheck": [],
    "build": []
  },
  "workRecordDirectory": "docs/compass/work"
}
~~~

Replace the example repository name and empty stack/check arrays only with facts found in project files. Keep commands as separate strings and copy existing commands verbatim. Do not make up checks. If the project name cannot be established, use null instead of a guess.
6. Do not create work records, design specs, hooks, or CI files during setup. The configured work-record directory is available for decisions or progress notes when later work calls for them.
7. Verify before reporting completion:
   - AGENTS.md has exactly one valid marker pair, unless a marker conflict was found.
   - CLAUDE.md has exactly one valid marker pair, or a literal @AGENTS.md import whose target AGENTS.md has the valid pair.
   - A newly created plugin-config.json parses as JSON.
   - Existing instructions outside managed blocks still appear unchanged.
8. Report which files were added or updated, which existing choices were detected, and that hooks/settings were left intact. If setup encountered a conflict, describe it without forcing a merge.

The Compass blocks are pointers to the installed skill, not copies of the shared rules. Plugin updates replace the shared workflow; they do not rewrite project profiles or work records.
