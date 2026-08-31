#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成市场情绪快照（港股恐贪指数 + 标普500ETF 溢价率），输出 HTML 区块到 stdout。

用法:
  python3 market_snapshot.py [--out <file>] [--no-hk] [--no-etf]

数据源:
  1. 港股恐贪指数: 守猪逮兔估值模型 API（https://fe.szdt.tech/invest/?futusource=nnq_im#/etf_hk），
     覆盖腾讯/美团/京东/阿里（本脚本内置 API 签名与请求逻辑，不依赖其他技能）
  2. 标普500ETF (513500) 溢价率: 腾讯行情接口(现价) + 东方财富基金净值接口(单位净值)

参数:
  --out     同时写入指定文件（默认只输出 stdout）
  --no-hk   跳过港股恐贪指数
  --no-etf  跳过标普500ETF 溢价率

退出码:
  0  成功（至少一个数据源成功）
  1  所有数据源均失败
"""

import argparse
import hashlib
import hmac
import html as html_mod
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

SNAPSHOT_TITLE = "📊 市场情绪快照"
SNAPSHOT_H2 = ("font-size:18px;margin:28px 0 8px;border-top:1px solid #d0d7de;"
               "padding-top:20px;")
S_BLOCK_TITLE = "font-size:15px;margin:0 0 8px;color:#374151;"
S_MUTED = "font-size:12px;color:#6b7280;"
S_NOTE = ("font-size:12px;color:#6b7280;background:#f6f8fa;border-radius:4px;"
          "padding:8px 10px;margin:8px 0 0;")

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
HK_HMAC_KEY = "X9XuQ89fjX4nq4FbdDM4LjVMYvDTsVVh"
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
    secret = HK_HMAC_KEY + timestamp
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


# ---------- 主流程 ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="市场情绪快照")
    parser.add_argument("--out", help="同时写入该文件")
    parser.add_argument("--no-hk", action="store_true", help="跳过港股恐贪指数")
    parser.add_argument("--no-etf", action="store_true", help="跳过标普500ETF溢价率")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = []
    ok = False

    # 港股恐贪指数
    if not args.no_hk:
        hk_html = fetch_hk_emotion_html()
        if hk_html:
            parts.append(hk_html)
            ok = True
        else:
            parts.append(
                '<p style="font-size:13px;color:#6b7280;">'
                "📈 港股恐贪指数：数据暂不可用（守猪逮兔 API 异常）</p>"
            )

    # 标普500ETF 溢价率
    if not args.no_etf:
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
        print("市场快照生成失败：所有数据源不可用", file=sys.stderr)
        return 1

    snapshot = (
        f'<h2 style="{SNAPSHOT_H2}">📊 市场情绪快照'
        f'<span style="font-size:12px;color:#6b7280;font-weight:400;">（{now}）</span></h2>'
        + "\n".join(parts)
    )
    print(snapshot)

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(snapshot + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
