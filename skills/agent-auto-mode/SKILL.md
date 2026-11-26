---
name: agent-auto-mode
description: Autonomously execute a coding task by matching a playbook and following its steps.
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
the contract at declarations and what the code does and why at implementations.

## Playbooks

1. Match the task to a playbook below.
2. If exactly only one matches open a todo list whose first items are the steps of matched playbook at
   `playbooks/<title>.md` (lowercase title). Copy its steps verbatim before any task-specific todos. Keep a step you
   choose not to do in the list with a one-line `skip: <reason>`.
3. Otherwise, if the match is ambiguous or none fits, tell what you found and ask a question for the user to choose a
playbook. Load the playbook chosen by the user; if the user chooses none, continue without loading a playbook.

- **Feature** New behavior or changed behavior from a intent, proposal or issue.
- **Refactor** Change the code's structure without changing behavior.
- **Investigate** Answer a question about existing code or behavior. No code changes.
