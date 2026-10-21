---
name: implement-parallel
description: "Land a large spec by splitting it into a task tree and running implementer subagents in parallel, each in its own git worktree, all merged onto one integration branch. Use when a spec is too big for one `implement` run and its parts can be built at the same time."
user-invocable: true
disable-model-invocation: true
---

Implement the work already described in the current spec, issue, or conversation which is too big for a single agent. A
planner subagent splits it into a **task tree** with blocking relationships between them, and implementer subagents
build the frontier of tasks in parallel, and everything lands on a single **integration branch**.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: the plan file
and task id, the worktree path, the spec section, the notes directory, the commits to read. Don't duplicate information
already available via pointers.

## Process

### 1. Fix the source and the repo

Confirm the repo root, the base (`origin/master` unless the user names another), and that the working tree is
clean. Fetch. Everything below runs from the repo root.

Pick `<feature>`, a short slug for this run. Everything this skill writes lives under
`~/.agents/implement-parallel/<feature>`, the **run directory** (`<run-dir>`): the plan, the exploration notes, the
review report, and the task worktrees. Nothing intermediate goes inside the repo.

### 2. Planner subagent: build the task tree

Launch one **planner** subagent. It is read-only with respect to the repo: it may explore and run searches, but it must not edit code.

Brief it with the source pointer and the plan file path, `<run-dir>/plan.md` (create the directory first). Tell it to:
- read the source and explore the codebase as needed, saving markdown notes under
  `<run-dir>/notes/` so every later implementer can read them instead of re-exploring;
- slice vertically by use case: every task is a tracer bullet, verifiable on its own, and free to touch several repos;
- write the plan in the format in [references/task-plan.md](./references/task-plan.md);
- maximise the frontier and pin every name that crosses a task boundary;
- do not spawn further subagents;
- return only the plan path, the task count, and the tree depth.

### 3. Put the plan in front of the user

Give the user the plan file path and ask the user:
- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct: does each task only depend on tasks that genuinely gate it?
- Should any task be merged or split further?

Iterate by re-briefing the planner for a structural change until the user approves the plan.

### 4. Create the integration branch

Confirm the integration branch name with the user: the same name in every repo. Create it and check it out in the
original checkout. There is no integration worktree.

```bash
git -C <repo> branch <integration> origin/master
git -C <repo> checkout <integration>
```

Landing, review and fixes all happen in that checkout, so it stays on the integration branch for the rest of the
run: that is the cost of not having a worktree, and it is why step 1 insists on a clean tree.

Task worktrees are the only worktrees, at `<run-dir>/worktrees/<repo>/<task>`. One caveat: **some repos care where
they sit.** If a repo's build or tests reach for siblings by relative path, put its worktrees next to the repo
(`../<repo>-<branch>`) instead, and note the exception in the plan.

### 5. Launch the frontier

Launch a **implementer subagent** in the background for each task. A task that touches several repos gets one
worktree per repo, all on the same branch name, based on the integration branch:

```bash
git -C <repo> worktree add -b <integration>-t01 <run-dir>/worktrees/<repo>/t01 <integration>
```

Each implementer subagent:
    - confirms its worktree is based on the integration branch before starting, and resets onto it if not;
    - calls the Skill tool with `tdd` to do the task;
    - merges the integration branch tip into its own branch before reporting done

### 6. Land each finished task

Once an **implementer subagent** finishes, merge its branch into the integration branch of every repo the task
touched, from that repo's original checkout, which is on the integration branch:

```bash
git -C <repo> merge --ff-only <integration>-t01
```

### 7. Recompute the frontier and go again

After each landing, recompute the frontier from the plan's `Status` fields, not from memory. Launch everything newly unblocked in parallel. Repeat until every task has landed.

### 8. Review the integration branch

Once all tasks are complete, launch one **code-reviewer subagent** with skill `code-review` on the integration
branch, with the repo's original checkout as its working directory. It writes its report to `<run-dir>/review.md`
and returns only that path and the finding count per axis. Fix all issues raised by code review in a single
**implementer subagent**, working in the same checkout and pointing it at that report.

### 9. Cleanup

Remove every worktree of the run, then let git forget the ones already gone:

```bash
git -C <repo> worktree remove <run-dir>/worktrees/<repo>/t01
git -C <repo> worktree prune
```

Leave the original checkout on the integration branch: switching it back is the user's call.

Keep `<run-dir>` until the user is done with it: it still holds the plan and the review report. Nothing cleans it
for you, so prune abandoned run directories under `~/.agents/implement-parallel/` yourself.
