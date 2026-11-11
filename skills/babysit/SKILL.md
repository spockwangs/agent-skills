---
name: babysit
description: "Keep a PR merge-ready by triaging comments and fixing CI in a loop."
disable-model-invocation: true
---

# Babysit

1. Launch a **implementer** subagent in the background (using the configured implementer model) for each PR in the
   conversation with the repo, PR link and the source branch.
2. Loop until the PR is merge ready. During the loop
   - reply to the commenter with why if the comment is not correct
   - fix the comment in a independent worktree if the comment is correct and reply and resolve the comment when done
3. When the PR is merge ready (all comments are resolved and CI is OK), summarize fixes if any and why.
