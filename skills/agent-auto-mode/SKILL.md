---
name: agent-auto-mode
description: Autonomously execute a coding task by selecting and following a playbook.
disable-model-invocation: true
icon: crown
color: yellow
---

## Non-negotiables

- On the first message of a task, tell the user the goal in your own words to accomplish and the problem they want to
  solve. Restate the user's goal in every subagent brief.
- **Guard the context window.** Context fills up from large outputs, long files, repeated reads, and fan-out planning.
  Delegate work that does not need the current agent's context, pass context pointers instead of copied material, and
  require subagents to return short summaries to its parent.

## Reply

Reply should be terse and clean, easy to read. Every claim should cite evidence (i.e. file:lines, or a link).

## Comments

Only comment surprises that the user can't infer from the code. Don't comment what the code has already said. Comment
the contract in headers and what the code does and why in implementation files.

## Playbooks

Open a todo list whose first items are the matched playbook's steps, copied in verbatim, before any task-specific
todos. Keep a step you choose not to do in the list with a one-line `skip: <reason>`. Match the task to a playbook below
and open its full steps at `playbooks/<title>.md` (lowercase title). Copy its steps verbatim. If the match is ambiguous
or none fits, tell the user what you found and ask the user which playbook to use; if the user chooses none, continue
without loading a playbook.

- **Feature** New behavior or changed behavior from a intent, proposal or issue.
- **Refactor** Change the code's structure without changing behavior.
