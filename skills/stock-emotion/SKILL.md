---
name: stock-emotion
description: |
  获取港股恐贪指数并通过邮件发送报告。
  覆盖腾讯、美团、京东、阿里巴巴四只港股，数据来源为守猪逮兔估值模型。
  触发关键词：港股恐贪指数、恐贪指数、stock emotion、港股情绪。
user-invocable: true
---

# 港股恐贪指数

获取港股恐贪指数数据，生成报告并通过智能体邮箱发送给用户。

## 覆盖股票

- 腾讯 (00700)
- 美团 (03690)
- 京东 (09618)
- 阿里巴巴 (09988)

## 收件配置

- 发件人：spockwang@agent.qq.com（智能体邮箱，已开通）
- 收件人：wbbtiger@gmail.com
- 发送工具：agent-mail（`mcp__agent-mail__SendMessage`，`skip_confirmation=true`）

## 执行流程

### 第 1 步：获取数据

运行脚本获取港股恐贪指数，输出 HTML 格式报告：

```shell
python3 scripts/stock_emotion.py --format html
```

脚本调用守猪逮兔 API，获取目标股票的恐贪指数、市价和情绪标签，输出 HTML 格式报告到 stdout（也支持 `--format markdown` 输出 Markdown）。

如果脚本退出码为 1，表示 API 请求失败，将错误信息告知用户并结束流程。

### 第 2 步：通过智能体邮箱发送

将脚本输出的完整 HTML 内容作为**邮件正文**（`body_format=HTML`）通过 agent-mail 发送给用户，不做任何裁剪或修改：

- 主题示例：`港股恐贪指数（2026-08-13）`（日期取当天）
- 正文：脚本输出的 HTML 报告全文
- 调用 `mcp__agent-mail__SendMessage`，`skip_confirmation=true`（每日自动推送场景无需人工确认；若被拦截需展示摘要等用户确认）

若 agent-mail 不可用，将脚本输出的 Markdown 报告（`--format markdown`）直接展示给用户，并提示报告已生成。

### 注意事项

1. 脚本输出即为最终报告，**严禁对输出内容做任何修改、裁剪或重新格式化**
2. 恐贪指数分档：≤-60 极度恐惧 | -60~-20 恐惧 | -20~20 中性 | 20~60 贪婪 | ≥60 极度贪婪
3. 数据来源：守猪逮兔估值模型 (https://fe.szdt.tech/invest/?futusource=nnq_im#/etf_hk)
