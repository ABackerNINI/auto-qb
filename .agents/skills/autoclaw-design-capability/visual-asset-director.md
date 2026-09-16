# Visual Asset Director

> This file is a visual-asset production rule module read by `REDESIGN.md`. It is not an independent Skill. Read it only when a page requires new or redesigned imagery, illustrations, banners, covers, or other visual assets.

## Goal

When a page requires supporting imagery, illustrations, covers, thumbnails, banners, or other visual assets, do not generate each asset independently. First establish a unified Visual Style Contract, then generate, review, and integrate all assets under the same rules.

The final result must ensure that:

- The imagery matches the overall visual character of the page
- Images on the same page belong to the same visual system
- Image composition fits the actual container and information hierarchy
- Images do more than merely exist; they improve the page's first impression
- Any image that fails review must be regenerated with a revised prompt

## Trigger Conditions

Execute this module only when:

- Important supporting imagery needs to be generated or redesigned
- A single design direction requires multiple visually consistent images
- Imagery is an important part of the hero section, brand expression, or overall page quality

When only a single simple icon, logo, or existing asset needs to be added, a style anchor and full asset manifest are not required.

## Core Process

1. Define the style before generating images.
2. Generate one style anchor before generating a series of images.
3. All images within a single design direction must share one Visual Style Contract.
4. When multiple design directions exist, each direction must have its own Visual Style Contract and independent image system.
5. Separate fixed style instructions from variable content instructions.
6. Images must pass individual-image review, set-consistency review, and full-page review.
7. Assets that fail the quality gate must not be integrated into the page or treated as complete.

## Multi-Direction Rules

When Redesign outputs three directions—A, B, and C—do not reuse one set of stylized imagery across all three.

Separate assets by direction:

```text
direction-a/visual-style-contract.md
direction-a/asset-manifest.json
direction-a/style-anchor.*
direction-a/assets/*

direction-b/visual-style-contract.md
direction-b/asset-manifest.json
direction-b/style-anchor.*
direction-b/assets/*

direction-c/visual-style-contract.md
direction-c/asset-manifest.json
direction-c/style-anchor.*
direction-c/assets/*
```

Only hard-inherited assets may be shared:

- Logos
- Brand marks
- Real product screenshots
- Assets the user explicitly requires
- Real case-study images
- Factual data visualizations

The following assets must not be shared across directions:

- Hero backgrounds
- Banners
- Mood imagery
- Illustrations
- Scene imagery
- Campaign covers
- Abstract key visuals
- Decorative visuals

Shared hard assets must be marked with `shared_hard_asset: true` in `asset-manifest.json`, together with the reason for reuse.

## Workflow

### 1. Read the Page and Design Context

First read:

- The current rendered page or page screenshots
- Existing project code, layout, and component structure
- Brand assets, logos, fonts, and existing imagery
- The Redesign direction and transformation mode
- The dimensions, aspect ratio, cropping behavior, and content purpose of each image container

Do not determine the image style in isolation from the page.

### 2. Establish the Global Visual Style Contract

Before generating any image, output and save a `visual-style-contract.md`. When multiple design directions exist, save a separate contract for each direction.

At minimum, include:

- Visual medium: photography, 3D, flat illustration, editorial illustration, abstract graphics, collage, etc.
- Overall tone: restrained, refined, experimental, warm, futuristic, etc.
- Color system: primary colors, supporting colors, neutrals, and prohibited colors
- Lighting rules: soft light, hard light, backlight, studio light, natural light, etc.
- Material rules: glass, paper, metal, fabric, matte surfaces, etc.
- Composition rules: subject scale, viewpoint, negative-space direction, and foreground / background relationships
- Detail density: low, medium, or high
- Image treatment: cropping, overlays, grain, sharpness, corner radius, and contrast
- Page integration: relationship to the background, typography, cards, and motion
- Prohibited elements:
  1. Irrelevant text inside the image
  2. Colors inconsistent with the page brand
  3. Mixed visual systems across images
  4. Meaningless patterns

### 3. Create the Visual Asset Manifest

During production, generate `asset-manifest.json` and record the following for each asset:

- `asset_id`
- `direction_id` — required for multiple directions
- Page and section
- Content objective
- Asset type
- Dimensions and aspect ratio
- Composition requirements
- Reference images
- Output path
- Current status
- Quality-review result

Do not generate images ad hoc while simultaneously writing the page.

### 4. Generate the Style Anchor

Apply the style-anchor constraint only when multiple images need to be generated.

Choose the single image that best defines the page's visual character, such as:

- The hero key visual
- The first campaign cover
- The most important case-study image
- The most representative illustration

Save the approved result as `style-anchor.*`.

The style anchor and all subsequent images must pass the following checks before batch generation continues:

- The anchor matches the page's visual direction
- Subsequent images match the visual tone of the anchor
- The color system is compatible with the page
- The composition fits the actual container
- The finish meets the quality required for a key page area
- No obvious AI artifacts are present
- The image has sufficient polish rather than placeholder-level quality

If the anchor fails, revise the prompt and regenerate it before continuing with batch generation.

### 5. Generate the Image Series

Within a single direction, all subsequent images must maintain consistency with the style anchor through:

- The same visual style
- A unified set of negative constraints

Each image prompt consists of two parts:

#### Fixed Section

Describe the style keywords shared across the full image system, matching the style anchor, together with the corresponding prohibited elements.

#### Variable Section

Describe only what must differ from the style anchor for the current image.

### 6. Check Visual Distinction Across Multiple Directions

- Confirm that images generated for A, B, and C each have an independent visual character
- Confirm that stylized imagery from one direction has not been reused in another
- Confirm that only hard-inherited assets are shared across directions

### 7. Review the Full Page

After integrating the imagery into the real page, inspect the final page screenshots and check:

- Whether the imagery improves the page's first impression
- Whether the imagery forms a unified visual language with the typography, background, cards, and motion
- Whether the imagery creates visual noise or competes with information
- Whether the set has appropriate rhythm and hierarchy
- Whether desktop and mobile crops are appropriate
- Whether overlays, grain, color grading, or contrast treatment should be standardized

If the full-page result fails, do not conceal the issue with CSS alone. Determine whether the problem comes from page treatment or from the image itself.

### 8. Apply the Quality Standards

Use the criteria below to assign one of three ratings:

- `Pass`: ready for delivery
- `Revise`: the direction is correct, but required issues remain
- `Reject`: the style or quality does not fit the current direction and must be redone

Review criteria:

#### Individual-Image Review

1. Accuracy of content expression
2. Fit with the page style
3. Composition and container fit
4. Color coordination with the page
5. Finish of lighting, materials, and texture
6. Detail quality and sharpness
7. Control of AI artifacts
8. Visual appeal and first impression

#### Set-Consistency Review

1. Consistent visual medium
2. Consistent color and color temperature
3. Consistent lighting
4. Consistent materials and rendering method
5. Consistent compositional density and camera language
6. Appropriate hierarchy and rhythm

#### Full-Page Review

1. Whether imagery supports the information hierarchy
2. Whether imagery is unified with the typography and component system
3. Whether imagery creates visual noise
4. Whether desktop and mobile crops are appropriate
5. Whether the page's first impression has improved significantly

#### Automatic Regeneration Conditions

Regenerate an asset if any of the following occurs:

- A single image clearly does not belong to the same visual system
- The imagery conflicts with the page background, typography, or component character
- The imagery is only placeholder quality
- A key subject is cropped or obscured
- Fake text, deformation, repeated structures, or obvious AI artifacts appear
- Different images use inconsistent lighting, materials, or illustration languages

### 9. Retry and Completion Conditions

Each image may be retried automatically for up to three rounds.

For each round, record:

- Why the previous result failed
- Which part of the prompt was changed
- Whether the new version improved

The module may end only when:

- All required visual assets have been generated and integrated
- All individual-image reviews pass
- All set-consistency reviews pass
