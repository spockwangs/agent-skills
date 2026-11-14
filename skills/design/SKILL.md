---
name: design
description: "Turn the settled proposal into one design spec to be implemented."
user-invocable: true
disable-model-invocation: true
---

Turn the settled proposal (from current conversation or a file) into one design spec to be implemented. If there is no
settled proposal to synthesize, tell the user to run `propose` first.

## Process

1. Explore the repository enough to understand its current structure and behavior. Design by conforming to following principles
   - minimize changes by reusing existing models, interfaces and codes if possible;
   - do not break existing contracts. If we have to, notify the user;
   - encode invariants in models, types and data structures instead of scattering across functions;
   - deep module principle: a small number of public interfaces with complicated implementations instead of many public
     interfaces with a simple implementation;

2. Write the spec using [the spec template](./references/spec-format.md). The template is in Chinese. Do not include specific file paths or code
   snippets. They become stale quickly. If a prototype produced a fragment that records a decision more precisely than
   prose can, include only its decision-bearing portion and identify it as coming from a prototype.

4. Write the draft spec to `spec.md` in the session's transcript directory. Give the file path to the user for
   review. Apply requested changes by editing that file, then point to it again.

5. After the user confirms, publish the file's content verbatim to the project's issue tracker as ready if the proposal
   comes from an issue tracker.
