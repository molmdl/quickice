# Phase 6: Documentation - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Create user-facing documentation explaining how to use QuickIce, interpret results, and understand the tool is experimental. README is the primary document with docs/ folder for detailed topics.

</domain>

<decisions>
## Implementation Decisions

### Content Structure
- **Approach:** Overview first — What it is → Why it exists → How to use
- **File organization:** README + docs/ folder
- **docs/ contents:** CLI reference + examples + ranking details
- **External references:** Point to GenIce docs instead of duplicating
- **Honesty principle:** Document only what's in the code, don't make things up

### Tone & Disclaimer
- **Disclaimer location:** Top of README in markdown quote block (`>`)
- **Disclaimer text:** Based on current README — "Experimental" with grammar correction
- **Tone:** Technical but clear

### CLI Examples
- **Coverage:** Full — all CLI flags with examples
- **Scenarios:** Varied phases — show examples for different ice phases (Ih, III, VI, etc.)
- **Format:** Mixed — short intro + code block + brief output note
- **Outputs:** Key outputs only — brief summary, not full results

### Ranking Explanation
- **Detail level:** With formulas — show scoring formulas and normalization
- **Aspects covered:** All three — energy scoring + density matching + diversity scoring
- **Limitations:** Include honest note that scoring is simplified, not physics-based

### Unfixed Issues
- **Section:** Dedicated "Known Issues" section in README
- **Summary:** "Polygon verification needed" — one-liner
- **Reference:** Point to ISSUES.md for details

</decisions>

<specifics>
## Specific Ideas

- Current README: `# quickice` + `(Experimental) A mini vibe coding project exercise.`
- Grammar correction for current README text
- External docs: GenIce2 documentation should be linked, not extracted

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-documentation*
*Context gathered: 2026-03-28*
