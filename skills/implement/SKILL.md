---
name: implement
description: "Implement the current spec, issue, or conversation with test-driven development, then have a code-reviewer subagent run code-review and an implementer subagent fix the findings."
user-invocable: true
disable-model-invocation: true
---

Implement the work already described in the current spec, issue, or conversation. Do not interview, and do not reopen the design.

If the user names a source, use that one. Otherwise use a spec, then an issue, then the conversation. State which source you are implementing before you write code. If they pass an issue reference, fetch it and state its title. If the reference is ambiguous, ask. If the plan lives only in the conversation, say so and implement that. Do not search for a spec file that is not there.

When the source contradicts itself or an existing ADR, stop and put the conflict in front of the user.

Keep communication with both subagents sparse, in both directions. Brief them mainly with **context pointers**: the spec path or issue reference, the review report path, research notes, the fixed point, and the commits to read. Leave out anything those pointers already hold. A source that lives only in the conversation has no pointer, so write it to a file outside the repo and pass that path.

## Process

1. Create a branch from `master` before writing any test or code. `git fetch origin`, then branch from `origin/master`. Use the branch name the user gave, or a short name for this work. Stop if the working tree is dirty. `git push -u origin HEAD` so the new branch tracks its remote. The fixed point for review is `origin/master`.

2. Drive test-driven development by [tdd-loop.md](./references/tdd-loop.md). Confirm the seams with the user before the first test, then run red → green one seam at a time.

3. Run typechecking regularly, single test files regularly, and the full test suite once at the end.

4. Commit the work to the current branch. `code-review` reads `git diff <fixed-point>...HEAD`, so the review sees nothing until this commit exists. The fixed point is `origin/master`.

5. Launch one **code-reviewer** subagent. Brief it to call the Skill tool with `code-review`. It reviews. It does not edit code, and it does not call `implement`. It writes its report to `/tmp/code-reviews/<repo-name>-<short-sha>.md` and returns only that path and the finding count for each axis.

6. Launch one **implementer** subagent, pointing it at the review report. It fixes the cited findings with the same red-green loop, commits on the current branch, and stops. It does not call the Skill tool with `implement` or `code-review`, and it does not spawn further agents. It returns only its commit SHAs and any finding it left unfixed, with the reason. If the review has no findings, skip this step.
