# AEGIS-X Slate Precision Design System & UI/UX Specification

## 1. Executive Summary & Design System Architecture

AEGIS-X is a cyber-physical security platform engineered for high-consequence Industrial Control Systems (ICS), Operational Technology (OT), IoT environments, and critical infrastructure. The AEGIS-X design system rejects "cyberpunk" tropes—neon glows, excessive glassmorphic blurs, dark-hacker aesthetics, and speculative AI HUD displays—in favor of **restrained precision, intentional contrast, cognitive calm, high information density, and traceable evidence**.

The design system draws structural inspiration from Apple’s interaction discipline, Linear’s typographic density, Stripe’s documentation rigor, and Figma’s stateful workspace architecture, while establishing its own distinct visual identity: **Slate Precision**.

---

## 2. Color System

### Dark Mode (Primary Palette)

- `--bg-base`: `#0B0E14` (Canvas background)
- `--bg-surface`: `#121620` (Primary container & card surface)
- `--bg-surface-elevated`: `#1A202C` (Modals, dropdowns, popovers)
- `--bg-surface-hover`: `#222A3A` (Hover state for interactive rows)
- `--border-subtle`: `#1F2633` (Dividers, grid lines)
- `--border-strong`: `#333D52` (Input borders, boundaries)
- `--border-focus`: `#2563EB` (Keyboard focus ring)
- `--text-primary`: `#F8FAFC` (Headings, primary data - WCAG AAA 15.8:1)
- `--text-secondary`: `#94A3B8` (Body text, labels - WCAG AA 6.4:1)
- `--text-tertiary`: `#64748B` (Captions, metadata - 3.8:1)
- `--text-disabled`: `#475569` (Disabled states)
- `--accent-primary`: `#2563EB` (AEGIS Blue)
- `--status-success`: `#059669` (Nominal state)
- `--status-warning`: `#D97706` (Anomaly threshold)
- `--status-critical`: `#DC2626` (Severe threat / Pending Approval)
- `--status-info`: `#0284C7` (System logs)

---

## 3. Typography System

- **sans**: `Inter, -apple-system, sans-serif`
- **mono**: `JetBrains Mono, monospace` (For IDs, IP addresses, MITRE codes, logs, hashes)

---

## 4. Spacing & Geometry

- Base grid: **8px strict scale** (4px token `--space-1` for inline tags/dots).
- Radii: `--radius-sm` (2px), `--radius-md` (4px default), `--radius-lg` (8px overlays), `--radius-pill` (9999px status dots).
- GPU Motion: `transform` & `opacity` transitions at `50ms` (instant), `100ms` (fast), `150ms` (normal), `250ms` (slow).

---

## 5. Components & Command Palette

- 40 base reusable components + specialized security components (`Incident Card`, `Risk Indicator`, `Evidence Item`, `Approval Gate`, `Digital Twin Node`, `Attack Graph Node`).
- Keyboard command palette (`⌘K` / `Ctrl+K`).
