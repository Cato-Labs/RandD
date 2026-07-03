---
name: Premium Hospitality Design System
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#434845'
  inverse-surface: '#313030'
  inverse-on-surface: '#f3f0ef'
  outline: '#737875'
  outline-variant: '#c3c8c4'
  surface-tint: '#56615c'
  primary: '#17211d'
  on-primary: '#ffffff'
  primary-container: '#2c3632'
  on-primary-container: '#949f99'
  inverse-primary: '#bec9c3'
  secondary: '#735c00'
  on-secondary: '#ffffff'
  secondary-container: '#fed65b'
  on-secondary-container: '#745c00'
  tertiary: '#1f1f1c'
  on-tertiary: '#ffffff'
  tertiary-container: '#343431'
  on-tertiary-container: '#9e9c98'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae5df'
  primary-fixed-dim: '#bec9c3'
  on-primary-fixed: '#141e1a'
  on-primary-fixed-variant: '#3f4945'
  secondary-fixed: '#ffe088'
  secondary-fixed-dim: '#e9c349'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#574500'
  tertiary-fixed: '#e5e2dd'
  tertiary-fixed-dim: '#c9c6c2'
  on-tertiary-fixed: '#1c1c19'
  on-tertiary-fixed-variant: '#474743'
  background: '#fcf9f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
typography:
  display-lg:
    fontFamily: EB Garamond
    fontSize: 48px
    fontWeight: '500'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: EB Garamond
    fontSize: 32px
    fontWeight: '500'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: EB Garamond
    fontSize: 28px
    fontWeight: '500'
    lineHeight: '1.2'
  headline-md:
    fontFamily: EB Garamond
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
  title-md:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: 0.01em
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.08em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-margin: 32px
  gutter: 24px
  stack-sm: 12px
  stack-md: 24px
  stack-lg: 48px
---

## Brand & Style

The brand personality centers on **Premium Hospitality Operations**. It transitions the interface from a utility tool into a high-end concierge experience. The design must feel warm, elegant, and meticulous, bridging the gap between sophisticated property owners and the operational excellence of turnover specialists.

The style is **Soft Minimalist** with a **Luxury Travel** influence. It prioritizes clarity and whitespace to reduce the cognitive load of complex property management tasks while maintaining an atmosphere of calm and "quiet luxury." Visuals should evoke the feeling of a boutique hotel lobby: welcoming, high-touch, and impeccably organized.

## Colors

The palette is anchored in **Warm Neutrals** to provide a welcoming, "Oatmeal" and "Cream" foundation. 
- **Primary:** A deep Forest Green (#2C3632) represents stability, property care, and organic luxury.
- **Secondary/Highlights:** Muted Gold or Copper accents are used sparingly for success states, premium status indicators, or "concierge-level" actions.
- **Neutrals:** We avoid harsh blacks. Text uses a soft Charcoal (#1A1A1A) to maintain high legibility without the industrial weight. 
- **Backgrounds:** A soft off-white (#FAF9F6) is used for the base canvas to reduce eye strain during long inspection workflows.

## Typography

This design system utilizes a high-contrast typographic pairing to balance editorial beauty with functional efficiency.

- **Headlines (EB Garamond):** Used for property names, section titles, and "welcome" moments. It should be set with generous leading.
- **Functional Data (Hanken Grotesk):** A modern, clean sans-serif used for all turnover data, checklists, and time-stamps. It provides the precision required for operational excellence.
- **Hierarchy:** Use `label-caps` for metadata like "Property ID" or "Status" to create a structured, professional rhythm.

## Layout & Spacing

The layout philosophy follows a **Fixed Grid** with generous white space to evoke a sense of "room to breathe." 

- **Desktop:** 12-column grid, 1200px max-width, 24px gutters.
- **Mobile:** Single column, 20px side margins. 
- **Rhythm:** We use a strict 8px base unit. Card padding is intentionally large (24px or 32px) to ensure the UI feels premium rather than cramped.
- **Reflow:** Functional data (checklists) should reflow into single-column vertical stacks on mobile to ensure ease of use for specialists on-site.

## Elevation & Depth

We utilize **Tonal Layering** combined with **Soft Ambient Shadows**. 

- **Surfaces:** Use a subtle background blur (Backdrop Filter: 12px) on navigation bars and floating action buttons to create a "Glassmorphism" effect that feels modern and light.
- **Shadows:** Shadows are highly diffused and tinted with the Primary Forest Green (e.g., `rgba(44, 54, 50, 0.08)`) to avoid a "dirty" grey appearance.
- **Depth Hierarchy:** 
  - Level 0: Background (#FAF9F6)
  - Level 1: Cards and main containers (White, very subtle shadow)
  - Level 2: Modals and dropdowns (White, medium diffused shadow)

## Shapes

The shape language is defined by large, inviting radii. This removes the "sharp edges" of industrial software.

- **Primary Radius:** 0.5rem (8px) for inputs and small components.
- **Large Radius:** 1rem (16px) for property cards and main containers.
- **Extra Large:** 1.5rem (24px) for prominent featured sections or "Guest Experience" highlights.
- **Buttons:** Use fully rounded (pill-shaped) ends for primary calls-to-action to maximize the friendly, hospitality-focused feel.

## Components

- **Buttons:** Primary buttons use the deep Forest Green background with White text. Secondary buttons use an Oatmeal border with Forest Green text. Use pill-shaped styling.
- **Cards:** Property cards should feature high-quality photography as a background or large header, with content overlaid on a soft white or blurred glass surface.
- **Chips:** Status indicators (e.g., "Ready for Guest," "Turnover in Progress") should use the "Soft" shape (8px) with muted, low-saturation background tints.
- **Input Fields:** Use a floating label style with a subtle 1px border in Oatmeal. Focus states should transition the border to Muted Gold.
- **Checkboxes:** Replace square boxes with soft circular "check-circles" to feel more like a concierge checklist and less like a tax form.
- **Iconography:** Use 1.5pt stroke weight. Icons should be hospitality-focused: 
    - *Property Care* (House icon)
    - *Turnover* (Refresh/Sparkle icon)
    - *Guest Access* (Classic key icon)
    - *Excellence* (Laurel or Star icon)
- **Specialized Component - "The Property Header":** A high-contrast section at the top of inspections showing the property name in EB Garamond with a soft-focus background image of the interior.
