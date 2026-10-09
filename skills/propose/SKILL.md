---
name: propose
description: Interviews the user relentlessly about a plan or design until a shared understanding is reached, and writes vocabulary and hard decisions under .agents as they crystallise (.agents/GLOSSARY.md and .agents/adr/). Use when the user wants to propose a change, stress-test a plan against a codebase, or settle domain language before specifying it.
user-invocable: true
disable-model-invocation: true
---

Call the Skill tool with "grill" and run that interview.

During the same session, build and sharpen the project's domain model using the discipline below.

# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline: challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely *reading* `.agents/GLOSSARY.md` for vocabulary is not this discipline: that's a one-line habit any skill can do. This discipline is for when you're changing the model, not just consuming it.)

## File structure

Glossary and ADRs both live under `.agents/`, directly in that directory. `.agents/skills/` is the installed skills tree; leave it alone.

Most repos have a single context:

```
/
├── .agents/
│   ├── GLOSSARY.md
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If `.agents/GLOSSARY-MAP.md` exists, the repo has multiple contexts. The map points to where each one lives, still under `.agents/`:

```
/
├── .agents/
│   ├── GLOSSARY-MAP.md
│   ├── adr/                          ← system-wide decisions
│   ├── ordering/
│   │   ├── GLOSSARY.md
│   │   └── adr/                      ← context-specific decisions
│   └── billing/
│       ├── GLOSSARY.md
│       └── adr/
└── src/
```

Create files lazily: only when you have something to write. If no `.agents/GLOSSARY.md` exists, create one when the first term is resolved. If no `.agents/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `.agents/GLOSSARY.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account': do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which is right?"

### Update GLOSSARY.md inline

When a term is resolved, update `.agents/GLOSSARY.md` right there. Don't batch these up: capture them as they happen. Use the format in [GLOSSARY-FORMAT.md](./references/GLOSSARY-FORMAT.md).

`.agents/GLOSSARY.md` should be totally devoid of implementation details. Do not treat it as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse**: the cost of changing your mind later is meaningful
2. **Surprising without context**: a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off**: there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./references/ADR-FORMAT.md).
