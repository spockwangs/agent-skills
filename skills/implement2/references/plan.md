# Task plan format

The plan is the contract between the orchestrator and every subagent: nobody pastes it into a prompt, they read the file.

## Skeleton

```markdown
# <spec title>

- Source: <intent path / spec path / issue reference / design doc path>
- Integration branch: <the same branch name in every repo>
- Key decisions:
  - <domain models, class sketch, data structures, state machines, module interfaces, function signatures>

## Tasks

### T01 - <title>
**Status:** pending
**Blocked by:** none
**Goal**: <the end-to-end behaviour this task makes work, in the user's terms>
**Scope:** <file paths to change or add>
**Steps:**
    1. xxx
    2. xxx
**Success criterion**
- [ ] Acceptance criterion
- [ ] Acceptance criterion

### T02 - <title>
**Blocked by:** T01
...
```

## Design principles

- **Model driven design**. Encodes the business rules and invariants in data structures instead of scattering multiple
  places. If two places change for the same reason, they should be in the same place.
- **Deep module principle**. A narrow interface with substantial hidden implementation is preferred than many interfaces
  with simple implementation.
- **Dependency rule**. Instable modules should depend on stable modules, not vice versa. For example, the modules
  responsible for UI, IO should depend on the modules responsible for business rules.

## Task decomposition rules

1. **Slice vertically, by use case.** A task is a tracer bullet: one narrow but complete path through every layer it needs (schema, API, UI, tests), verifiable on its own. Never slice by repo or by layer. If a use case crosses three repos, one task crosses three repos, because splitting it there is what makes each half unverifiable alone. The test: "what can I demo when this is done?" A task with no answer is not a vertical slice.
2. **Sized to one fresh context window.** An implementer that has never seen the spec must be able to finish it. If a task looks like hours of agent work, split it by use case, not by repo.
3. **Blocked by is a real gate only.** An edge means the task needs something another task creates, in its own repo or across repos. Number blockers first. Every unnecessary edge is concurrency thrown away.
4. **Prefactoring first.** If the change is easier after some mechanical prep, that prep is an early task of its own. Make the change easy, then make the easy change.
5. **Success criteria must be able to fail at the base commit.** A criterion that is already true, or that only another task can satisfy, grades nothing. Keep file paths and line numbers out of the task body; they go stale, behaviour does not.
6. **Fifteen tasks is a lot, three is a warning.** Too many means over-decomposition; too few means the graph was never really split.

## Wide refactors

A mechanical change whose blast radius covers a whole codebase (rename a column, retype a shared symbol) cannot be a tracer bullet: one edit breaks every call site. Sequence it expand, migrate, contract: add the new form beside the old; move call sites over in batches, one task per batch (a batch may span repos), each blocked by the expand; delete the old form in a task blocked by every batch. Green is promised only at the contract task.

## Status

The orchestrator is the only writer of `Status`: `pending`, `running`, `done`. The frontier is computed from these fields, never from a tracker and never from memory.
