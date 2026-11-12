---
name: implement2
description: "Implement a feature according to a spec by splitting it into a task tree and running multiple subagents in parallel, each in its own git worktree, all merged onto one integration branch."
disable-model-invocation: true
---

Implement the work already described in the current spec, issue, or conversation which is too big for a single agent. A
planner subagent splits it into a **task tree** with blocking relationships between them, and implementer subagents
build the frontier of tasks in parallel, and everything lands on a single **integration branch**.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: the plan file
and task id, the worktree path, the spec section, the notes directory, the commits to read. Don't duplicate information
already available via pointers.

## Start

Open a todo list with one entry per phase before launching anything.

1. Plan
2. Implement
3. Review
4. Summary

## Phase 1: Plan

1. Make sure the workspace is clean and latest from origin.
2. Launch one **planner** subagent using the configured model. It is read-only with respect to the repo. Brief it with
   the source pointer. Tell it to:
   - read the source and explore the codebase as needed;
   - modular design and information hiding principle: encode invariants in types and data structures instead of
     scattering across files and functions. If some rule will be changed only one place should be changed.
   - deep module principle: a narrow interface with substantial hidden implementation is preferred than many interfaces
     with simple implementation.
   - slice vertically by use case: every task is a tracer bullet, verifiable on its own, and free to touch several repos;
   - maximise the frontier and pin every name that crosses a task boundary;
   - do not spawn further subagents;
   - write the plan to the file `plan.md` under this session's transcript directory in the format in [references/plan.md](./references/plan.md);
   - reply to the main thread the plan path, the task count, and the tree depth.
3. Confirm with the user about the plan. Iterate by re-briefing the planner for a structural change until the user approves the plan.

## Phase 2: Implement

1. Create the integration branch for each repo. Landing, review and fixes all happen in that checkout, so it stays on
the integration branch for the rest of the run.

```bash
git -C <repo> checkout -b <integration> origin/master
git -C <repo> push -u origin <integration>
```

2. Launch a **implementer** subagent in the background for each task using the configured model. Each subagent gets the
plan path and its task id. You own the plan and subagents should not edit it. A task that touches several repos gets one
worktree per repo (find `<worktree-dir>` specified by the project and if not found, use the `.worktrees` under the repo
root) , all on the same branch name, based on the integration branch:

```bash
git -C <repo> worktree add -b <integration>-t01 <worktree-dir>/<integration>-t01 <integration>
```

Each implementer subagent:
    - confirms its worktree is based on the integration branch before starting, and resets onto it if not;
    - calls the Skill tool with `tdd` to do the task;
    - merges the integration branch tip into its own branch before reporting done

3. Once an **implementer** subagent finishes, merge its branch into the integration branch of every repo the task
touched, from that repo's original checkout, which is on the integration branch:

```bash
git -C <repo> merge --ff-only <integration>-t01
```

Update the plan's `Status` fields and recompute the frontier. Launch everything newly unblocked in parallel. Repeat until every task has finished.

## Phase 3: Review

Once all tasks are complete, launch one **code-reviewer** subagent with skill `code-review` on the integration branch
using the configured model, with the spec path as the input and the repo's original checkout as its working
directory. It writes its report to `review.md` at the session's transcript directory and returns only that path and the
finding count per axis. Fix all issues raised by code review in a single **implementer subagent**, working in the same
checkout and pointing it at that report.

## Phase 4: Summary

1. Remove every worktree of the run, then let git forget the ones already gone:

```bash
git -C <repo> worktree remove <worktree-dir>/<integration>-t01
git -C <repo> worktree prune
```

Leave the original checkout on the integration branch: switching it back is the user's call.

2. List the changes by module and why, and the proof that it works.
