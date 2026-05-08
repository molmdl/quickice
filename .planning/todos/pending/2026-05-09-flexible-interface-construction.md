---
created: 2026-05-09T17:30
title: Support flexible interface construction modes
area: feature
files:
  - quickice/interface/
  - quickice/interface_panel.py
---

## Problem

Current interface construction has limited flexibility:
- Slab placement is fixed (ice on top, water below)
- Cannot mix different hydrate types in same system
- Cannot combine ice + hydrate in same system

## Solution

Extend interface construction capabilities:
1. **Slab placement options**: Allow ice on bottom, water on top, or sandwich configurations
2. **Multiple hydrate types**: Support sI + sII in same system
3. **Ice + hydrate systems**: Generate ice structure with hydrate pockets

Architecture considerations:
- May require new configuration UI
- GenIce2 API limitations need investigation
- Target: v5.x milestone
