---
name: agent-setup
description: "Configure the models the agent uses per role. Detect available models and writes an always applied rule that overrides the default."
user-invocable: true
disable-model-invocation: true
---

# Agent Setup

Write per-role model settings in a file that will be applied by current agent for all sessions.

- Cursor: `~/.cursor/rules/models.mdc`
- Claude Code: `~/.claude/rules/models.md`
- CodeBuddy: `~/.codebuddy/rules/models.mdc`
- Other harnesses: merge with `~/.agents/AGENTS.md` which will be loaded into every session.

## Steps

### 1. List the available model ids

List the model slugs and efforts that you can pass to a subagent in this session.

### 2. Load current model setting

If the model setting already exists, read it and treat it as default.

### 3. Confirm, validate and write

Ask for a model for each role in the template shape. Validate the model slug must be in the detected set. Write the file
to appropriate places specified by the harness. Overwrite the whole file so re-runs stay idempotent.

```markdown
# model configuration: one line per role.
implementer: <chosen-model>
code-reviewer: <chosen-model>
planner: <chosen-model>
```
