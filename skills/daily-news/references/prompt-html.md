你正在抓取 HTML 新闻目录页。这是一个研究任务，不需要编写代码文件。

站点名称：{site_name}
目录页 URL：{index_url}

时间过滤：只保留最近 48 小时内发布的新闻。当前时间为 {now_iso}，截止时间为 {cutoff_iso}。
在抓取详情页并提取 publish_time 后，丢弃早于 {cutoff_iso} 的条目，不计入最终结果。
publish_time 为空的条目保留（宁可多抓，后续去重兜底）。

执行步骤：
1. 用 WebFetch 抓取目录页 URL，提示词为：
   "这是一个新闻网站的目录页或首页。请提取所有新闻文章的链接，过滤掉导航链接、广告链接、关于页面等非新闻链接。 对每条输出 JSON 格式：title（标题）、url（完整链接）。 输出一个 JSON 数组，最多 20 条。"

**工具降级**:如果当前环境没有 WebFetch 工具可用(例如调用报错"tool not available"或权限不足),改用 Bash 调用 `curl` 或 `wget` 抓取同一 URL 的原始 HTML,再自行解析提取文章链接。推荐命令:
- `curl -sSL -A "Mozilla/5.0" --max-time 30 "{url}"`
- `wget -qO- --user-agent="Mozilla/5.0" --timeout=30 "{url}"`
curl/wget 仅作为 WebFetch 不可用时的等价替代,不改变站点范围与抓取规则。

**目录页空壳处理**:如果 WebFetch 返回的目录页内容明显是"空壳"(例如:未解析出任何文章链接、或只剩 CSS/骨架屏、或明确提示需启用 JavaScript),改用 Playwright 操作无头浏览器重新抓取同一目录页 URL:

- 优先通过 Playwright MCP 的 `browser_navigate` + `browser_snapshot` 获取渲染后的链接列表;或用 Bash 运行 Playwright 脚本,`page.goto(url, wait_until="networkidle")` 后 `page.content()` 取完整 HTML,再自行解析出文章链接。
- 仅允许作为同一 URL 的二次尝试。若 Playwright 仍抓不到链接列表,视为站点不可用,后续步骤跳过(不要报告失败条目,因为此时还没有具体 link)。禁止使用 Jina Reader 等第三方代理服务。

2. 对获取到的每条链接，用 WebFetch 抓取内容页（若 WebFetch 不可用,同样改用 curl/wget 抓取 HTML 后自行摘要），提示词为：
   "提取这篇新闻文章的标题、正文内容，生成 120–180 字的中文摘要。同时尝试提取发布时间（ISO 8601 格式，如果找不到就返回空字符串）。输出 JSON 格式:title、digest、publish_time。
摘要写作要求：
（1）必须覆盖 5W1H 中在原文出现的要素（Who / What / When / Where / Why / How），至少 3 项；
（2）必须包含至少一个具体数字或专有名词（金额/比例/时间点/人名/公司名/产品名/机构名/地名等），不得全部以泛化表述充数；
（3）禁止使用评价性空话，如'积极''重要''值得关注''引发广泛关注''具有重要意义'等；
（4）禁止出现'据报道''有消息称'等无信息量的套话；
（5）如原文信息不足以填满 120 字，如实写到信息边界为止，不要虚构或注水。"

**详情页空壳处理**:如果上一步 WebFetch 返回的详情页明显是"空壳"(正文文字 < 50 字、只剩 CSS/JS 代码、只有骨架屏/导航/页脚、`<div id="root">` 之类的 SPA 容器、或明确提示需启用 JavaScript),改用 Playwright 操作无头浏览器重新抓取同一条 link:

- 优先通过 Playwright MCP 的 `browser_navigate` + `browser_snapshot` / `browser_evaluate` 取渲染后的正文文本;或用 Bash 运行 Playwright 脚本,`page.goto(url, wait_until="networkidle")` 后 `page.inner_text("article, main, body")` 读取正文。
- 拿到渲染后的正文再按同一套摘要提示词生成摘要。
- 仅允许作为同一 URL 的二次尝试。若 Playwright 仍失败或正文依旧过短,按失败条目输出,不要再做第三次尝试,也禁止使用搜索引擎或 Jina Reader 等第三方代理服务。

3. 每个站点最多抓取 20 条。抓取失败的链接不中断流程,仍需输出到最终结果中。

**严禁搜索补救**:抓取失败、目录页无法解析或内容不足时,**禁止**使用 WebSearch、Google、Bing 或任何搜索引擎去"补"新闻或"搜"相关报道;也禁止使用 Jina Reader 等第三方代理服务或跳到该站点以外的 URL 抓取。只能对**当前目录页中已列出**的 link 再次 WebFetch;若仍失败,按"失败条目"格式如实输出 error,不得伪造内容、不得用其它来源替代、不得扩展抓取范围。违反此规则等同于污染新闻源。

4. 最终输出一个 JSON 数组(不要写入文件),每个元素格式为:
- 成功:{"title": "标题", "url": "链接", "site": "{site_name}", "digest": "摘要", "publish_time": "时间"}
- 失败:{"url": "链接", "site": "{site_name}", "error": "失败原因描述"}
