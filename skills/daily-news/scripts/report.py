#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取打分后的新闻 JSONL，按 score 降序生成报告并输出到 stdout。
默认输出 HTML 格式，可用 --format markdown 输出 Markdown。
可选读取抓取错误文件；默认内置生成市场情绪快照（港股恐贪指数 + 标普500ETF 溢价率）置于报告最开头。

用法:
  python3 report.py <scored_file> [--errors <errors_file>] [--min-score <N>] \
      [--no-snapshot] [--no-hk] [--no-etf] [--format html|markdown]

参数:
  scored_file    打分后的 JSONL 文件，每行格式：
    {"title": "...", "content": "...", "score": N, "one_liner": "...", "sources": [{"url": "...", "source": "..."}]}
  errors_file    抓取失败的 JSONL 文件（可选），每行格式：
    {"url": "...", "source": "...", "error": "..."}
  min_score      仅推送 score >= min_score 的新闻，默认 5
  no_snapshot    跳过市场情绪快照（默认生成，仅 HTML 格式生效）
  no_hk          快照中跳过港股恐贪指数
  no_etf         快照中跳过标普500ETF 溢价率
  format         输出格式：html（默认）或 markdown

行为:
  1. 过滤掉 score < min_score 的新闻
  2. 按 score 降序排列剩余新闻
  3. 生成市场情绪快照（默认开启），嵌入报告标题之后、新闻之前
  4. 生成报告（HTML 或 Markdown，每条含标题、分数、一句话摘要、来源链接）
  5. 如果有错误文件且非空，在报告末尾附加失败条目列表
  6. 打印完整报告到 stdout（由调用方负责推送）

退出码:
  0  正常完成
  1  无新闻可发送
  2  参数错误
"""

import hashlib
import hmac
import html as html_mod
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone

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

# ---- 市场情绪快照（港股恐贪指数 + 标普500ETF 溢价率）----
SNAPSHOT_TITLE = "📊 市场情绪快照"
SNAPSHOT_H2 = ("font-size:18px;margin:28px 0 8px;border-top:1px solid #d0d7de;"
               "padding-top:20px;")
S_BLOCK_TITLE = "font-size:15px;margin:0 0 8px;color:#374151;"
S_MUTED = "font-size:12px;color:#6b7280;"

TENCENT_QUOTE_URL = "http://qt.gtimg.cn/q=sh513500"
EM_FUND_NAV_URL = (
    "https://api.fund.eastmoney.com/f10/lsjz?fundCode=513500&pageIndex=1&pageSize=3"
)


def _get(url: str, headers=None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


# ---------- 港股恐贪指数（守猪逮兔估值模型 API）----------

HK_API_BASE = "https://szdt.tech/api"
HK_ENDPOINT = "/invest/stock_emotion_hk?etf_type=8"
HK_API_SALT = "X9XuQ89fjX4nq4FbdDM4LjVMYvDTsVVh"
HK_SOURCE_URL = "https://fe.szdt.tech/invest/?futusource=nnq_im#/etf_hk"

# 目标股票（按展示顺序）
HK_TARGET_STOCKS = [
    "HK.00700",  # 腾讯
    "HK.03690",  # 美团
    "HK.09618",  # 京东
    "HK.09988",  # 阿里巴巴
]

# 恐贪指数情绪分档
HK_EMOTION_LEVELS = [
    (-100, -60, "极度恐惧"),
    (-60,  -20, "恐惧"),
    (-20,   20, "中性"),
    (20,    60, "贪婪"),
    (60,   100, "极度贪婪"),
]


def hk_score_to_emotion(score: int) -> str:
    """将恐贪指数映射为情绪标签。"""
    for low, high, label in HK_EMOTION_LEVELS:
        if low <= score <= high:
            return label
    if score < -100:
        return "极度恐惧"
    return "极度贪婪"


def hk_build_signature(timestamp: str) -> str:
    """构造 HMAC-SHA256 签名。"""
    secret = HK_API_SALT + timestamp
    sign_str = f"GET_{HK_ENDPOINT}__{secret}"
    return hmac.new(
        secret.encode(), sign_str.encode(), hashlib.sha256
    ).hexdigest()


def hk_fetch_stock_emotions() -> list:
    """调用 API 获取港股个股恐贪数据，返回原始列表。"""
    timestamp = datetime.now(timezone.utc).isoformat()
    signature = hk_build_signature(timestamp)

    url = f"{HK_API_BASE}{HK_ENDPOINT}"
    req = urllib.request.Request(url)
    req.add_header("X-Timestamp", timestamp)
    req.add_header("X-Signature", signature)
    req.add_header("X-Auth", "")
    req.add_header("User-Agent", "Mozilla/5.0")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    if data.get("status") != 1:
        raise RuntimeError(f"API 返回异常: {data.get('msg', 'unknown')}")

    return data["data"]


def hk_filter_targets(stocks: list) -> list:
    """从完整列表中按 HK_TARGET_STOCKS 顺序过滤目标股票。"""
    stock_map = {s["code"]: s for s in stocks}
    result = []
    for code in HK_TARGET_STOCKS:
        if code in stock_map:
            result.append(stock_map[code])
    return result


def hk_format_code(code: str) -> str:
    """HK.00700 -> 00700"""
    return code.replace("HK.", "")


def hk_emotion_color(score):
    """按恐贪指数返回情绪标签颜色（恐惧系绿/蓝，中性灰，贪婪系橙/红）。"""
    if not isinstance(score, (int, float)):
        return "#6b7280"
    if score <= -60:
        return "#0f766e"
    if score <= -20:
        return "#16a34a"
    if score <= 20:
        return "#6b7280"
    if score <= 60:
        return "#ea580c"
    return "#dc2626"


def hk_build_html(targets: list) -> str:
    """生成港股恐贪指数 HTML 区块（与 stock-emotion 技能输出一致）。"""
    rows = []
    updated_at = ""
    for stock in targets:
        name = stock.get("name", "")
        code = hk_format_code(stock["code"])
        emotion = stock.get("emotion") or {}
        score = emotion.get("score", "-")
        price = emotion.get("price", "-")
        if emotion.get("updated_at"):
            updated_at = emotion["updated_at"]

        if isinstance(score, (int, float)):
            emotion_label = hk_score_to_emotion(int(score))
        else:
            emotion_label = "无数据"

        color = hk_emotion_color(score)
        rows.append(
            "<tr>"
            f"<td style=\"padding:10px 16px;border-bottom:1px solid #e5e7eb;font-weight:600;\">{html_mod.escape(str(name))}</td>"
            f"<td style=\"padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#6b7280;\">{html_mod.escape(code)}</td>"
            f"<td style=\"padding:10px 16px;border-bottom:1px solid #e5e7eb;\">{html_mod.escape(str(price))}</td>"
            f"<td style=\"padding:10px 16px;border-bottom:1px solid #e5e7eb;text-align:center;font-weight:700;\">{html_mod.escape(str(score))}</td>"
            f"<td style=\"padding:10px 16px;border-bottom:1px solid #e5e7eb;text-align:center;\">"
            f"<span style=\"display:inline-block;padding:3px 12px;border-radius:9999px;background:{color}1a;color:{color};font-weight:600;\">{html_mod.escape(emotion_label)}</span>"
            "</td></tr>"
        )

    date_str = datetime.now().strftime("%Y-%m-%d")
    updated_line = f"更新时间：{html_mod.escape(updated_at)}" if updated_at else ""
    return (
        "<div style=\"font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "font-size:14px;line-height:1.6;color:#1f2328;max-width:640px;\">"
        f"<h2 style=\"font-size:20px;margin:0 0 16px;\">📈 港股恐贪指数 <span style=\"font-size:13px;color:#6b7280;font-weight:400;\">（{date_str}）</span></h2>"
        "<table style=\"border-collapse:collapse;width:100%;background:#ffffff;\">"
        "<thead><tr style=\"background:#f9fafb;color:#374151;\">"
        "<th style=\"padding:10px 16px;text-align:left;border-bottom:1px solid #e5e7eb;\">股票</th>"
        "<th style=\"padding:10px 16px;text-align:left;border-bottom:1px solid #e5e7eb;\">代码</th>"
        "<th style=\"padding:10px 16px;text-align:left;border-bottom:1px solid #e5e7eb;\">市价</th>"
        "<th style=\"padding:10px 16px;text-align:center;border-bottom:1px solid #e5e7eb;\">恐贪指数</th>"
        "<th style=\"padding:10px 16px;text-align:center;border-bottom:1px solid #e5e7eb;\">情绪</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<p style=\"margin:12px 0 4px;font-size:12px;color:#6b7280;\">"
        "≤-60 极度恐惧 | -60~-20 恐惧 | -20~20 中性 | 20~60 贪婪 | ≥60 极度贪婪</p>"
        "<p style=\"margin:4px 0;font-size:12px;color:#6b7280;\">"
        f"数据来源：<a href=\"{html_mod.escape(HK_SOURCE_URL)}\" style=\"color:#2563eb;\">守猪逮兔估值模型</a>"
        + (f" | {updated_line}" if updated_line else "")
        + "</p></div>"
    )


def fetch_hk_emotion_html() -> str:
    """直接调用内置 API 逻辑获取港股恐贪指数 HTML 区块；失败返回空串。"""
    try:
        stocks = hk_fetch_stock_emotions()
        targets = hk_filter_targets(stocks)
        if not targets:
            return ""
        return hk_build_html(targets)
    except Exception:
        return ""


# ---------- 标普500ETF 溢价率 ----------

def fetch_tencent_quote() -> dict:
    """获取腾讯行情，返回 {name, code, price, change_pct, time}。"""
    raw = _get(TENCENT_QUOTE_URL).decode("gbk", errors="replace")
    body = raw.split('"')[1]
    f = body.split("~")
    if len(f) < 33:
        raise RuntimeError("腾讯行情字段不完整")
    return {
        "name": f[1],
        "code": f[2],
        "price": float(f[3]),
        "change_pct": float(f[32]),
        "time": f[30],
    }


def fetch_fund_nav() -> dict:
    """获取东方财富基金单位净值，返回 {nav, nav_date}。"""
    headers = {"Referer": "https://fundf10.eastmoney.com/", "User-Agent": "Mozilla/5.0"}
    data = json.loads(_get(EM_FUND_NAV_URL, headers).decode())
    lst = (data.get("Data") or {}).get("LSJZList") or []
    if not lst:
        raise RuntimeError("基金净值接口返回空")
    first = lst[0]
    return {"nav": float(first["DWJZ"]), "nav_date": first["FSRQ"]}


def premium_color(premium: float) -> str:
    """溢价率配色：≥5% 红 | 3~5% 橙 | 1~3% 蓝 | -1~1% 灰 | <-1% 绿。"""
    if premium >= 5:
        return "#dc2626"
    if premium >= 3:
        return "#ea580c"
    if premium >= 1:
        return "#2563eb"
    if premium <= -1:
        return "#16a34a"
    return "#6b7280"


def build_etf_premium_html(quote: dict, nav: dict) -> str:
    """生成标普500ETF 溢价率 HTML 卡片。"""
    price = quote["price"]
    premium = (price / nav["nav"] - 1) * 100
    color = premium_color(premium)

    t = quote["time"]
    quote_time = (f"{t[0:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}" if len(t) >= 12 else t)

    badge = (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:9999px;'
        f'background:{color}1a;color:{color};font-weight:700;font-size:15px;">'
        f'{premium:+.2f}%</span>'
    )
    warn = ""
    if premium >= 5:
        warn = ("<p style=\"margin:6px 0 0;font-size:12px;color:#cf222e;\">"
                "⚠️ 溢价处于历史高位（QDII 跨境 ETF 因外汇额度限制申购），"
                "注意溢价回落风险。</p>")

    return (
        '<div style="margin:0 0 16px;">'
        f'<h3 style="{S_BLOCK_TITLE}">🇺🇸 标普500ETF 博时（513500）溢价率</h3>'
        "<table style=\"border-collapse:collapse;font-size:13px;min-width:420px;\">"
        "<tr><td style=\"padding:4px 12px 4px 0;color:#57606a;\">场内现价</td>"
        f"<td style=\"padding:4px 0;font-weight:600;\">{price:.3f} 元"
        f"<span style=\"color:#57606a;font-weight:400;\">（{quote['change_pct']:+.2f}%）</span></td></tr>"
        "<tr><td style=\"padding:4px 12px 4px 0;color:#57606a;\">单位净值</td>"
        f"<td style=\"padding:4px 0;\">{nav['nav']:.4f} 元"
        f"<span style=\"color:#6b7280;font-size:12px;\">（{nav['nav_date']}）</span></td></tr>"
        "<tr><td style=\"padding:4px 12px 4px 0;color:#57606a;\">溢价率</td>"
        f"<td style=\"padding:4px 0;\">{badge}</td></tr>"
        "</table>"
        f'<p style="{S_MUTED}">行情时间：{quote_time}（A股收盘）｜'
        '溢价率 = (现价 − 单位净值) ÷ 单位净值</p>'
        f"{warn}</div>"
    )


def build_market_snapshot(no_hk: bool = False, no_etf: bool = False) -> str:
    """生成市场情绪快照 HTML 区块；所有数据源失败时返回空串。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = []
    ok = False

    if not no_hk:
        hk_html = fetch_hk_emotion_html()
        if hk_html:
            parts.append(hk_html)
            ok = True
        else:
            parts.append(
                '<p style="font-size:13px;color:#6b7280;">'
                "📈 港股恐贪指数：数据暂不可用（守猪逮兔 API 异常）</p>"
            )

    if not no_etf:
        try:
            quote = fetch_tencent_quote()
            nav = fetch_fund_nav()
            parts.append(build_etf_premium_html(quote, nav))
            ok = True
        except Exception as e:
            parts.append(
                f'<p style="font-size:13px;color:#6b7280;">'
                f"🇺🇸 标普500ETF 溢价率：数据暂不可用（{html_mod.escape(str(e))}）</p>"
            )

    if not ok:
        return ""

    return (
        f'<h2 style="{SNAPSHOT_H2}">{SNAPSHOT_TITLE}'
        f'<span style="font-size:12px;color:#6b7280;font-weight:400;">（{now}）</span></h2>'
        + "\n".join(parts)
    )


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
    """解析命令行参数，返回 (scored_file, errors_file, min_score, fmt, no_snapshot, no_hk, no_etf)。"""
    if len(argv) < 2:
        print("用法: python3 report.py <scored_file> [--errors <errors_file>] [--min-score <N>] [--no-snapshot] [--no-hk] [--no-etf] [--format html|markdown]",
              file=sys.stderr)
        sys.exit(2)

    scored_file = argv[1]
    errors_file = None
    min_score = 5
    fmt = "html"
    no_snapshot = False
    no_hk = False
    no_etf = False

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
        elif argv[i] == "--no-snapshot":
            no_snapshot = True
            i += 1
        elif argv[i] == "--no-hk":
            no_hk = True
            i += 1
        elif argv[i] == "--no-etf":
            no_etf = True
            i += 1
        elif argv[i] == "--format" and i + 1 < len(argv):
            fmt = argv[i + 1].lower()
            if fmt not in ("html", "markdown"):
                print(f"--format 仅支持 html 或 markdown: {argv[i + 1]}", file=sys.stderr)
                sys.exit(2)
            i += 2
        else:
            print(f"未知参数: {argv[i]}", file=sys.stderr)
            sys.exit(2)

    return scored_file, errors_file, min_score, fmt, no_snapshot, no_hk, no_etf


def main():
    scored_file, errors_file, min_score, fmt, no_snapshot, no_hk, no_etf = parse_args(sys.argv)

    items = load_jsonl(scored_file)
    errors = load_jsonl(errors_file) if errors_file else []
    snapshot_html = ""
    if fmt == "html" and not no_snapshot:
        snapshot_html = build_market_snapshot(no_hk=no_hk, no_etf=no_etf)

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
