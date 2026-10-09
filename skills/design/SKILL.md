---
name: design
description: "Turn propose's settled conversation into one design spec and publish it to the project issue tracker: no interview, just synthesis of decisions already made."
user-invocable: true
disable-model-invocation: true
---

Turn the current conversation and codebase understanding into one design spec. Do not interview the user or present alternative designs. Synthesize decisions already made by `propose`.

## Input

Read the durable output from `propose`:

- The current conversation for the complete shared understanding.
- `.agents/GLOSSARY.md` for domain vocabulary. If `.agents/GLOSSARY-MAP.md` exists, read it and the glossary for the relevant context.
- ADRs in `.agents/adr/`. In a multi-context repo, also read `.agents/<context>/adr/` for the relevant context.

The spec is a decision record, not a place to make new decisions. Every statement in it must come from the conversation, the codebase, the glossary, or an ADR. If the design would contradict an ADR or requires a material decision that `propose` did not settle, stop and identify the missing or conflicting decision.

If there is no settled conversation to synthesize, tell the user to run `propose` first.

## Process

1. Explore the repository enough to understand its current structure and behavior. Reuse the project's domain vocabulary and respect applicable ADRs.

2. Write one spec using [the spec template](./references/spec-format.md). The template is in Chinese. Record one coherent design: problem, solution, user stories, goals, one design, and a test plan. Do not offer options for the user to choose between.

3. Do not include specific file paths or code snippets. They become stale quickly. If a prototype produced a fragment that records a decision more precisely than prose can, include only its decision-bearing portion and identify it as coming from a prototype.

4. Write the draft spec to a file outside the repository: `/tmp/design-specs/<repo-name>-<short-slug>.md` (create the directory if needed). Keep the spec body out of the conversation. Give the user the file path as a link and ask them to review it there. Apply requested changes by editing that file, then point to it again.

5. After the user confirms, publish the file's content to the project's issue tracker. If the tracker or required label vocabulary is unknown, ask the user for that configuration.

The confirmed spec is the input to implementation.

## Reference

- [Spec template](./references/spec-format.md)
