# Dashboard Frontend Design

## Overview

Single HTML file dashboard for Tao Research System. Paper-themed aesthetic (warm ivory, serif headings, burgundy accents). Served by Flask, no build step.

## Layout

- **Left sidebar**: Project list from `/api/projects`, click to load
- **Main area**: 3 rows
  1. Pipeline Tracker — 18-stage horizontal timeline
  2. Experiment Monitor (60%) + Quality Chart (40%) — side by side
  3. File Browser — two-pane (tree + preview)

## Panels

### Pipeline Tracker
- Connected nodes for 18 stages (init -> done)
- Completed = sage green filled, Current = burgundy pulsing, Future = gray hollow
- Iteration badge pill, loop annotations for pivots
- ~80px height, stage abbreviations with hover tooltips

### Experiment Monitor
- Summary chips (total/completed/running/queued)
- Compact table: Task ID, Status, Progress bar
- Status dots: green=done, amber=running, gray=queued
- Recovery event footnote

### Quality Trajectory
- Chart.js line chart, burgundy line with warm gradient fill
- Reference line at 8.0 (quality gate threshold)
- X=iteration, Y=score 0-10

### File Browser
- Left tree pane (30%): collapsible directory tree, 3 levels deep
- Right preview pane (70%): JSON pretty-print, Markdown rendered, text as monospace
- Auto-expand writing/, plan/, exp/

## Color Palette
- Background: `#FDFAF5` (warm ivory)
- Text: `#2C2C2C` (dark charcoal)
- Accent: `#8B3A3A` (burgundy)
- Success: `#6B8F71` (sage green)
- Running: `#C4903D` (warm amber)
- Borders: `#E8E0D4` (warm gray)

## Typography
- Headings: Georgia / Palatino (serif)
- Data values: monospace
- Body: system sans-serif

## API Requirements

Existing:
- `GET /api/projects` — project list
- `GET /api/project/<name>/dashboard` — status, experiment counts, quality scores
- `GET /api/project/<name>/files/<path>` — file content

New:
- `GET /api/project/<name>/tree` — directory tree for file browser
- `GET /api/project/<name>/experiments` — per-task experiment details
- `GET /` — serve dashboard.html

## Auto-refresh
- Poll dashboard data every 5 seconds
- Poll experiment data every 5 seconds when experiments panel is visible
