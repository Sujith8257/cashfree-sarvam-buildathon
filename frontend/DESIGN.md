---
name: Cashfree
description: A calm collections register for borrower context and follow-up.
colors:
  primary: "#286d52"
  primary-hover: "#205740"
  primary-active: "#204735"
  rail: "#173d36"
  rail-selected: "#325a4a"
  sage: "#eaf0e3"
  canvas: "#f5f7f6"
  surface: "#ffffff"
  surface-soft: "#f8faf9"
  ink: "#20362b"
  muted: "#65746c"
  line: "#e2e8e4"
  accent-soft: "#eaf3ee"
  dark-canvas: "#102019"
  dark-surface: "#192c22"
  dark-surface-soft: "#20362a"
  dark-ink: "#edf3ef"
  dark-muted: "#a5b8ac"
  dark-line: "#30483a"
  dark-accent: "#8fcbb0"
  dark-accent-soft: "#294b38"
typography:
  headline:
    fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif'
    fontSize: "29px"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.8px"
  metric:
    fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif'
    fontSize: "32px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.8px"
  title:
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.2px"
  body:
    fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif'
    fontSize: "16px"
    lineHeight: 1.5
  label:
    fontSize: "12px"
rounded:
  control: "6px"
  navigation: "7px"
  container: "8px"
  panel: "10px"
  dialog: "12px"
  pill: "9999px"
spacing:
  small: "8px"
  control: "12px"
  medium: "16px"
  panel: "24px"
  page: "40px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.container}"
    padding: "8px 16px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
  navigation-active:
    backgroundColor: "{colors.rail-selected}"
    textColor: "{colors.surface}"
    rounded: "{rounded.navigation}"
    padding: "12px 13px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "21px 23px 7px"
  input:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "4px 12px"
    height: "36px"
---

# Design System: Cashfree

## Overview

**Creative North Star: "The Collections Register"**

A forest-green navigation rail frames a quiet, daytime working surface. Compact controls, ruled rows, and aligned amounts make borrower context easy to scan. The optional dark theme preserves the same hierarchy through deep green surfaces.

**Key Characteristics:**
- Forest rail and sage portfolio emphasis.
- Restrained borders and shallow depth.
- Compact operational typography and tabular amounts.
- Code-drawn interface with SVG icons; no raster artwork ships.

## Colors

### Primary
Forest green carries primary actions, selected filters, and text actions. The rail uses a deeper forest; sage distinguishes the principal portfolio metric. Existing Tailwind `blue` tokens are remapped to greens, so their names do not imply a blue visual accent.

### Neutral
Canvas, surface, soft surface, ink, muted text, and line tokens establish the light workspace. Their dark counterparts are implemented through CSS custom-property overrides. Shared Tailwind components also use the green-tinted slate scale.

Semantic badges retain emerald for paid/completed, amber for busy, rose for failed/disputed/refused, purple for promises, and the remapped green scale for pending review. Pair status color with visible labels and icons.

**The Context Rule.** Keep semantic status colors attached to the status they describe.

## Typography

Segoe UI with Helvetica Neue, Arial, and sans-serif fallbacks supplies the whole interface. Page headings use the headline token; section headings use the title token, with borrower-directory headings at 18px. Supporting copy is commonly 12–14px, and record tables use 13px. Mobile page headings reduce to 26px.

Portfolio values use the metric token and tabular numerals, increasing to 36px above the wide breakpoint. Right-aligned table amounts and queue balances also use tabular numerals. There is no separate display face or editorial type system.

The balance bar is labeled “Outstanding / principal”; promise totals describe recorded commitments. Preserve these explicit metric labels when presenting the same figures.

## Layout

Desktop uses a fixed 244px left rail, 76px topbar, and a centered content area capped at 1640px with 40px side padding. The portfolio summary combines a sage field with three metrics; supporting panels use an asymmetric two-column grid and a 24px gap.

At 1250px the rail narrows to 218px and page padding to 26px; the summary stacks. At 1000px the heading actions wrap and supporting panels become one column. At 760px the rail becomes an off-canvas drawer with a scrim, the topbar is 65px, page gutters are 20px, form grids stack, and borrower cards are the initial view. At 1600px the content gains additional top padding and larger metric type.

## Elevation & Depth

The workspace relies on tonal fields and one-pixel borders. Record cards and toolbars explicitly remove utility shadows. Shared buttons and inputs retain shallow utility shadows; selected tabs use a subtle inset-context lift. Dialogs and transient notices carry the strongest shadows.

- Selected tab: `0 1px 3px #172e2010`.
- Toast: `0 8px 30px #10281f30`.
- Native dialog: `0 20px 75px #071c1b35`, over a `#0c211b88` backdrop.

**The Workspace Depth Rule.** Use borders and tonal separation for persistent records; reserve pronounced lift for overlays.

## Shapes

Controls have gently rounded corners; record containers use the container radius, summary and queue panels use the panel radius, and dialogs use the dialog radius. Navigation uses its own slightly smaller radius. Status badges and borrower avatars are circular or pill-shaped. There are no decorative cutouts or raster textures.

## Components

### Buttons
The shared primary is forest green with white text and darker hover/active states. Shared default controls are 36px high; heading actions override this to 39px and use the control radius. Outline controls have a light surface and green-tinted border; secondary controls use tinted slate; ghost and text actions remain quiet until hover. Disabled controls reduce opacity. Existing destructive and emerald variants remain in the shared API.

### Inputs / Fields
Shared inputs use a bordered white surface, control radius, 12px horizontal padding, and a green focus ring. Record filters are 37px high; dialog inputs are at least 40px high. Dark variants use dark slate surfaces. Labels, errors, and disabled styling remain visible; do not rely on placeholders as labels.

### Chips
Status badges use a small pill, fine border, and compact label with an SVG icon. They communicate record state rather than navigation selection.

### Cards / Containers
Panels use surface fill and line borders. Queue rows use top dividers, circular initials, left-aligned identity, and right-aligned tabular balance. Rows gain soft-surface fill on hover. Borrower cards and record tools follow the same restrained border language.

### Navigation
Rail items have 46px minimum height, icon plus label, and a filled selected state with a subtle border. Mobile navigation slides in over a scrim. Record tabs use a raised selected surface; borrower scope filters use an accent underline.

### Dialogs and Feedback
Native dialogs constrain height to 94vh, cap detail width at 800px and forms at 680px, and scroll internally. Toasts sit above the workspace. Interactive color changes use 160ms ease-out; the mobile rail uses 180ms ease-out. Reduced-motion preferences disable animation and transitions. Keyboard focus uses a visible ring or outline.

Save feedback identifies whether a record reached Supabase or is stored on this device only. Remote errors remain visible in forms rather than being replaced by a success state.

### Transcript
Agent messages use bordered light surfaces with dark text. Customer messages use the existing deep emerald utility (`emerald-800`) with white message text and white speaker labels. Opposing corner cuts distinguish the two sides without relying only on color.

## Do's and Don'ts

### Do:
- **Do** use tabular numerals for balances and portfolio values.
- **Do** preserve labeled status indicators and visible keyboard focus.
- **Do** use theme-aware surface and text tokens for workspace additions.

### Don't:
- **Don't** apply overlay-scale shadows to persistent record panels.
- **Don't** treat the remapped blue utility names as permission to introduce a blue primary palette.
- **Don't** replace compact operational controls with decorative display typography.
