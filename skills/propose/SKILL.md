---
name: propose
description: Interviews the user relentlessly about an idea or a requirement until a shared understanding is reached. Use when the user wants to propose a change, stress-test a plan against a codebase, or settle domain language before specifying it.
user-invocable: true
disable-model-invocation: true
---

Call the Skill tool with "grill" and run that interview.

During the same session, build and sharpen the proposal using the discipline below.

- Sharpen fuzzy language. When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying
  'account': do you mean the Customer or the User? Those are different things."
- Walk the user stories one by one using behavior analysis. What is the input, output and observed effects for each user
  story? What if the input is invalid/ What if the operation can't be executed under certain conditions?
- Actively build and sharpen the project's domain model as you design to satisfy the user story. This is the *active*
  discipline: challenging terms, inventing edge-case scenarios.
- When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe
  edge cases and force the user to be precise about the boundaries between concepts.
- Cross-reference with code. When the user states how something works, check whether the code agrees. If you find a
  contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which
  is right?"

## Outputs

After the interview is completed, write the proposal to `intent.md` in the session's transcript directory in the format
of `references/intent.md`. If the idea comes from an issue tracker, publish the proposal verbatim as comments.
