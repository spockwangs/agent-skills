# 新闻聚合配置

## 新闻源

每行一个站点，格式为 JSON 对象。

| 字段   | 说明                                                     |
|--------|----------------------------------------------------------|
| `url`  | 站点入口地址                                             |
| `type` | 站点类型：`rss`（RSS/Atom Feed）或 `html`（HTML 目录页） |
| `site` | 站点显示名称，用于报告中的来源标注                       |

### 站点列表

```json
{"url": "https://www.dapenti.com/blog/index.asp", "type": "html", "site": "打喷嚏"}
{"url": "https://www.technologyreview.com/topnews.rss", "type": "rss", "site": "MIT科技评论"}
{"url": "https://www.scientificamerican.com/platform/syndication/rss/", "type": "rss", "site": "科学美国人"}
{"url": "https://bloombergnew.buzzing.cc/feed.xml", "type": "rss", "site": "彭博社"}
{"url": "https://news.ycombinator.com/rss", "type": "rss", "site": "Hacker News"}
{"url": "https://apnews.com/world-news", "type": "html", "site": "AP News"}
{"url": "https://lilianweng.github.io/index.xml", "type": "rss", "site": "Lil'Log"}
{"url": "https://simonwillison.net/atom/entries/", "type": "rss", "site": "Simon Willison's Weblog"}
{"url": "https://openai.com/zh-Hans-CN/research/index/", "type": "html", "site": "OpenAI"}
```

### 如何添加新站点

在上方站点列表的代码块中追加一行 JSON 即可，例如：

```json
{"url": "https://example.com/news.rss", "type": "rss", "site": "示例站点"}
{"url": "https://example.com/news/", "type": "html", "site": "示例目录页"}
```

如果用户在调用 SKILL 时传入了自定义 URL 列表，则优先使用用户提供的列表，忽略此文件中的默认配置。

