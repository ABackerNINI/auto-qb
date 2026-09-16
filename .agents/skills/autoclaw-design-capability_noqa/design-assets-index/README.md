# Design Assets Index

This directory is bundled as a workspace-local reference resource for Auto Designer's redesign workflow.

- `REDESIGN.md` and `UI-check.md` read `design-assets-index/SKILL.md` by relative path when external design assets are needed.
- The directory is intentionally outside `workspace/skills/`, so it is not injected into `<available_skills>` and cannot auto-trigger as a global Skill.
- User-provided and project-local assets always take priority.
- The license of each selected external asset must be verified independently.

The initial source list was adapted from the `design-assets-index` project by Ezra-Y and from the upstream awesome lists credited by that project. See `LICENSE` for the bundled index license.
