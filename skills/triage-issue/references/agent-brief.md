# Agent brief

Once an issue is fully triaged and ready to implement, write a structured comment describing the design so an agent can start
implementing from it.

## Principles

### Durability over precision

The issue may stay open for a long time, and the code will change in the meantime. The brief must stay useful after the code
changes.

- Describe changes to module interfaces, contracts, and the domain model.
- Do not reference file paths or line numbers; they go stale.

### Describe external behavior, not internal implementation

Describe what the system should do, not how. The agent will explore the code and decide how to implement it.

- **Good:** When creating a task, the user can specify an approver and an expiry date.
- **Bad:** Add an approver field to CreateTaskConfigRequest.

### Explicit success criteria

The agent needs to know when it is done. Completion criteria must be verifiable.

## Template

Write the comment in Chinese using this template.

```markdown
**类型：** bug / 优化
**总结：** 一句话描述应该做什么

**当前的行为：**
描述当前的现状。对于 bug，这是复现 bug 的行为。对于优化，这是当前的现状。

**预期行为：**
描述完成后预期的行为。明确边界情况和错误处理逻辑。

**关键决策：**
- 领域模型的变化（如有）
- 状态转移图的变化（如有）
- 模块及其接口的变化

**验收标准：**
列出可验证、可执行的测试用例
```
