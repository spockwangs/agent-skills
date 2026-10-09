# TDD process

TDD is the red → green loop. Consult this file before and during every cycle, not after. It covers what a good test is, where tests go, where mocks go, and the rules of the loop.

When exploring the codebase, read `.agents/GLOSSARY.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs under `.agents/adr/`.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification: "user can checkout with valid cart" tells you exactly what capability exists, and it survives refactors because it doesn't care about internal structure.

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

### Anti-patterns

- **Implementation-coupled.** The test mocks an internal collaborator, tests a private method, or verifies through a side channel. The tell: the test breaks when you refactor and the behavior has not changed. A test name that describes how is the same smell.

```typescript
// BAD: mocks an internal collaborator and asserts the call
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});

// BAD: bypasses the interface
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// GOOD: verifies through the interface
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

- **Tautological.** The assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself). It passes by construction and can never disagree with the code.

```typescript
// BAD: expected value is recomputed the way the code computes it
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});
```

- **Horizontal slicing.** Writing all tests first, then all implementation. Bulk tests verify imagined behavior: you test the shape of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in vertical slices instead: one test, then one implementation, then repeat. Each test is a tracer bullet that responds to what the last cycle taught you.

## Where to test

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

Test only at pre-agreed seams. Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything, so agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?" Give each proposed seam a one-line note on what it catches and what it misses. When the source already names the seams, restate them and confirm those.

When the shape of the interface is itself unsettled (how deep the module is, where the seam belongs, what the interface should expose), settle that public interface with the user before writing the test.

## Where to mock

Mock at system boundaries only:

- External APIs (payment, email, and the like)
- Databases (sometimes; prefer a test database)
- Time and randomness
- The file system (sometimes)

Do not mock your own classes or modules, internal collaborators, or anything you control.

At a system boundary, design an interface that is easy to mock.

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

**Prefer SDK-style interfaces over a generic fetcher.** One specific function per external operation, not one function with conditional logic. Each mock then returns one shape, the test setup has no conditional logic, and it is obvious which operation a test exercises.

```typescript
// GOOD: each function is independently mockable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch("/orders", { method: "POST", body: data }),
};

// BAD: mocking requires conditional logic inside the mock
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to the review stage (`code-review`), not the red → green implementation cycle.
