---
name: revela
description: An iCloud album developed into a layflat book at home; no photo leaves the computer.
colors:
  envelope-yellow: "#f2b705"
  envelope-back: "#d99a00"
  lab-red: "#b5221a"
  press-black: "#1b1a17"
  ink-soft: "#3d3524"
  print-paper: "#fbfbf8"
  desk: "#e9e8e4"
  muted: "#5c5a55"
  hairline: "#d6d4cf"
typography:
  mark:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "clamp(4.5rem, 13vw, 10.5rem)"
    fontWeight: 900
    lineHeight: 0.78
    letterSpacing: "-0.045em"
  display:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "clamp(2.2rem, 5.2vw, 4.4rem)"
    fontWeight: 900
    lineHeight: 0.98
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Archivo Narrow, Arial Narrow, sans-serif"
    fontSize: "clamp(1.7rem, 3.4vw, 3rem)"
    fontWeight: 700
    lineHeight: 1
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.5
  body-app:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Archivo Narrow, Arial Narrow, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    letterSpacing: "0.06em"
  command:
    fontFamily: "ui-monospace, SF Mono, Menlo, monospace"
    fontWeight: 500
rounded:
  none: "0"
  sm: "3px"
spacing:
  gutter: "clamp(18px, 4vw, 48px)"
  wrap: "1240px"
  section: "clamp(72px, 9vw, 128px)"
components:
  button-primary:
    backgroundColor: "{colors.lab-red}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "15px 22px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.press-black}"
    rounded: "{rounded.sm}"
    padding: "15px 22px"
  button-app-primary:
    backgroundColor: "{colors.lab-red}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
  input-ruled:
    backgroundColor: "transparent"
    textColor: "{colors.press-black}"
    rounded: "{rounded.none}"
    padding: "4px 0 6px"
  order-form:
    backgroundColor: "{colors.print-paper}"
    textColor: "{colors.press-black}"
    rounded: "{rounded.none}"
  app-bar:
    backgroundColor: "{colors.envelope-yellow}"
    textColor: "{colors.press-black}"
    padding: "10px 28px"
---

# Design System: revela

## Overview

**Creative North Star: "The Photo-Lab Envelope"**

Every surface is the paper a photo lab hands back: a yellow envelope printed in two inks, a white order form with ruled fields, a perforated claim stub, prints with white borders. Paper objects behave like paper: loose ones tilt and cast soft warm shadows, printed ones lie flat behind a 2px rule.

The landing page (`site/`) is the full envelope. The app (`templates/`) is the same lab, restrained: a grey desk under the spreads so the photos lead, yellow only in the top bar.

**Key Characteristics:**
- Drenched yellow ground, two inks (lab red, press black), white paper for anything you fill in or hold.
- Archivo 900 for the mark and headings; Archivo Narrow caps for form language.
- 2px black rules everywhere; dashed means perforation, dotted means leader.
- Selection is a hand-drawn red X.

## Colors

Two inks on envelope yellow, plus white paper; the app adds a grey desk.

### Primary
- **Lab Red**: the one action color (Copy, Rebuild book, closing CTA), the mark, the 14px band over the front panel (5px under the app bar), the drawn X, totals and counts, the `$` prompt.

### Neutral
- **Envelope Yellow**: page ground of the landing page, the app index and the app bar.
- **Envelope Back**: the deeper yellow of the envelope's inside (mouth strip, sealed section).
- **Press Black**: text, every rule and border, the inverted "how it works" band, focus outline.
- **Ink Soft**: secondary text on yellow and paper.
- **Print Paper**: order form, prints, slip, facts grid, app sidebar.
- **Desk / Muted / Hairline**: app only: the ground under the spreads, secondary text, row dividers.

### Named Rules
**The Two Inks Rule.** Yellow is printed in red and black only. No third hue, no cream, no gradients beyond the spread gutter shade.

**The Red Is Small Rule.** Red text on yellow is 3.6:1, so it appears only at display scale (the mark, the seal). Smaller red sits on paper.

## Typography

**Display Font:** Archivo (variable 100–900, self-hosted)
**Label Font:** Archivo Narrow (variable 400–700, self-hosted)
**Command:** system monospace, for shell commands only.

**Character:** a lab's printed stationery: a fat grotesque mark and a condensed caps form face.

### Hierarchy
- **Mark**: the lowercase word "revela" in lab red. Landing at mark scale, app bar 24px, app index 64px.
- **Display**: section headings, max 16ch, balanced.
- **Headline**: the landing h1 only, Narrow caps, max 24ch.
- **Body**: 17px on the landing (16px under 640px), 15px in the app. Ledes 18–21px, max 58ch.
- **Label** (`.caps`): uppercase Narrow for nav, field legends, slip headers, chips, captions. 12.5px in the app.

### Named Rules
**The Lowercase Mark Rule.** "revela" is always lowercase Archivo 900 in lab red, tracked tight (-0.04 to -0.045em).

## Layout

Content sits in a centered wrap (`min(1240px, 100% - 2 * gutter)`). Sections stack full-bleed bands (yellow, black, deep yellow), each opening with a 2px rule or a color change rather than a card. Grids use 2px rules between cells rather than gaps (order form fields, facts). Under 640px everything goes to one column. The app is a two-column desk: spreads (max 1100px) plus a 340px sticky paper sidebar, which drops below at 900px.

## Elevation & Depth

Hybrid. Printed things are flat with a 2px border. Physically separate paper (prints, the slip, the spread, the front panel over the prints, the seal, the primary button) gets a two-layer shadow: a tight dark contact shadow plus a wide warm-brown blur (`rgb(60–120 20–50 0 / .2–.3)`). Values live in the sidecar.

### Named Rules
**The Loose Paper Rule.** Only loose paper tilts (prints -5° to 2°, slip 1.2°, seal -8°) and casts a shadow. Forms, grids and bands never tilt.

## Shapes

Square by default. 3px corners only on pressable things (buttons, chips, the language toggle). Circles only for the seal and the stub's punch holes. The perforation is a 2px dashed rule with half-circle notches cut at both ends; the sealed flap is a clipped triangle.

## Components

### Buttons
- **Primary:** lab red fill, white text, Archivo 700 17px, 3px corners, inline 18px SVG icon. Hover lifts 1px with a deeper shadow; active presses 1px.
- **Ghost:** 2px press-black border, no fill, no shadow.
- **App Rebuild:** same red at app size; disabled turns into an ink outline reading "No changes", with a white pill for the change count.

### Order form
Print-paper panel, 2px black border, fields split by 2px rules. Text input is a ruled line (2px bottom border that turns red on focus). Options are 24px square tick boxes; a checked one draws a red X left to right (clip-path, 0.35s, `--ease`).

### Claim stub
Below the form behind the perforation: the live command in monospace with a red `$`, then Copy (primary) and GitHub (ghost). On phones it moves up under the album field.

### Spread
White double page with a darkened gutter (linear-gradient at the fold). In the app every photo slot is a button: hover reveals a black "Remove" chip; a removed slot fades to 14% grey with the red X over it and a paper chip "Removed · put back".

### App sidebar rows
Thumbnail with a 4px white print border, name and reason, and an outlined Narrow button that fills black on hover.

## Do's and Don'ts

### Do:
- **Do** keep red for the one action per view, the mark and selection marks.
- **Do** draw rules and borders at 2px press black; use dashed for tear lines only.
- **Do** self-host every font and image (the page loads nothing from outside).
- **Do** keep app chrome restrained: desk grey under photos, yellow only in the top bar.

### Don't:
- **Don't** use a serif, cream ground, or a third accent hue.
- **Don't** round cards or panels; corners are square except on pressable things.
- **Don't** tilt or shadow anything printed (forms, grids, bands).
- **Don't** use red text smaller than display scale on yellow.
