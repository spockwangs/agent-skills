---
name: coding-guidelines
description: "Language-specific coding guidelines selected by file type. Use before editing or reviewing source files, to load the rules that apply to the languages in scope."
user-invocable: false
disable-model-invocation: false
---

# Coding Guidelines

This skill is a door, not a rulebook: it resolves which guideline documents apply to the files in front of you, and you follow only those.

## Process

1. Decide the file set in scope. Before editing, that is the files you are about to change. When reviewing, it is the diff: `git diff --name-only <fixed-point>...HEAD`.
2. Read `index.yaml` next to this file. It maps file globs to guideline documents.
3. Match every file in scope against every entry. A file may match more than one entry; when two rules conflict, the entry later in the file wins, so narrow scopes are listed after the general one.
4. Read only the matched documents. Do not read the whole `references/` directory.
5. Apply the loaded rules for the rest of the task. If a rule contradicts the surrounding code, surface the conflict instead of silently picking one.

If nothing matches, say that no guideline matched and continue with the project's own conventions. Do not infer rules from a language name alone: a missing entry is a gap to report, not something to invent.

## Adding a language

Write the rules to `references/<language>.md`, then add one entry to `index.yaml`. Keep one document per language, and give narrow exceptions (tests, generated code, vendored or legacy directories) their own entries after the general one.
