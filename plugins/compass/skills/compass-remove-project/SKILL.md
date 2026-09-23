---
name: compass-remove-project
description: Remove Compass's managed pointers from the current project before uninstalling the plugin. Remove only complete COMPASS-PLUGIN marker blocks and preserve all project configuration, work records, settings, and hooks.
---

# Remove Compass from this project

Run only when the user asks to remove or disconnect Compass from the current project.

1. Inspect AGENTS.md and CLAUDE.md for the exact markers COMPASS-PLUGIN:START and COMPASS-PLUGIN:END.
2. In each file, remove the text from one complete start marker through its matching end marker, inclusive. Preserve all text outside the block. Trim at most one extra blank line at the join.
3. If markers are incomplete, duplicated, or reversed in a file, leave that file unchanged and report the issue.
4. Do not delete .compass/project-profile.json, .compass/plugin-config.json, docs/compass work records, settings, hooks, CI, or any other project content. Tell the user these project-owned files remain and can be reviewed separately.
5. Report the exact entry files whose managed blocks were removed.

Run this skill before disabling or uninstalling the plugin if the project pointer should also be removed. Removing the marketplace or plugin does not modify project files.
