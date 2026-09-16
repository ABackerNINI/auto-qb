# UI Completion Check - UI-check.md

> This is a workspace-local post-redesign rule file. Read it explicitly from `REDESIGN.md`; do not invoke it as a standalone Skill.

## Goal

Perform a final review and completion pass on the finished interface so that its visual consistency, multi-viewport responsiveness, interaction completeness, and implementation quality meet delivery standards.

The purpose of this review is not to redesign the page, but to identify and fix issues that reduce its level of polish.

## Review Boundaries

- Preserve the established design direction, content structure, and core user flows
- Do not arbitrarily rebuild the page or add irrelevant decoration
- Prefer reusing the project's existing components, variables, and design conventions
- Fix issues directly instead of only producing an audit report

## Review Order

### 1. Icons and Visual Assets

Check and fix:

- Whether icons come from a consistent icon library
- Whether icon size, stroke width, corner style, and visual weight are consistent
- Whether icons are correctly aligned with text, applying optical alignment when necessary
- Whether icon meanings are clear; important actions must not rely on icons alone
- Whether emoji have been incorrectly used as interface icons
- Whether images, illustrations, and logos are sharp, complete, and undistorted
- Whether image aspect ratios and crops suit their placement
- Whether images and illustrations on the same page share a consistent style
- Whether there are broken links, blurry images, or meaningless placeholder assets

Prioritize user-provided assets and assets already available in the project. When external assets need to be replaced, read `design-assets-index/SKILL.md` and verify the usage license of each specific asset.

### 2. Typography and Content

Check and fix:

- Text that is too small, lines that are too long, or content that is too dense
- Abnormal wrapping, truncation, overflow, or obscured content
- Whether labels and copy for buttons, forms, navigation, and states are clear and accurate
- Whether the selected fonts support the languages and characters actually used on the page
- Lorem Ipsum, meaningless placeholder copy, or obviously incorrect content

### 3. Color and Interface Styling

Check and fix:

- Whether text, icons, buttons, and backgrounds have sufficient contrast
- Whether success, warning, error, disabled, and selected states are easy to distinguish
- Meaningless gradients, excessive shadows, or stacked visual effects

Do not redefine the entire color system unless the current palette already harms readability or consistency.

### 4. Layout and Spacing

Check and fix:

- Whether content aligns correctly to the grid or a shared baseline
- Whether components of the same type follow consistent width, height, and arrangement rules
- Overlap, misalignment, overflow, clipping, or abnormal empty space
- Whether all content has been wrapped in unnecessary cards

Prioritize systemic issues that affect the entire page. Avoid arbitrary, one-off pixel adjustments.

### 5. Multi-Viewport Responsiveness

At minimum, check:

- Desktop
- Mobile
- Key intermediate widths when the page structure is complex

Ensure that:

- The page does not create unintended horizontal scrolling
- Content does not overlap, overflow, or get cropped incorrectly
- Navigation, tables, forms, dialogs, and primary actions remain usable
- Information order and priority remain sensible on smaller screens
- Font sizes, spacing, and touch targets are not too small
- Images preserve their correct aspect ratios
- Long text, different languages, and extreme data values do not break the layout
- Mobile layouts are meaningfully reorganized rather than merely scaled-down desktop layouts

## Validation Requirements

After fixing issues:

- Run or rebuild the project again
- Check the main pages and core interactions
- Confirm that style changes have not broken existing functionality
- Recheck the affected viewport sizes and components

If the environment supports page rendering and visual understanding, inspect screenshots of the actual interface.

If the current model does not support visual understanding, perform DOM, CSS, responsive layout, contrast, and interaction-state checks, and do not claim that screenshot-based visual validation has been completed.

## Completion Criteria

The review is complete only when:

- Icons, typography, colors, and component rules are consistent
- Both desktop and mobile interfaces are fully usable
- There are no obvious overlaps, overflows, misalignments, or missing content
- Required interaction states have been completed
- Visual assets are sharp and stylistically consistent
- Existing core functionality has not been broken
