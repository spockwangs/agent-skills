你正在抓取 RSS/Atom 新闻源。这是一个研究任务，不需要编写代码文件。

站点名称：{site_name}
Feed URL：{feed_url}

时间过滤：只保留最近 48 小时内发布的新闻。当前时间为 {now_iso}，截止时间为 {cutoff_iso}。
发布时间早于截止时间的条目直接跳过，不抓取详情、不计入结果。
发布时间无法确定的条目保留（宁可多抓，后续去重兜底）。

执行步骤：
1. 用 WebFetch 抓取上述 Feed URL，提示词为：
   "这是一个 RSS 或 Atom feed。请提取所有条目，对每条输出 JSON 格式：title（标题)、link（原文链接）、summary（摘要，如果太短则标记为 incomplete）、publish_time（发布时间，转为 ISO 8601 格式，如无法确定则填空字符串）。 输出一个 JSON 数组。"

   收到结果后，先按 publish_time 过滤：丢弃早于 {cutoff_iso} 的条目。publish_time 为空的条目保留。

**工具降级**:如果当前环境没有 WebFetch 工具可用(例如调用报错"tool not available"或权限不足),改用 Bash 调用 `curl` 或 `wget` 抓取同一 URL 的原始内容,再自行解析。推荐命令:
- `curl -sSL -A "Mozilla/5.0" --max-time 30 "{url}"`
- `wget -qO- --user-agent="Mozilla/5.0" --timeout=30 "{url}"`
抓到原始 XML/HTML 后,按同样的提取规则解析 RSS/Atom 条目。curl/wget 仅作为 WebFetch 不可用时的等价替代,不改变站点范围与抓取规则。

2. 对返回的每条条目：
- 如果 summary 内容充实（≥50字），将其精炼为 120–180 字的中文摘要
- 如果 summary 标记为 incomplete 或内容过短，用 WebFetch 抓取 link 对应的原文页面（若 WebFetch 不可用,同样改用 curl/wget 抓取原文后自行摘要），
提示词为："提取这篇新闻的正文内容，生成 120–180 字的中文摘要。
摘要写作要求：
（1）必须覆盖 5W1H 中在原文出现的要素（Who / What / When / Where / Why / How），至少 3 项；
（2）必须包含至少一个具体数字或专有名词（金额/比例/时间点/人名/公司名/产品名/机构名/地名等），不得全部以泛化表述充数；
（3）禁止使用评价性空话，如'积极''重要''值得关注''引发广泛关注''具有重要意义'等；
（4）禁止出现'据报道''有消息称'等无信息量的套话；
（5）如原文信息不足以填满 120 字，如实写到信息边界为止，不要虚构或注水。"

如果 WebFetch 返回的内容明显是"空壳"(例如:正文文字 < 50 字、只剩 CSS/JS 代码、只有骨架屏/导航/页脚、只有 `<div id="root">` 之类的 SPA 容器、或明确提示"需要启用 JavaScript"),改用 Playwright 操作无头浏览器重新抓取同一 URL:

- 优先通过 Playwright MCP(如已配置)调用 `browser_navigate` 打开 URL,等待页面加载完成后用 `browser_snapshot` 或 `browser_evaluate` 取 `document.body.innerText` / 主要正文 DOM。
- 若无 MCP,则用 Bash 运行一段 Python/Node 的 Playwright 脚本:`playwright` 启动 chromium,`page.goto(url, wait_until="networkidle")`,再读取 `page.content()` 或 `page.inner_text("article, main, body")`。
- 仅允许作为**同一 URL 的二次尝试**,抓到渲染后的 HTML/正文后按同一套摘要提示词进行摘要。
- 如果 Playwright 仍然失败或正文依旧过短,按失败条目输出,不要再做第三次尝试,也禁止使用搜索引擎或第三方代理。

3. 每个站点最多处理 20 条。抓取失败的条目不中断流程,仍需输出到最终结果中。

**严禁搜索补救**:抓取失败、内容不足或摘要信息量不够时,**禁止**使用 WebSearch、Google、Bing 或任何搜索引擎/其他站点去"补"新闻或"搜"相关报道,也禁止使用 Jina Reader 等第三方代理服务。只能对**当前 feed 中**已出现的 link 再次 WebFetch;若仍失败,按"失败条目"格式如实输出 error,不得伪造内容、不得用其它来源替代、不得扩展抓取范围。违反此规则等同于污染新闻源。

4. 最终输出一个 JSON 数组(不要写入文件),每个元素格式为:
- 成功:{"title": "标题", "url": "链接", "site": "{site_name}", "digest": "摘要", "publish_time": "时间"}
- 失败:{"url": "链接", "site": "{site_name}", "error": "失败原因描述"}
