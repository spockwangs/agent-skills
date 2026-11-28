## Bug-fix

You own the task. Plan, review and verify. Delegate investigation and fix to subagents.

1. Reproduce the bug. Add tests to capture the bug.
2. Identify the cause by binary search. Explore the code to guess some candidate hypotheses. Then rule them out until
   one survives. The hypotheses must be accepted or rejected by observed evidence. You can add tests, instrumentation or
   logging to observe the running code.
3. Plan the fix. If it crosses module boundary, invoke `/implement` to fix.
4. Verify on the same surface. The original reproduce now passes.
5. Open a PR.

**Reply:** what was broken, its root cause, fix and how it is verified.
