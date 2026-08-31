---
name: obsidian
description: Write and edit Obsidian markdown notes for technical topics, especially ML and research notes. Use when the user asks to create, refine, summarize, or extend markdown notes, add sections, improve derivations, normalize notation, or add references and footnotes in note-friendly format.
---

# Obsidian Notes

## Purpose

Use this skill when working on Obsidian markdown notes, especially research notes with math, citations, derivations, and compact explanatory prose.

## Default style

- Write in clear, concise English unless the user asks otherwise.
- Prefer short sections with descriptive headings.
- Keep the note readable as a note, not as a paper.
- Preserve the user's existing structure unless the user asks to reorganize it.
- Prefer consistent notation throughout the note.

## Writing rules

1. Add new material as self-contained sections with informative headings.
2. Put broad overview material near the beginning when the user asks for a conceptual introduction.
3. Keep derivations stepwise: define symbols, state the objective, show the key transformation, then state the final result.
4. When introducing formulas, add one or two sentences of intuition after the math.
5. Avoid unnecessary repetition across sections. If a concept already appears, extend or refine it instead of restating it.
6. When comparing related papers, state clearly which notation or objective belongs to which paper.
7. NEVER include a standalone title heading (e.g., `# Notes on X`) at the top of the file. The file name serves as the title. Start the note directly with the first content section (e.g., `# Motivation` or `# Introduction`).

## Math formatting

- Use LaTeX math delimiters: inline `$...$`, display `$$...$$`.
- Prefer standard notation already present in the note, such as `$x_0, x_t, p_\theta, q$`.
- Define symbols before using them in derived formulas.
- For multi-step objectives, show the high-level form first, then the specialized form.
- When a loss decomposes into per-step terms, explicitly state the relationship between the total objective and each term.

## Citations and references

- Use markdown footnote references in the form `[^key]` when citing papers in prose.
- Keep reference definitions in a final `# References` section.
- Use stable, readable keys such as `[^Ho2020]` or `[^Sohl-Dickstein2015]`.
- When adding a new citation, update both the inline footnote marker and the definition at the end.

## Editing workflow

1. Read the current note and identify the surrounding notation and section structure.
2. Insert new content where it best fits the note's conceptual flow.
3. Reuse existing notation unless there is a strong reason to normalize it.
4. If adding a derivation, make the intermediate steps explicit enough to follow without turning the note verbose.
5. If adding references, ensure every footnote used in the body has a matching definition.
6. After editing, quickly review for notation consistency and markdown readability.

## Preferred note patterns

### Concept section

Use:

```markdown
# Topic

Brief overview paragraph.

## Key idea

Short explanation.
```

### Derivation section

Use:

```markdown
## Optimization objective

State the objective.

Show the main derivation steps.

Conclude with the final formula and one sentence of interpretation.
```

### Reference section

Use:

```markdown
# References

[^Key]: Author. *Title*. Venue or arXiv. URL
```

## Constraints

- Do not turn notes into long-form essays unless the user asks.
- Do not introduce a new notation system unnecessarily.
- Do not add bibliography entries that are not cited unless the user asks for a bibliography dump.
- Prefer compact explanation over exhaustive background.
- NEVER add a standalone title section (like `# Notes on X`) at the top of the file. The file name serves as the title. Start directly with the first content section.
