---
name: daily-news
description: |
  每日新闻聚合：用 download.py 从配置的多个新闻源（RSS / Hacker News / Reddit / Twitter）并行抓取，与历史记录去重，按 URL 聚合多源报道，AI 打分排序输出报告，并在报告最开头嵌入市场情绪快照（港股恐贪指数 + 标普500ETF 溢价率），通过智能体邮箱（agent-mail）将报告 HTML 原文以邮件正文形式发送到用户邮箱。
  触发关键词：每日新闻、新闻聚合、daily news、抓取新闻。
user-invocable: true
disable-model-invocation: false
context: fork
---

# 每日新闻聚合

用 `scripts/download.py` 从配置的新闻源（`scripts/sources.yaml`）并行抓取新闻，与历史记录去重，按 URL 聚合多源报道，AI 打分排序生成报告；`scripts/report.py` 生成报告时内置市场情绪快照（港股恐贪指数 + 标普500ETF 溢价率）置于报告最开头，最后通过智能体邮箱（agent-mail）将报告 HTML 原文以邮件正文形式发送到用户邮箱（wbbtiger@gmail.com）。

## 缓存目录

所有中间文件和历史记录存放在 `~/.cache/daily-news/` 下：

```text
~/.cache/daily-news/
├── current.jsonl          # 本轮抓取的原始记录（每行一个 JSON）
├── aggregated.jsonl       # 按 URL 聚合后的最终结果
├── errors.jsonl           # 本轮抓取失败的条目
└── history/
    └── YYYY-MM-DD.jsonl   # 当天已推送过的历史记录（用于去重）
```

## 执行流程

### 第 1 步：初始化

1. 确保缓存目录存在：

```shell
mkdir -p ~/.cache/daily-news/history
```

2. 清空本轮缓存文件：

```shell
> ~/.cache/daily-news/current.jsonl
> ~/.cache/daily-news/aggregated.jsonl
> ~/.cache/daily-news/errors.jsonl
```

### 第 2 步：用 download.py 抓取各站点

调用 `scripts/download.py`，读取 `scripts/sources.yaml` 中配置的数据源（RSS / Hacker News / Reddit / Twitter），并行抓取，按统一 schema 输出 JSONL 到 current.jsonl，每行字段为：
`title, url, content, author, publish_time, source, metadata`（`publish_time` 为 ISO 8601 UTC 字符串）。

时间窗口由 `sources.yaml` 的 `time_window_hours` 控制（默认 48 小时），早于该窗口的条目自动过滤；调试全量抓取可加 `--no-filter`。

```shell
python3 scripts/download.py \
    --config scripts/sources.yaml \
    --output ~/.cache/daily-news/current.jsonl \
    --errors ~/.cache/daily-news/errors.jsonl
```

说明：
- 成功条目写入 current.jsonl，失败条目（如源不可达、Reddit 403 封锁）写入 errors.jsonl，单源失败不阻塞其它源。
- Twitter 需设置环境变量 `APIFY_TOKEN`（变量名可在 sources.yaml 的 `apify_token_env` 配置），否则自动跳过、不计为失败。
- 退出码：0 正常；1 无任何成功条目；2 参数/配置错误。若退出码为 1，输出「本轮无新增新闻」并结束流程。

### 第 3 步：与历史记录去重

调用 scripts/dedup.py 对本轮抓取结果进行去重：

```shell
python3 scripts/dedup.py ~/.cache/daily-news/current.jsonl
```

脚本自动根据当天日期往前推 7 天，加载 ~/.cache/daily-news/history/YYYY-MM-DD.jsonl（存在的文件），执行以下去重规则：
1. current 内部 URL 去重：同一 URL 只保留首次出现的条目
2. 与近 7 天历史 URL 精确去重：移除已出现在近 7 天历史记录中的 URL

去重后结果原地覆盖 current.jsonl。脚本输出去重统计（如 80 条 → 62 条（移除 18 条重复））。

如果脚本退出码为 1（去重后无记录），则输出提示"本轮无新增新闻"并结束流程。

### 第 4 步：按 URL 聚合 + 并行打分

#### 4.1 按 URL 聚合（脚本）

调用 scripts/cluster.py，输入去重后的 current.jsonl，输出聚合结果 aggregated.jsonl：

```shell
python3 scripts/cluster.py \
    ~/.cache/daily-news/current.jsonl \
    ~/.cache/daily-news/aggregated.jsonl
```

脚本规则：
1. 按 URL 精确匹配分组（同一 URL 的多条记录合并为一条）
2. `title` / `publish_time`：取 content 最长的那条记录的值
3. `content`：多条记录的 content 用 `--- From {source} ---` 分隔串联；单条记录直接取 content
4. `sources`：所有记录的 {url, source} 取并集

输出 aggregated.jsonl 每行格式：

```json
{"id": 0, "title": "标题", "content": "正文内容", "sources": [{"url": "...", "source": "..."}], "publish_time": "时间"}
```

`id` 为从 0 开始的顺序整数，作为该条记录在全流程中的唯一标识，后续打分回写时按 `id` 匹配而非按行号位置匹配。

#### 4.2 并行打分与一句话摘要（子 Agent）

将 aggregated.jsonl 中的记录分批（每批约 40 条），为每批启动一个子 Agent（`run_in_background: true`）并行打分。子 Agent 将结果**写入文件**而非文本返回，合并时按 `id` 匹配回写，彻底避免位置错位。

**分批**：读取 aggregated.jsonl，按 ~40 条一批切分，保存为 JSON 数组到 `~/.cache/daily-news/batches/batch_{i}.json`，每项保留 `id`、`title`、`content`（截断至 1500 字）：

```python
import json, os

records = []
with open(os.path.expanduser('~/.cache/daily-news/aggregated.jsonl')) as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

batch_size = 40
os.makedirs(os.path.expanduser('~/.cache/daily-news/batches'), exist_ok=True)
for i in range(0, len(records), batch_size):
    batch_idx = i // batch_size
    batch = [{'id': r['id'], 'title': r.get('title', ''), 'content': r.get('content', '')[:1500]}
             for r in records[i:i+batch_size]]
    with open(os.path.expanduser(f'~/.cache/daily-news/batches/batch_{batch_idx}.json'), 'w') as f:
        json.dump(batch, f, ensure_ascii=False)
print(f'共 {len(records)} 条，分成 {(len(records) + batch_size - 1) // batch_size} 批')
```

**子 Agent 提示**（每个子 Agent 处理一批，`run_in_background: true`）：

```text
你是新闻评分助手。这是一个研究任务。

请读取文件 {batch_file_path}，其中包含一个 JSON 数组，每项有 id、title 和 content 字段。

对每条新闻，根据 content 完成两项任务：

任务 1 — 打分（满分 10 分，整数）：
- 新颖性（0-5分）：是否为首次报道的新事件/新发现，而非旧闻翻新或例行报道
- 突发性（0-5分）：是否代表重大技术突破、政策转向、市场拐点、或颠覆性事件

打分参考：
- 9-10 分：颠覆性事件（如重大科学突破、战争爆发/结束、划时代产品发布）
- 7-8 分：重要行业/政策新闻（如大型并购、重要政策出台、重大漏洞披露）
- 5-6 分：有价值但非突破性的报道（如产品更新、常规财报、行业趋势分析）
- 3-4 分：例行报道或影响较小的事件
- 1-2 分：旧闻翻新、无实质新信息、或过于小众

任务 2 — 一句话摘要（50-100字），保留最核心的事实，不要评价性修饰。

将结果写入文件 {score_file_path}，格式为 JSON 数组，每个元素必须包含 id 字段：
[{"id": 0, "score": 8, "one_liner": "..."}, {"id": 1, "score": 5, "one_liner": "..."}, ...]
id 必须与输入一致，顺序不重要。只写入文件，不要输出其它内容。
```

其中 `{batch_file_path}` = `~/.cache/daily-news/batches/batch_{i}.json`，`{score_file_path}` = `~/.cache/daily-news/batches/batch_{i}_scores.json`。

**收集与回写**：所有子 Agent 完成后，运行合并脚本按 `id` 匹配回写到 aggregated.jsonl：

```python
import json, glob, os

# 读取原始记录
records = []
with open(os.path.expanduser('~/.cache/daily-news/aggregated.jsonl')) as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

# 读取所有打分文件，按 id 建索引
score_map = {}
for path in sorted(glob.glob(os.path.expanduser('~/.cache/daily-news/batches/batch_*_scores.json'))):
    with open(path) as f:
        for s in json.load(f):
            score_map[s['id']] = s

# 按 id 回写
missing = 0
for r in records:
    s = score_map.get(r.get('id'))
    if s:
        r['score'] = s.get('score', 0)
        r['one_liner'] = s.get('one_liner', '')
    else:
        r['score'] = 0
        r['one_liner'] = ''
        missing += 1

with open(os.path.expanduser('~/.cache/daily-news/aggregated.jsonl'), 'w') as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f'打分完成: {len(records)} 条' + (f'，WARNING: {missing} 条缺少打分' if missing else ''))
```

### 第 5 步：生成报告并通过智能体邮箱发送

1. 调用 scripts/report.py 生成 **HTML 格式**报告到 `~/.cache/daily-news/report.html`（默认 `--format html`；如需旧格式可加 `--format markdown`）。只保留打分 ≥ 6 的新闻（`--min-score` 可调），低于阈值的条目在报告中剔除。report.py 会**内置生成市场情绪快照**（港股恐贪指数 + 标普500ETF 溢价率）并置于报告最开头（标题之后、新闻之前），无需额外步骤：

```shell
python3 scripts/report.py ~/.cache/daily-news/aggregated.jsonl --errors ~/.cache/daily-news/errors.jsonl --min-score 6 > ~/.cache/daily-news/report.html
```

快照内容与容错：
- **港股恐贪指数**：内置守猪逮兔 API 逻辑（签名 + 请求 + 过滤，不依赖其他技能），覆盖腾讯(00700)/美团(03690)/京东(09618)/阿里巴巴(09988)四只港股，输出表格 + 情绪彩色标签 + 更新时间。
- **标普500ETF 博时(513500) 溢价率**：腾讯行情接口取场内现价 + 东方财富基金净值接口取官方单位净值，计算溢价率 = (现价 − 单位净值) ÷ 单位净值；溢价 ≥ 5% 时附加红色高溢价风险提示。
- 单个数据源失败不阻塞整体：失败区块显示「数据暂不可用」占位；全部失败时仅不显示快照标题，继续新闻流程（不中断每日简报）。
- 如需跳过快照可加 `--no-snapshot`，单独跳过港股/ETF 可加 `--no-hk` / `--no-etf`。

2. 通过智能体邮箱将报告 HTML 原文以**邮件正文**形式发送（不做任何摘要处理，不附带附件）：
   - 读取 `~/.cache/daily-news/report.html` 的完整内容
   - 调用 `mcp__agent-mail__SendMessage`（通过 ToolSearch 加载 schema 后用 DeferExecuteTool 调用），参数：
     - `to`: `[{"email": "wbbtiger@gmail.com"}]`
     - `subject`: 取 report.html 的 `<title>` 内容
     - `body`: report.html 完整 HTML 文本
     - `body_format`: `"HTML"`
     - `skip_confirmation`: `true`
     - **不传 `attachments`，不传 `file_refs`**
   - 用户已授权每日自动推送；若返回 `CONFIRMATION_REQUIRED`，展示 `operation_summary` 请用户确认后带 `confirmation_token` 重试（自动化运行无人确认时在回复中说明「简报已生成，等待确认发送」，不视为失败）
   - agent-mail 不可用时回退 SMTP 方案：`EMAIL_TO=wbbtiger@gmail.com SMTP_APP_PASSWORD=... python3 scripts/send_email.py --report ~/.cache/daily-news/report.html`（send_email.py 自动识别 HTML/Markdown）；两者都不可用时提示「简报已生成于 ~/.cache/daily-news/report.html」，不视为失败

### 第 6 步：归档历史

推送完成后，将本轮记录归档：

1. 将 ~/.cache/daily-news/current.jsonl 的内容追加到 ~/.cache/daily-news/history/YYYY-MM-DD.jsonl
2. 清空 ~/.cache/daily-news/current.jsonl 和执行过程中生成的其它临时文件。

```shell
cat ~/.cache/daily-news/current.jsonl >> ~/.cache/daily-news/history/$(date +%Y-%m-%d).jsonl
> ~/.cache/daily-news/current.jsonl
```

3. 清理超过 30 天的历史记录：

```shell
find ~/.cache/daily-news/history -name "*.jsonl" -mtime +30 -delete
```

# 外部配置

`scripts/sources.yaml` — 数据源配置（YAML）。顶层 `time_window_hours` 控制时间窗口；`sources` 列表中每项通过 `type` 选择抓取器（`rss` / `hackernews` / `reddit` / `twitter`）并附带各自参数（如 subreddit、min_score、apify_token_env 等）。新增/修改数据源只需编辑此文件。

如果用户传入了自定义 URL 列表，将其转为一份临时 sources.yaml（每条 `type: rss`，给出 `name` 与 `url`）传给 `--config`，忽略默认配置。

## 关键注意事项

1. **抓取**：`download.py` 在内部并行抓取所有配置源，单源失败不阻塞其它源，失败条目写入 errors.jsonl，由最终报告的「⚠️ 抓取失败」区块呈现。
2. **避免并发写入**：`download.py` 统一写 current.jsonl / errors.jsonl，无需多 Agent 协调；第 4.2 步的打分子 Agent 各自将结果写入独立的 `batch_{i}_scores.json` 文件（不返回文本），由合并脚本按 `id` 匹配后统一回写 aggregated.jsonl，避免位置错位。
3. **只抓配置源，严禁搜索引擎补救**：只能抓取 `scripts/sources.yaml` 中配置的数据源（或用户传入的自定义 URL 列表）。禁止使用 WebSearch、Google、Bing 或任何搜索引擎搜索新闻作为补充，禁止跳转到未配置的外部站点抓取。抓取失败/内容不足时按 errors 原样上报，宁缺毋滥。
4. **字段统一**：全流程统一字段名 —— `download.py` 输出 `content`/`source`，`cluster.py` 读写 `content`/`source`，`report.py` 渲染 `source`，无需任何别名映射。
5. **时间窗口**：默认仅保留最近 `time_window_hours`（48）小时内的条目；`--no-filter` 可抓全量（仅调试用）。
6. **容错**：单个源抓取失败不应阻塞整个流程，跳过并在最终报告中提示。
