---
name: Obsidian Precision
colors:
  surface: '#0e141a'
  surface-dim: '#0e141a'
  surface-bright: '#343a41'
  surface-container-lowest: '#090f15'
  surface-container-low: '#171c23'
  surface-container: '#1b2027'
  surface-container-high: '#252a32'
  surface-container-highest: '#30353d'
  on-surface: '#dee3ec'
  on-surface-variant: '#c1c6d7'
  inverse-surface: '#dee3ec'
  inverse-on-surface: '#2c3138'
  outline: '#8b90a0'
  outline-variant: '#414755'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e69'
  primary-container: '#4b8eff'
  on-primary-container: '#00285c'
  inverse-primary: '#005bc1'
  secondary: '#c5c6d1'
  on-secondary: '#2e3039'
  secondary-container: '#454650'
  on-secondary-container: '#b4b4bf'
  tertiary: '#c4c6d3'
  on-tertiary: '#2d303b'
  tertiary-container: '#8e909d'
  on-tertiary-container: '#262934'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#e1e1ed'
  secondary-fixed-dim: '#c5c6d1'
  on-secondary-fixed: '#191b23'
  on-secondary-fixed-variant: '#454650'
  tertiary-fixed: '#e0e2f0'
  tertiary-fixed-dim: '#c4c6d3'
  on-tertiary-fixed: '#181b25'
  on-tertiary-fixed-variant: '#444652'
  background: '#0e141a'
  on-background: '#dee3ec'
  surface-variant: '#30353d'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 20px
  container-max: 1440px
---

## Brand & Style
The design system is engineered for **SpecGuard AI**, a high-performance developer tool. The brand personality is authoritative, technical, and hyper-efficient, mirroring the precision required in AI-driven security and specification analysis.

The aesthetic follows a **High-Density Minimalism** approach, heavily influenced by modern developer-centric platforms. It utilizes a dark-mode first philosophy to reduce eye strain during long sessions. The visual language relies on **Glassmorphism** for depth and **Tactile Precision** through subtle 1px borders, creating a UI that feels like a high-end instrument rather than a generic web application.

## Colors
This design system uses a deeply layered dark palette to establish hierarchy without relying on high-luminance backgrounds.

- **Primary**: Electric Blue (#007aff) is used sparingly for primary actions, focus states, and progress indicators to maintain a "heads-up display" feel.
- **Surfaces**: The base is Obsidian (#0b0e14). Secondary containers use Charcoal (#12141c) to create a subtle lift.
- **Semantic Risk**: Risk levels are categorized by high-saturation status colors. These should be used for badges, small indicators, and text-links, never as large background fills, to maintain the professional aesthetic.
- **Borders**: All borders use a low-opacity white (typically `rgba(255, 255, 255, 0.08)`) to define edges against the dark background.

## Typography
The typography is centered on **Inter** for its exceptional legibility and neutral character in dense UI environments. **JetBrains Mono** is utilized as a secondary functional font for technical metadata, IDs, and code snippets.

- **Headlines**: Use tighter letter-spacing for large displays to give a "machined" look.
- **Body**: Fixed at 14px for the majority of the application to allow for high information density without sacrificing readability.
- **Monospaced Accents**: Any element representing data (IDs, hashes, file paths) must use the label-mono style to distinguish it from instructional text.

## Layout & Spacing
The layout follows a **Rigid Grid Model** with a 4px baseline. This ensures all components align to a predictable rhythm.

- **Desktop**: A 12-column grid with 20px gutters. Content is typically housed in "panes" reminiscent of an IDE.
- **Panes**: Sidebars are fixed-width (typically 240px or 280px), while the main editor/dashboard area is fluid.
- **Density**: Use "Compact" spacing for data-heavy views (8px padding in lists) and "Default" spacing for landing or configuration pages (16px+).

## Elevation & Depth
Depth is created through **Subtractive Layering** and **Glassmorphism**. Rather than traditional drop shadows, we use interior glows and backdrop blurs.

- **Layer 0 (Base)**: #0b0e14.
- **Layer 1 (Card/Section)**: #12141c with a 1px solid border `rgba(255, 255, 255, 0.05)`.
- **Layer 2 (Popovers/Modals)**: #1a1d27 with a `backdrop-filter: blur(12px)` and a slightly more prominent border.
- **Shadows**: Use "Deep Obsidian" shadows—large blur radius (24px+), low opacity (40%), and a dark tint to ground floating elements without creating "muddy" UI.

## Shapes
The shape language is "Soft-Technical." Elements use an 8px radius (`rounded-md`) for standard components and 12px-16px for larger containers.

- **Buttons/Inputs**: 8px (standardized).
- **Cards/Modals**: 12px.
- **Status Pills**: Fully rounded (pill-shaped).
- **Focus States**: A 2px offset ring in Primary Blue (#007aff).

## Components

### Buttons
- **Primary**: Background: #007aff; Text: White. No border.
- **Secondary**: Background: rgba(255, 255, 255, 0.03); Border: 1px solid rgba(255, 255, 255, 0.1); Text: #ffffff.
- **Ghost**: No background/border; Text: #8a8f98. Hover state: Lighten text and add subtle background tint.

### Input Fields
- Dark backgrounds (#0b0e14) with a 1px border. 
- On focus: Border changes to #007aff and a subtle outer glow is applied.
- Labels use `label-mono` at 12px, placed above the field.

### Risk Badges
- Small, uppercase, monospaced text.
- Background: 10% opacity of the semantic color.
- Border: 1px solid 20% opacity of the semantic color.
- Text: 100% opacity of the semantic color.

### Code Snippets
- Background: #000000; Padding: 16px; Font: `code-sm`.
- Syntax highlighting should follow a "Midnight" theme with muted pastels.

### Cards
- Interactive cards should have a subtle hover lift: background changes from #12141c to #1a1d27.
- Use a "glass" header for cards with a 1px bottom border to separate content logically.