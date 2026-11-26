# Smell Baseline (the floor of the Standards axis)

The Standards axis of `code-review` always carries this fixed set of Fowler code smells (*Refactoring*, Chapter 3) on top of the standards recorded in the repository. It applies even when the repo records no standards at all.

Two rules constrain it:

- **Repository first.** Recorded repo standards always win; when a repo standard endorses something the baseline would flag, suppress that smell.
- **Always a judgment call.** Each smell is a labeled heuristic ("suspected Feature Envy"), never a hard violation. Skip everything a tool already enforces.

Each smell is written as *what it is* → *how to fix*; hold it against the diff:

- **Mysterious Name**: the name of a function, variable, or type doesn't reveal what it does or holds. → Rename it; if you can't think of an honest name, the design itself is murky.
- **Duplicated Code**: the same logical shape recurs across multiple hunks or files of this change. → Extract the shared shape and call it from both places.
- **Feature Envy**: a method reaches into another object's data more than into its own. → Move the method onto the data it envies.
- **Data Clumps**: the same few fields or parameters always travel together (a type that wants to be born). → Bundle them into a type and pass that type.
- **Primitive Obsession**: a primitive or string stands in for a domain concept that deserves its own type. → Give the concept its own small type.
- **Repeated Switches**: the same `switch` / `if` ladder over the same type recurs within this change. → Replace with polymorphism, or share one mapping between the sites.
- **Shotgun Surgery**: one logical change forces the diff to scatter edits across many files. → Gather what changes together into one module.
- **Divergent Change**: one file or module gets changed for several unrelated reasons. → Split it so each module changes for only one reason.
- **Speculative Generality**: abstractions, parameters, or hooks added for needs the spec doesn't have. → Delete them; inline back until a real need appears.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → Hide the traversal behind a method on the first object.
- **Middle Man**: a class or function that does little more than forward. → Cut it out and call the real target directly.
- **Refused Bequest**: a subclass or implementer ignores or overrides most of what it inherits. → Drop the inheritance; use composition instead.

## Usage

When spawning the Standards subagent, paste the full text of this file into its briefing — the subagent has no other way to read it. The subagent holds each smell against every hunk of the diff; on a hit it names it ("suspected Feature Envy"), cites the hunk, and attaches the *how to fix*.
