---
name: autoclaw-design-capability
description: Use this skill for UI, UX, product design, visual design, redesigning existing interfaces or codebases, HTML prototypes, dashboards, landing pages, reports, posters, and PPT/slides/deck deliverables. It routes the task through AutoClaw design rules, skeletons, design systems, craft guidance, and output frameworks so the current agent can complete the work directly without invoking the auto-designer agent.
---

# AutoClaw Design Capability

Use this skill when the current task needs a design deliverable: UI, UX, app/web prototype, dashboard, landing page, report, poster, visual artifact, PPT, slides, presentation, HTML deck, or a redesign of an existing interface or codebase.

Do not call or delegate to the `auto-designer` agent. The current agent completes the work directly by reading the files in this skill.

This skill is not for standalone image generation, image editing, logos, avatars, illustrations, or other requests whose primary deliverable is an image. Those tasks use the dedicated image-generation capability.

## Input Asset Understanding

When the host injects a valid `[图片参考描述]` block for screenshots, existing UI, PPT pages, product mockups, brand visuals, or other visual reference images, use that description directly and do not call image recognition again.

Only when that block is absent or explicitly says automatic recognition is unavailable, use `autoglm-image-recognition` to extract:

- screen/page type and visible content
- layout structure and visual hierarchy
- color, typography, spacing, and component patterns
- brand/style cues
- concrete issues, invariants, and reusable design constraints

Feed the host-provided or fallback recognition summary into the routing process. Do not rely only on the current model's visual interpretation.

## Required Start

For every supported design task:

1. Read `DESIGN.md`.
2. If the user supplied a PRD, QA, or product document, read `PRD_INGESTION.md`.
3. If an accessible codebase or project is part of the design task, read `CODE_INGESTION.md` to establish the current implementation baseline.
4. Read `TASK_ROUTER.md` and let it choose the Redesign branch or the standard three-axis route.

For a standard new Phase 1 task, read `INTERACTIONS.md` before generation and follow its `question-form` contract. After the interaction is complete, read `INDEX.md` and complete the three-axis route.

For Redesign, read `REDESIGN.md`; do not read `INDEX.md` or run the standard three-axis route unless `TASK_ROUTER.md` explicitly keeps the task on the standard branch.

Both branches must read `OUTPUT_RULES.md` before producing deliverables.

## Standard Route

Use `TASK_ROUTER.md` and `INDEX.md` to select:

1. The primary resource from `审美相关skill/design-skeletons/` or `审美相关skill/skills/`.
2. The design system from `审美相关skill/design-systems/`.
3. The required craft files from `审美相关skill/craft/`.

Do not list or load the entire resource tree. Prefer a design skeleton for a new visual artifact; use generic skills mainly for review, consultation, extraction, or fallback cases where no skeleton fits.

For PPT, slides, presentation, or deck requests, default to an HTML deck skeleton with `od.mode=deck` unless the user explicitly requests another supported form.

## Redesign Route

Follow `REDESIGN.md` for existing interfaces, codebases, screenshots, or visual references that must be preserved and improved.

- Read `visual-asset-director.md` when the page needs new or redesigned imagery.
- Read `UI-check.md` after implementation and fix the issues it identifies.
- Read `design-assets-index/SKILL.md` only when suitable user or project assets are unavailable; treat it as a local reference, not a globally invoked skill.

## Mandatory Reads Before Generation

For the standard route, read the selected resources before writing the deliverable:

- selected skeleton or skill `SKILL.md`
- selected skeleton `example.html`, when present
- selected design-system `DESIGN.md`, unless `OUTPUT_RULES.md` explicitly permits skipping it
- every selected craft file
- output framework files required by the selected resource's `od.mode`

For App-class prototype work that requires the two-file delivery pattern, read `infinite-canvas-output/SKILL.md` and use `infinite-canvas-output/assets/infinite-canvas-template.html` as the canvas base.

## Output Discipline

Follow `OUTPUT_RULES.md` for language, file naming, versioning, archive behavior, validation, intent alignment, and mode-specific delivery rules.

When selected resources conflict, follow the priority order in `OUTPUT_RULES.md`. Load only files required for the current route and task.
