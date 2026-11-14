---
name: create-pr
description: "Create a pull request for a repo via available tools. Use when creating a PR, or pull request.
user-invocable: true
disable-model-invocation: true
---

# Create PR

1. Commit local changes.
2. Run unit tests and if there is any failure launch a **implementer** subagent to fix and commit.
3. Find the PR title and body format required by this project (AGENTS.md, CLAUDE.md etc). Otherwise use the following.
   - Title: `type(scope): subject`. Type is `feat`, `fix`, `refactor`, or `test`. Scope is about product, business or
     feature. Subject is short, imperative.
   - Body: brief words about why the changes exist, what changes and proof that it works.
     - `## Why`: the problem statement.
     - `## What changed`: short bullets of changes.
     - `## Tradeoffs`: rejected alternatives. Skip when there is none.
     - `## Blast radius`: who or what it touches and will be affected. Why it is safe or risky.
     - `## Verification`: a short bullets of proof that the change worked.
4. Create PR via available tools and present the PR link to the user.
