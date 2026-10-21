---
name: tdd
description: "Test-driven development: the red to green loop. Use when building a feature or fixing a bug test-first, when the user asks for tests before code, or when a task brief tells you to build with tdd."
user-invocable: true
disable-model-invocation: false
---

# Test-Driven Development

TDD is the red to green loop: write the failing test, then write only enough code to pass it, then repeat. This skill is the reference that makes that loop produce tests worth keeping: what a good test is, where tests go, where mocks go, and the rules of the loop. Consult it before and during every cycle, not after.

When exploring the codebase, read `GLOSSARY.md` or `.agents/GLOSSARY.md` if it exists, so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you are touching.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests should not have to. A good test reads like a specification: "user can checkout with valid cart" tells you exactly what capability exists, and it survives refactors because it does not care about internal structure.

A good test:

- Tests behavior users or callers care about
- Uses the public API only
- Survives internal refactors
- Describes what, not how
- Makes one logical assertion

```typescript
// GOOD: tests observable behavior
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

Expected values come from an independent source of truth: a known-good literal, a worked example, or the spec.

```typescript
// GOOD: expected value is an independent, known literal
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```

But do not over-engineer for the sake of testing. If the expected behavior is hard to verify through public interfaces, verifying by mocking the internals is acceptable.

## Where to test: seams

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test. You cannot test everything, so agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

If you are in a session with the user, confirm the seams before the first test: "What's the public interface, and which seams should we test?" Give each proposed seam a one-line note on what it catches and what it misses. When the task brief or the spec already names the seams, restate them and confirm those.

If you are running as a subagent with no user to ask, take the seams from the task brief and record them in your report. Do not stall waiting for confirmation you cannot get.

When the shape of the interface is itself unsettled (how deep the module is, where the seam belongs, what the interface should expose), settle that public interface before writing the test.

## Where to mock

Mock at system boundaries only:

- External APIs (payment, email, and the like)
- Databases (sometimes; prefer a test database)
- Time and randomness
- The file system (sometimes)

Do not mock your own classes or modules, internal collaborators, or anything you control. At a system boundary, design an interface that is easy to mock.

**Use dependency injection.** Pass external dependencies in rather than creating them internally.

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Do not anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle. Each test is a tracer bullet that responds to what the last cycle taught you.
- **Vertical slices, never horizontal.** Do not write all tests first and then all implementation. Bulk tests verify imagined behavior: they test the shape of things rather than user-facing behavior, and they commit you to a test structure before you understand the implementation.
- **No refactoring inside the loop.** Refactoring belongs to the review stage (`code-review`), not to the red to green cycle.

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior has not changed.
- **Tautological**: the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code.

## Done when

- Every behavior you implemented has a test that failed before the code existed.
- The tests read as specification and go through public interfaces.
- Typechecking passes, and the test suite for the touched packages passes.
- You can report, per cycle, the seam, the test, and the minimal implementation that turned it green.
