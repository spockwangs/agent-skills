## Refactor

You own the contract. Change the code structures but do not change behavior.

1. Pin the behavior contract. Explore the codebase to learn the contract. Write characterization tests to capture the
   current behavior, run them, and do not change any code under test until they pass.
2. Plan the structural changes. Invoke the skill `implement` to do the changes.
3. Prove the behavior is unchanged. Re-run the original test suite and the new characterization tests; all must pass.
4. Open a PR.

**Reply:** the structure that changed, and the proof that behavior is preserved.
