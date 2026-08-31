#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 URL 的新闻聚合脚本。

用法:
  python3 cluster.py <current_file> <output_file>

参数:
  current_file  去重后的 JSONL(每行含 title / content / url / source / publish_time)
  output_file   聚合后的 JSONL,每行一条聚合记录:
    {"id": 0, "title": "...", "content": "...", "sources": [{"url": "...", "source": "..."}], "publish_time": "..."}

聚合规则:
  1. 按 URL 精确匹配分组(同一 URL 的多条记录合并为一条)
  2. title / publish_time: 取 content 最长的那条记录的值
  3. content: 多条记录的 content 用 "--- From {source} ---" 分隔串联
  4. sources: 所有记录的 {url, source} 取并集

退出码:
  0 成功  1 无输入  2 参数错误
"""

import json
import os
import sys
from collections import OrderedDict


def load_jsonl(fp: str) -> list:
    items = []
    if not os.path.exists(fp):
        return items
    with open(fp, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"警告: 第 {lineno} 行 JSON 解析失败,已跳过", file=sys.stderr)
    return items


def aggregate(items: list) -> list:
    """按 URL 分组聚合,返回聚合记录列表。"""
    # 用 OrderedDict 保持首次出现顺序
    groups: dict[str, list] = OrderedDict()
    for item in items:
        url = item.get("url", "")
        if not url:
            continue
        groups.setdefault(url, []).append(item)

    results = []
    for url, members in groups.items():
        # 找 content 最长的记录
        best = max(members, key=lambda m: len(m.get("content", "")))

        # 串联正文
        content_parts = []
        for m in members:
            source = m.get("source", "未知来源")
            content = m.get("content", "")
            if content:
                content_parts.append(f"--- From {source} ---\n{content}")
        content = "\n".join(content_parts) if len(members) > 1 else best.get("content", "")

        # sources 取并集(按 url+source 去重)
        seen = set()
        sources = []
        for m in members:
            key = (m.get("url", ""), m.get("source", ""))
            if key not in seen:
                seen.add(key)
                sources.append({"url": m.get("url", ""), "source": m.get("source", "")})

        results.append({
            "id": len(results),
            "title": best.get("title", ""),
            "content": content,
            "sources": sources,
            "publish_time": best.get("publish_time", ""),
        })

    return results


def main():
    if len(sys.argv) < 3:
        print("用法: python3 cluster.py <current_file> <output_file>", file=sys.stderr)
        sys.exit(2)

    current_file, output_file = sys.argv[1], sys.argv[2]
    items = load_jsonl(current_file)
    if not items:
        print("输入为空")
        sys.exit(1)

    results = aggregate(items)

    with open(output_file, "w", encoding="utf-8") as f:
        for record in results:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    multi = sum(1 for members in _count_groups(items).values() if len(members) > 1)
    print(f"聚合完成: {len(items)} 条 → {len(results)} 条(其中 {multi} 条由多源合并)")


def _count_groups(items: list) -> dict:
    groups: dict[str, list] = {}
    for item in items:
        url = item.get("url", "")
        if url:
            groups.setdefault(url, []).append(item)
    return groups


if __name__ == "__main__":
    main()
