#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取港股恐贪指数并输出报告（默认 Markdown，可输出 HTML）。

数据来源：守猪逮兔估值模型 (https://fe.szdt.tech/invest/?futusource=nnq_im#/etf_hk)
API: https://szdt.tech/api/invest/stock_emotion_hk?etf_type=8

用法:
  python3 stock_emotion.py [--format markdown|html]

输出:
  markdown/html 格式的恐贪指数报告（stdout）

退出码:
  0  成功
  1  API 请求失败
"""

import argparse
import hashlib
import hmac
import html as html_mod
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------- 配置 ----------

API_BASE = "https://szdt.tech/api"
ENDPOINT = "/invest/stock_emotion_hk?etf_type=8"
HMAC_KEY = "X9XuQ89fjX4nq4FbdDM4LjVMYvDTsVVh"
SOURCE_URL = "https://fe.szdt.tech/invest/?futusource=nnq_im#/etf_hk"

# 目标股票（按展示顺序）
TARGET_STOCKS = [
    "HK.00700",  # 腾讯
    "HK.03690",  # 美团
    "HK.09618",  # 京东
    "HK.09988",  # 阿里巴巴
]

# 恐贪指数情绪分档
EMOTION_LEVELS = [
    (-100, -60, "极度恐惧"),
    (-60,  -20, "恐惧"),
    (-20,   20, "中性"),
    (20,    60, "贪婪"),
    (60,   100, "极度贪婪"),
]


def score_to_emotion(score: int) -> str:
    """将恐贪指数映射为情绪标签。"""
    for low, high, label in EMOTION_LEVELS:
        if low <= score <= high:
            return label
    if score < -100:
        return "极度恐惧"
    return "极度贪婪"


def build_signature(timestamp: str) -> str:
    """构造 HMAC-SHA256 签名。"""
    secret = HMAC_KEY + timestamp
    sign_str = f"GET_{ENDPOINT}__{secret}"
    return hmac.new(
        secret.encode(), sign_str.encode(), hashlib.sha256
    ).hexdigest()


def fetch_stock_emotions() -> list[dict]:
    """调用 API 获取港股个股恐贪数据，返回原始列表。"""
    timestamp = datetime.now(timezone.utc).isoformat()
    signature = build_signature(timestamp)

    url = f"{API_BASE}{ENDPOINT}"
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


def filter_targets(stocks: list[dict]) -> list[dict]:
    """从完整列表中按 TARGET_STOCKS 顺序过滤目标股票。"""
    stock_map = {s["code"]: s for s in stocks}
    result = []
    for code in TARGET_STOCKS:
        if code in stock_map:
            result.append(stock_map[code])
    return result


def format_code(code: str) -> str:
    """HK.00700 -> 00700"""
    return code.replace("HK.", "")


def build_markdown(targets: list[dict]) -> str:
    """生成 Markdown 格式报告。"""
    lines = ["## 港股恐贪指数", ""]
    lines.append("| 股票 | 代码 | 市价 | 恐贪指数 | 情绪 |")
    lines.append("|------|------|------|----------|------|")

    updated_at = ""
    for stock in targets:
        name = stock.get("name", "")
        code = format_code(stock["code"])
        emotion = stock.get("emotion") or {}
        score = emotion.get("score", "-")
        price = emotion.get("price", "-")
        if emotion.get("updated_at"):
            updated_at = emotion["updated_at"]

        if isinstance(score, (int, float)):
            emotion_label = score_to_emotion(int(score))
        else:
            emotion_label = "无数据"

        lines.append(f"| {name} | {code} | {price} | {score} | {emotion_label} |")

    lines.append("")
    lines.append(
        "> ≤-60 极度恐惧 | -60~-20 恐惧 | -20~20 中性 | 20~60 贪婪 | ≥60 极度贪婪"
    )
    source_line = f"> 数据来源：守猪逮兔估值模型({SOURCE_URL})"
    if updated_at:
        source_line += f" | 更新时间：{updated_at}"
    lines.append(source_line)

    return "\n".join(lines)


def emotion_color(score):
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


def build_html(targets: list[dict]) -> str:
    """生成 HTML 格式报告（适合作为邮件正文）。"""
    rows = []
    updated_at = ""
    for stock in targets:
        name = stock.get("name", "")
        code = format_code(stock["code"])
        emotion = stock.get("emotion") or {}
        score = emotion.get("score", "-")
        price = emotion.get("price", "-")
        if emotion.get("updated_at"):
            updated_at = emotion["updated_at"]

        if isinstance(score, (int, float)):
            emotion_label = score_to_emotion(int(score))
        else:
            emotion_label = "无数据"

        color = emotion_color(score)
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
        f"数据来源：<a href=\"{html_mod.escape(SOURCE_URL)}\" style=\"color:#2563eb;\">守猪逮兔估值模型</a>"
        + (f" | {updated_line}" if updated_line else "")
        + "</p></div>"
    )


def main():
    parser = argparse.ArgumentParser(description="港股恐贪指数报告")
    parser.add_argument(
        "--format", choices=["markdown", "html"], default="markdown",
        help="输出格式（默认 markdown）",
    )
    args = parser.parse_args()

    try:
        stocks = fetch_stock_emotions()
    except Exception as e:
        print(f"港股恐贪指数获取失败: {e}", file=sys.stderr)
        sys.exit(1)

    targets = filter_targets(stocks)
    if not targets:
        print("未找到目标股票数据", file=sys.stderr)
        sys.exit(1)

    if args.format == "html":
        print(build_html(targets))
    else:
        print(build_markdown(targets))


if __name__ == "__main__":
    main()
