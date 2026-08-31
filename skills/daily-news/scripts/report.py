#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取打分后的新闻 JSONL，按 score 降序生成报告并输出到 stdout。
默认输出 HTML 格式，可用 --format markdown 输出 Markdown。
可选读取抓取错误文件；可选嵌入市场情绪快照（market_snapshot.py 输出）置于报告最开头。

用法:
  python3 report.py <scored_file> [--errors <errors_file>] [--min-score <N>] \
      [--snapshot <snapshot.html>] [--format html|markdown]

参数:
  scored_file    打分后的 JSONL 文件，每行格式：
    {"title": "...", "content": "...", "score": N, "one_liner": "...", "sources": [{"url": "...", "source": "..."}]}
  errors_file    抓取失败的 JSONL 文件（可选），每行格式：
    {"url": "...", "source": "...", "error": "..."}
  min_score      仅推送 score >= min_score 的新闻，默认 5
  snapshot       市场情绪快照 HTML 文件（可选，仅 HTML 格式生效），置于报告最开头
  format         输出格式：html（默认）或 markdown

行为:
  1. 过滤掉 score < min_score 的新闻
  2. 按 score 降序排列剩余新闻
  3. 生成报告（HTML 或 Markdown，每条含标题、分数、一句话摘要、来源链接）
  4. 如果有 snapshot 文件，将其 HTML 区块嵌入报告标题之后、新闻之前
  5. 如果有错误文件且非空，在报告末尾附加失败条目列表
  6. 打印完整报告到 stdout（由调用方负责推送）

退出码:
  0  正常完成
  1  无新闻可发送
  2  参数错误
"""

import html as html_mod
import json
import os
import sys
from datetime import date

# ---- HTML 内联样式（邮件 / 浏览器均可阅读） ----
S_BODY = ("font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,"
          "'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;"
          "font-size:14px;line-height:1.6;color:#1f2328;max-width:720px;margin:0 auto;padding:16px;")
S_H1 = "font-size:22px;line-height:1.4;margin:0 0 4px;"
S_META = "color:#57606a;font-size:13px;margin:0 0 20px;"
S_H3 = "font-size:16px;margin:24px 0 6px;"
S_SCORE = "color:#57606a;font-size:13px;font-weight:normal;"
S_P = "margin:0 0 6px;"
S_BQ = ("margin:4px 0 0;padding:6px 12px;border-left:3px solid #d0d7de;"
        "color:#57606a;background:#f6f8fa;border-radius:0 4px 4px 0;")
S_HR = "border:none;border-top:1px solid #d0d7de;margin:20px 0;"
S_H2 = "font-size:18px;margin:28px 0 8px;"
S_OL = "margin:8px 0;padding-left:22px;color:#cf222e;font-size:13px;"
S_A = "color:#0969da;text-decoration:none;"


def load_jsonl(filepath: str) -> list:
    """读取 JSONL 文件，跳过空行和格式错误的行。"""
    items = []
    if not os.path.exists(filepath):
        return items
    with open(filepath, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"警告: 第 {lineno} 行 JSON 解析失败，已跳过", file=sys.stderr)
    return items


def score_emoji(score: int) -> str:
    """根据分数返回对应的 emoji 标记。"""
    if score >= 8:
        return "🟢"
    if score >= 5:
        return "🟡"
    return "🔴"


# ---------- Markdown 路径 ----------

def format_sources_md(sources: list) -> str:
    """将 sources 数组格式化为 Markdown 链接，多个用分隔符连接。"""
    parts = []
    for src in sources:
        source = src.get("source", "来源")
        url = src.get("url", "")
        if url:
            parts.append(f"[{source}]({url})")
        else:
            parts.append(source)
    return " | ".join(parts)


def build_news_items_md(items: list) -> str:
    """按 score 降序生成新闻条目的 Markdown 片段。"""
    sorted_items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)

    blocks = []
    for item in sorted_items:
        title = item.get("title", "无标题")
        score = item.get("score", 0)
        one_liner = item.get("one_liner", "")
        sources_md = format_sources_md(item.get("sources", []))
        emoji = score_emoji(score)

        block = f"### {emoji} {title} ({score}/10)\n\n{one_liner}\n\n> 来源: {sources_md}"
        blocks.append(block)
    return "\n\n---\n\n".join(blocks)


def build_errors_md(errors: list) -> str:
    """生成抓取失败条目的 Markdown 片段。"""
    lines = [f"## ⚠️ 抓取失败（{len(errors)}条）\n"]
    for i, item in enumerate(errors, 1):
        source = item.get("source", "未知站点")
        url = item.get("url", "未知URL")
        error = item.get("error", "未知错误")
        lines.append(f"{i}. **[{source}]** {url} — {error}")
    return "\n".join(lines)


def build_markdown(header: str, news_md: str, errors_md: str) -> str:
    """组装完整的 Markdown 文档。"""
    parts = [f"# {header}"]
    if news_md:
        parts.append(news_md)
    if errors_md:
        parts.append(errors_md)
    return "\n\n".join(parts) + "\n"


# ---------- HTML 路径 ----------

def format_sources_html(sources: list) -> str:
    """将 sources 数组格式化为 HTML 链接，多个用分隔符连接。"""
    parts = []
    for src in sources:
        source = html_mod.escape(src.get("source", "来源"))
        url = src.get("url", "")
        if url:
            parts.append(f'<a href="{html_mod.escape(url)}" style="{S_A}">{source}</a>')
        else:
            parts.append(source)
    return ' <span style="color:#d0d7de;">|</span> '.join(parts)


def build_news_items_html(items: list) -> str:
    """按 score 降序生成新闻条目的 HTML 片段。"""
    sorted_items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)

    blocks = []
    for item in sorted_items:
        title = html_mod.escape(item.get("title", "无标题"))
        score = item.get("score", 0)
        one_liner = html_mod.escape(item.get("one_liner", ""))
        sources_html = format_sources_html(item.get("sources", []))
        emoji = score_emoji(score)

        block = (
            f'<h3 style="{S_H3}">{emoji} {title} '
            f'<span style="{S_SCORE}">({score}/10)</span></h3>\n'
            f'<p style="{S_P}">{one_liner}</p>\n'
            f'<blockquote style="{S_BQ}">来源: {sources_html}</blockquote>'
        )
        blocks.append(block)
    return "\n\n<hr style=\"{0}\">\n\n".format(S_HR).join(blocks)


def build_errors_html(errors: list) -> str:
    """生成抓取失败条目的 HTML 片段。"""
    lines = [f'<h2 style="{S_H2}">⚠️ 抓取失败（{len(errors)}条）</h2>', f'<ol style="{S_OL}">']
    for item in errors:
        source = html_mod.escape(item.get("source", "未知站点"))
        url = item.get("url", "")
        error = html_mod.escape(item.get("error", "未知错误"))
        if url:
            lines.append(
                f'<li><b>[{source}]</b> <a href="{html_mod.escape(url)}" style="{S_A}">'
                f'{html_mod.escape(url)}</a> — {error}</li>'
            )
        else:
            lines.append(f"<li><b>[{source}]</b> {url} — {error}</li>")
    lines.append("</ol>")
    return "\n".join(lines)


def build_html(title: str, meta: str, snapshot_html: str, news_html: str, errors_html: str) -> str:
    """组装完整的 HTML 文档（可直接作为邮件正文或浏览器查看）。"""
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        '<head><meta charset="utf-8">',
        f"<title>{html_mod.escape(title)}</title>",
        "</head>",
        f'<body style="{S_BODY}">',
        f'<h1 style="{S_H1}">{html_mod.escape(title)}</h1>',
        f'<p style="{S_META}">{html_mod.escape(meta)}</p>',
    ]
    if snapshot_html:
        parts.append(snapshot_html)
    if news_html:
        parts.append(news_html)
    if errors_html:
        parts.append(errors_html)
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


# ---------- 主流程 ----------

def parse_args(argv: list) -> tuple:
    """解析命令行参数，返回 (scored_file, errors_file, min_score, fmt, snapshot_file)。"""
    if len(argv) < 2:
        print("用法: python3 report.py <scored_file> [--errors <errors_file>] [--min-score <N>] [--snapshot <file>] [--format html|markdown]",
              file=sys.stderr)
        sys.exit(2)

    scored_file = argv[1]
    errors_file = None
    min_score = 5
    fmt = "html"
    snapshot_file = None

    i = 2
    while i < len(argv):
        if argv[i] == "--errors" and i + 1 < len(argv):
            errors_file = argv[i + 1]
            i += 2
        elif argv[i] == "--min-score" and i + 1 < len(argv):
            try:
                min_score = int(argv[i + 1])
            except ValueError:
                print(f"--min-score 需要整数: {argv[i + 1]}", file=sys.stderr)
                sys.exit(2)
            i += 2
        elif argv[i] == "--snapshot" and i + 1 < len(argv):
            snapshot_file = argv[i + 1]
            i += 2
        elif argv[i] == "--format" and i + 1 < len(argv):
            fmt = argv[i + 1].lower()
            if fmt not in ("html", "markdown"):
                print(f"--format 仅支持 html 或 markdown: {argv[i + 1]}", file=sys.stderr)
                sys.exit(2)
            i += 2
        else:
            print(f"未知参数: {argv[i]}", file=sys.stderr)
            sys.exit(2)

    return scored_file, errors_file, min_score, fmt, snapshot_file


def main():
    scored_file, errors_file, min_score, fmt, snapshot_file = parse_args(sys.argv)

    items = load_jsonl(scored_file)
    errors = load_jsonl(errors_file) if errors_file else []
    snapshot_html = ""
    if snapshot_file and os.path.exists(snapshot_file):
        with open(snapshot_file, encoding="utf-8") as f:
            snapshot_html = f.read().strip()

    total = len(items)
    items = [it for it in items if it.get("score", 0) >= min_score]

    if not items and not errors:
        print("无新闻可发送")
        sys.exit(1)

    today = date.today().isoformat()
    title = f"📰 每日新闻摘要 — {today}"
    meta = f"共 {len(items)} 条，筛除 {total - len(items)} 条低于 {min_score} 分"

    if fmt == "html":
        news_html = build_news_items_html(items) if items else ""
        errors_html = build_errors_html(errors) if errors else ""
        print(build_html(title, meta, snapshot_html, news_html, errors_html))
    else:
        header = f"{title}（{meta}）"
        news_md = build_news_items_md(items) if items else ""
        errors_md = build_errors_md(errors) if errors else ""
        print(build_markdown(header, news_md, errors_md))


if __name__ == "__main__":
    main()
