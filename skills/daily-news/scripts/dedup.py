#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻去重脚本：根据 URL 精确去重。

用法:
  python3 dedup.py <current_file>

参数:
  current_file   本轮抓取的 JSONL 文件（去重后原地覆盖）

历史文件自动按近 7 天日期定位：与 current_file 同目录下的 history/YYYY-MM-DD.jsonl，
覆盖今天及往前 6 天共 7 个日期，存在的文件都会被加载合并为历史集合。

去重规则:
  1. current 内部按 URL 去重（保留首次出现的）
  2. 与近 7 天 history 按 URL 精确去重（移除已推送过的）

退出码:
  0  正常完成，去重后仍有记录
  1  去重后无记录（全是重复新闻）
  2  参数错误或文件读取失败
"""

import json
import os
import sys
from datetime import date, timedelta

# 历史去重窗口：今天 + 往前 6 天 = 7 天
HISTORY_WINDOW_DAYS = 7


def load_jsonl(filepath: str) -> list:
    """读取 JSONL 文件，返回 JSON 对象列表。跳过空行和格式错误的行。"""
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
                print(f"警告: {filepath} 第 {lineno} 行 JSON 解析失败，已跳过", file=sys.stderr)
    return items


def save_jsonl(filepath: str, items: list) -> None:
    """将 JSON 对象列表写入 JSONL 文件（覆盖）。"""
    with open(filepath, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def dedup(current_items: list, history_items: list) -> list:
    """执行 URL 精确去重，返回去重后的列表。"""
    # 1. current 内部按 URL 去重
    seen_urls = set()
    url_deduped = []
    for item in current_items:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        url_deduped.append(item)

    # 2. 与 history 按 URL 精确去重
    history_urls = {item.get("url", "") for item in history_items}
    final = [item for item in url_deduped if item.get("url", "") not in history_urls]

    return final


def main():
    if len(sys.argv) < 2:
        print("用法: python3 dedup.py <current_file>", file=sys.stderr)
        sys.exit(2)

    current_file = sys.argv[1]

    # 根据 current_file 所在目录定位近 7 天的历史文件
    cache_dir = os.path.dirname(os.path.abspath(current_file))
    history_dir = os.path.join(cache_dir, "history")
    today = date.today()
    history_files = [
        os.path.join(history_dir, f"{(today - timedelta(days=i)).isoformat()}.jsonl")
        for i in range(HISTORY_WINDOW_DAYS)
    ]

    # 读取文件
    current_items = load_jsonl(current_file)
    if not current_items:
        print("current 文件为空，无需去重")
        sys.exit(1)

    # 合并近 7 天的历史记录
    history_items = []
    loaded_days = 0
    for hf in history_files:
        if os.path.exists(hf):
            history_items.extend(load_jsonl(hf))
            loaded_days += 1

    count_before = len(current_items)

    # 执行去重
    result = dedup(current_items, history_items)

    count_after = len(result)
    count_removed = count_before - count_after

    # 覆盖写入
    save_jsonl(current_file, result)

    print(
        f"去重完成: {count_before} 条 → {count_after} 条"
        f"(移除重复 {count_removed} 条;"
        f"历史窗口 {loaded_days}/{HISTORY_WINDOW_DAYS} 天,共 {len(history_items)} 条历史)"
    )

    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()
