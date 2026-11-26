---
name: code-review
description: |
  Code review: review the diff between HEAD and a fixed point (commit / branch / tag / merge-base) along two axes — Standards (does the code follow the coding standards and language-level guidelines recorded in this repository?) and Spec (does the code faithfully implement the requirements of the source issue / spec?). Each axis runs in its own parallel subagent so their contexts don't pollute each other; the two reports are presented side by side, never merged or re-ranked.
  Trigger keywords: code review, review, review since X, review branch, review PR.
user-invocable: true
---

# Code Review

Review the diff between `HEAD` and a **fixed point** specified by the user along two axes:

- **Standards**: does the code follow the coding standards and language-level guidelines **recorded in this repository** (`coding-guidelines`)?
- **Spec**: does the code faithfully implement the requirements of the source issue / spec?

Each axis runs in its own **parallel subagent** so their contexts don't pollute each other; this skill then aggregates and presents both reports side by side.

## Scope of this skill

This skill does one thing: **review a given diff and report problems along the two axes.**

- **In scope**: pinning the diff range, locating the spec source, locating the standards sources (repository standards + `/coding-guidelines` language-level guidelines), spawning the two parallel subagents, aggregating side by side
- **Out of scope**: fixing code (that's `implement`'s job), bug hunting (null pointers / races / out-of-bounds — that's the harness's built-in review, not this skill), auditing whole-codebase drift (that's architecture governance)

This skill **only looks at one diff**, read-only. It does not fix what it finds, nor does it decide for you what to fix first.

## Why two axes

A change can pass one axis and fail the other:

- The code is compliant everywhere but implements the wrong thing → **Standards pass, Spec fail**
- The code does exactly what the issue asked for but violates project conventions → **Spec pass, Standards fail**

Reporting separately keeps the passing axis from hiding the failing one. Therefore the two axes are **never merged across axes, never re-ranked across axes**: each axis is sorted internally by importance from high to low, and the final summary gives only the single most severe finding of each axis (i.e. the first item of each axis's list) — **never pick one overall winner across axes**; that is exactly what the separation exists to prevent.

## Procedure

### 1. Pin the fixed point

Whatever fixed point the user names is the fixed point (commit SHA, branch name, tag, `main`, `HEAD~5`, etc.). **If the user didn't specify one, ask — don't guess.**

Capture the diff command once: `git diff <fixed-point>...HEAD` (three dots — compares against the merge-base). Also record the commit list: `git log <fixed-point>..HEAD --oneline`.

Before going further, verify the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or an empty diff must fail **here**, not after the two parallel subagents have been spawned.

### 2. Locate the spec source

Look for the source spec in this order:

1. Issue references in commit messages (`#123`, `Closes #45`, GitLab `!67`, etc.). If this repo has an issue-tracker workflow configured, follow it; otherwise skip this item.
2. A path passed in by the user as an argument.
3. Spec / design files in the repo: `docs/specs/`, `specs/`, `.scratch/`, and artifacts from the `design` phases (documents written from the spec template).
4. If none found, ask the user where the spec is. If the user says there is none, the **Spec subagent is skipped**, and the final report states "no spec available".

### 3. Locate standards sources + coding-guidelines + smell baseline

This step is done by this skill itself **before** spawning the subagents, and the results are pasted into the briefing — subagents have no reliable way to read these materials on their own. The three layers of sources have a fixed priority; on conflict the higher one wins:

1. **Repository-recorded standards** — highest. Find everything in the repo that records "how code should be written", e.g. `CODING_STANDARDS.md`, `CONTRIBUTING.md`, coding sections in `AGENTS.md`.
2. **Skill `/coding-guidelines`** — applies when the repo has nothing recorded for that language.
3. **Smell baseline** — weakest; always a judgment call.

When repository standards conflict with `coding-guidelines`, **the repository wins**, and the conflict is named in the report rather than treated as a violation.

On top of any of the above sources, the Standards axis **always** carries the **smell baseline** below: a fixed set of Fowler code smells (*Refactoring*, Chapter 3), applicable even when the repo records nothing and there are no language-level guidelines. Two rules constrain it:

- **Repository first.** When a repo standard endorses something the baseline would flag, suppress that smell.
- **Always a judgment call.** Each smell is a labeled heuristic ("suspected Feature Envy"), never a hard violation. As with any standard here, skip everything a tool already enforces.

The smell baseline lives in [references/smell-baseline.md](./references/smell-baseline.md). **When spawning the Standards subagent, the full text of the baseline must be pasted into its briefing** — the subagent has no other way to read it.

### 4. Spawn the two subagents in parallel

**The Standards subagent briefing should include:**

- The complete diff command and commit list.
- The list of repo standards source files found in step 3.
- The **full text** of the language-level guidelines resolved from `/coding-guidelines` in step 3, noting which paths each document covers; if nothing matched, write "no language-level guidelines available".
- The full text of the smell baseline from step 3.
- The brief: "**Report sorted by importance, highest first**: (a) every place in the diff that violates a standard — cite the repo standard (file + the specific rule) or, for language-level guidelines, cite the document name; (b) any baseline smells you see — name them and cite the hunk. Distinguish hard violations from judgment calls: violations of repo standards and language-level guidelines may be hard violations, but baseline smells are always judgment calls. On conflict, repo standards override language-level guidelines, and language-level guidelines override the baseline — judge by the winning layer; don't report the conflict itself as a violation. Skip everything a tool already enforces. Sort hard violations above judgment calls; within the same tier, sort by blast radius. **Do not invoke `/code-review` or spawn any further subagents: do this review directly.** 400 words max."

**The Spec subagent briefing should include:**

- The diff command and commit list.
- The path to the spec or its fetched content.
- The brief: "**Report sorted by importance, highest first**: (a) requirements the spec demands but the diff is missing or only half-implements; (b) behavior present in the diff that the spec never asked for (scope creep); (c) requirements that look implemented but look implemented wrong. Every finding must cite the corresponding spec lines. Sort order: missing/wrongly-implemented requirements above scope creep, scope creep above implementation blemishes; within the same tier, sort by impact on users / the contract. **Do not invoke `/code-review` or spawn any further subagents: do this review directly.** 400 words max."

If there is no spec, skip the Spec subagent and note that in the final report.

> Both briefs explicitly forbid recursively invoking `/code-review` and spawning further subagents. This is a known failure mode that spirals out of control (a subagent rediscovers this skill and fans out layer after layer), so it's blocked at the briefing layer rather than relying on the harness as a backstop.

### 5. Aggregate

Place the two reports verbatim (or lightly cleaned up) under the headings `## Standards` and `## Spec`, **each internally sorted by importance, highest first**. **Do not merge across axes, do not re-rank across axes** — the two axes are deliberately separated (see "Why two axes"). The intra-axis ordering is done by each axis's subagent when it reports; aggregation only does light cleanup, never re-ranks within an axis.

Close with a one-line summary: the total number of findings per axis, and the single most severe finding **of each axis** (i.e. the first item of each axis's list, if any). **Do not pick an overall winner across axes** — that re-ranking is exactly what the separation exists to prevent.

## Definition of done

The review is complete when all of the following hold:

- The report is two separate blocks, `## Standards` and `## Spec` — not one merged list
- Each block is internally sorted by importance, highest first (hard violations / missing-or-wrong requirements first, judgment calls / scope creep / implementation blemishes after)
- Every Standards finding names its source: either a rule in a specific repo file, a `coding-guidelines` language-level document, or one of the twelve smells with a hunk citation
- `coding-guidelines` was resolved against the diff's file types, or the report states "no language-level guidelines available"
- Every Spec finding cites the corresponding spec lines
- The closing summary gives each axis's own most severe finding (the first item of each axis's list) and **refuses** to pick an overall winner across axes
- When no spec is available, the Spec block says "no spec available" instead of reverse-engineering requirements from the code

## Boundaries and caveats

- **Only committed diffs**: `<fixed-point>...HEAD` is a three-dot diff, measured from the merge-base — it does **not** include staged or working-tree changes. To review uncommitted work, commit first, review, then amend or add a fixup.
- **Findings are hypotheses, not evidence**: this skill aggregates the two reports verbatim or lightly cleaned; it does not re-verify each one against the files. A finding may cite the wrong location or exaggerate impact. Read its citations before acting on it.
- **Non-convergent**: fixing findings exposes new surface, and the judgment-call half of the Standards axis is non-deterministic across runs. Don't loop until "clean" — it never goes clean. Treat one pass as a list of leads, act on the ones with citations behind them, then stop.
- **Best run in a fresh session**: reviewing your own code in the same session that wrote it means reviewing with all the assumptions that shaped the code — exactly the context an independent reviewer wouldn't have. Running `/code-review` from a clean session is the honest version.
