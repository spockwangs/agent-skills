# TDD 红→绿循环参考

`implement` 在每个 seam 上跑红→绿循环时对照本文件。每个循环都适用，循环前后都要看，不是事后才看。

## 什么是好测试

测试透过**公共接口**验证**行为**，不验证实现细节。代码可以整个重写，测试不该动。一个好测试读起来像规格说明："客户能用有效购物车结算"告诉你存在什么能力，并且能在重构后存活，因为它不在乎内部结构。

## 循环规则

- **先红后绿**：先写失败的测试，再只写让它通过的最小代码。不预演未来的测试、不加投机功能。
- **一次一片**：一个 seam、一个测试、一段最小实现，构成一个循环。
- **垂直切片，不要水平切片**：不要先把所有测试写完再实现。批量测试验证的是**想象中**的行为，你会测事物的形状而不是用户面对的行为，并且在理解实现之前就锁死了测试结构。一片测试 → 一片实现 → 重复，每片是响应上一片结果的示踪弹。
- **重构不在循环里**：重构属于收尾的自审环节，不在红→绿实现循环中混做。

## 反模式

### 实现细节耦合

mock 了内部协作对象、测了私有方法、或通过旁路验证（查数据库而不是用接口）。

**信号**：重构后行为没变，测试却挂了。

```typescript
// BAD：mock 内部协作对象，断言调用
test("checkout 调用 paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});

// GOOD：透过接口断言外部行为
test("客户能用有效购物车结算", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

### 同义反复（Tautological）

期望值用代码自己的方式重新算了一遍，于是测试按构造就通过，永远无法与代码意见相左。期望值必须来自**独立的真值来源**：已知的字面量、手算的例子、spec。

```typescript
// BAD：期望值用实现的方式重算
test("calculateTotal 求和", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// GOOD：期望值是独立的已知字面量
test("calculateTotal 求和", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```

### 旁路验证

绕过接口去查内部状态。

```typescript
// BAD：绕过接口查数据库
test("createUser 存进数据库", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// GOOD：透过接口验证可观察行为
test("createUser 让用户可被取回", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

## mock 纪律

只在**系统边界**上 mock：

- 外部 API（支付、邮件等）
- 数据库（有时——优先用测试 DB）
- 时间 / 随机性
- 文件系统（有时）

**不要 mock**：你自己的类 / 模块、内部协作对象、任何你控制的东西。

在系统边界上为可测性设计接口：

1. **用依赖注入**：外部依赖传进来，而不是在内部 new 出来
2. **优先 SDK 风格接口**：每个外部操作一个具体函数，而不是一个带条件分支的通用 fetcher——这样每个 mock 只返回一种形状，测试 setup 里没有条件逻辑
