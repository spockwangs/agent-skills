#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 SMTP 将每日新闻简报（全文）发送到邮箱。默认适配 Gmail（应用专用密码）。

用法:
  EMAIL_TO=you@gmail.com SMTP_APP_PASSWORD='xxxx xxxx xxxx xxxx' \
  python3 send_email.py [--report ~/.cache/daily-news/report.html] [--subject "..."] \
      [--smtp-host smtp.gmail.com] [--smtp-port 587]

参数:
  --report     报告文件路径（默认 ~/.cache/daily-news/report.html；自动识别 HTML / Markdown）
  --subject    邮件主题（默认取报告 <title> 或第一行标题）
  --smtp-host  SMTP 服务器（默认 smtp.gmail.com）
  --smtp-port  SMTP 端口（默认 587）

环境变量:
  EMAIL_TO             收件人邮箱（必填）
  SMTP_APP_PASSWORD    邮箱应用专用密码（必填；仅本次进程使用，不写入任何文件）

行为:
  - 报告为 HTML：正文直接使用报告 HTML，纯文本回退为剥离标签后的文本
  - 报告为 Markdown：正文为 HTML 转换 + 纯文本原文
  邮件为 multipart/alternative，不附带附件。
  所有条目完整呈现，不截断。

退出码:
  0  发送成功
  1  发送失败（SMTP 错误等）
  2  参数/配置错误（缺少邮箱或密码）
"""
import argparse
import os
import re
import smtplib
import sys
import html as html_mod
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

DEFAULT_REPORT = os.path.expanduser("~/.cache/daily-news/report.html")
SENDER_NAME = "WorkBuddy 新闻简报"


def md_inline(text: str) -> str:
    """行内转换：链接 + 加粗 + HTML 转义。"""
    text = html_mod.escape(text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html_mod.escape(m.group(2))}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def md_to_html(md: str) -> str:
    """极简 markdown -> HTML：标题、分隔线、链接、加粗、引用块、段落。"""
    out = []
    for line in md.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):
            out.append(f"<h2>{html_mod.escape(line[2:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html_mod.escape(line[4:])}</h3>")
        elif line.strip() == "---":
            out.append("<hr>")
        elif line.startswith(">"):
            out.append(f"<blockquote>{md_inline(line[1:].strip())}</blockquote>")
        else:
            out.append(f"<p>{md_inline(line)}</p>")
    return "\n".join(out)


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="发送每日新闻简报邮件（全文）")
    parser.add_argument("--report", default=DEFAULT_REPORT, help="报告 markdown 路径")
    parser.add_argument("--subject", default=None, help="邮件主题（默认取报告标题）")
    parser.add_argument("--smtp-host", default="smtp.gmail.com")
    parser.add_argument("--smtp-port", type=int, default=587)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])

    to_addr = os.environ.get("EMAIL_TO", "").strip()
    password = os.environ.get("SMTP_APP_PASSWORD", "").strip().replace(" ", "")
    if not to_addr:
        print("错误: 未设置 EMAIL_TO 环境变量", file=sys.stderr)
        return 2
    if not password:
        print("错误: 未设置 SMTP_APP_PASSWORD 环境变量", file=sys.stderr)
        return 2

    if not os.path.exists(args.report):
        print(f"错误: 报告文件不存在: {args.report}", file=sys.stderr)
        return 2
    with open(args.report, encoding="utf-8") as f:
        raw = f.read()

    is_html = raw.lstrip().startswith("<")
    if is_html:
        # HTML 报告：正文直接用原 HTML，纯文本回退为剥离标签后的内容
        m = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
        subject = args.subject or (html_mod.unescape(m.group(1).strip()) if m else "")
        body_html = raw
        body_plain = re.sub(r"<[^>]+>", "", raw)
        body_plain = html_mod.unescape(body_plain)
        body_plain = re.sub(r"\n{3,}", "\n\n", body_plain).strip()
    else:
        # Markdown 报告：走 md_to_html 转换
        md = raw
        subject = args.subject
        if not subject:
            first_line = md.splitlines()[0] if md else ""
            subject = first_line[2:] if first_line.startswith("# ") else first_line
        body_plain = md
        body_html = (
            '<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
            f'font-size:14px;line-height:1.6;color:#1f2328;">{md_to_html(md)}</div>'
        )

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((str(Header(SENDER_NAME, "utf-8")), to_addr))
    msg["To"] = to_addr
    msg["Subject"] = Header(subject, "utf-8")
    msg.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(args.smtp_host, args.smtp_port, timeout=60) as server:
            server.starttls()
            server.login(to_addr, password)
            server.sendmail(to_addr, [to_addr], msg.as_string())
    except Exception as e:
        print(f"错误: 邮件发送失败: {e}", file=sys.stderr)
        return 1

    print(f"OK: 已发送全文简报至 {to_addr}，主题「{subject}」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
