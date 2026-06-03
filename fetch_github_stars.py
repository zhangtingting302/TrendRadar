"""
GitHub 高星新项目 RSS 生成器

通过 GitHub Search API 获取最近7天新建的高 Star 仓库，
生成 RSS XML 文件供 TrendRadar 读取。

使用方式：
  uv run python fetch_github_stars.py
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "rss_cache")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "github-stars.xml")

# 搜索条件
DAYS_BACK = 7
MIN_STARS = 50
MAX_ITEMS = 30


def fetch_new_repos(days_back=7, min_stars=50, max_items=30):
    """从 GitHub API 获取最近创建的高星仓库"""
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = (
        f"https://api.github.com/search/repositories"
        f"?q=created:>{since}+stars:>{min_stars}"
        f"&sort=stars&order=desc&per_page={max_items}"
    )

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "TrendRadar-RSS-Generator",
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"[GitHub Stars] API 限流，跳过本次获取")
            return []
        print(f"[GitHub Stars] API 错误: {e.code} {e.reason}")
        return []
    except Exception as e:
        print(f"[GitHub Stars] 请求失败: {e}")
        return []

    repos = []
    for item in data.get("items", []):
        repos.append({
            "name": item["full_name"],
            "url": item["html_url"],
            "description": item.get("description") or "",
            "stars": item["stargazers_count"],
            "language": item.get("language") or "",
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
            "topics": item.get("topics") or [],
            "homepage": item.get("homepage") or "",
        })

    print(f"[GitHub Stars] 获取 {len(repos)}/{data.get('total_count', 0)} 个新项目 (>{min_stars} stars, 近{days_back}天)")
    return repos


def generate_rss(repos):
    """将仓库列表转为 RSS XML"""
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "GitHub 高星新项目"
    SubElement(channel, "link").text = "https://github.com/trending"
    SubElement(channel, "description").text = f"最近{DAYS_BACK}天新建的 Star>{MIN_STARS} 的 GitHub 项目"
    SubElement(channel, "language").text = "zh-CN"

    for repo in repos:
        item = SubElement(channel, "item")

        # 标题包含 Star 数和语言，方便 AI 分析
        lang_tag = f" [{repo['language']}]" if repo["language"] else ""
        title = f"{repo['name']}{lang_tag} ({repo['stars']} stars)"
        SubElement(item, "title").text = title
        SubElement(item, "link").text = repo["url"]

        # 描述包含完整信息
        desc_parts = []
        if repo["description"]:
            desc_parts.append(repo["description"])
        if repo["topics"]:
            desc_parts.append(f"Topics: {', '.join(repo['topics'][:10])}")
        if repo["homepage"]:
            desc_parts.append(f"Homepage: {repo['homepage']}")
        desc_parts.append(f"Language: {repo['language'] or 'N/A'}")
        desc_parts.append(f"Stars: {repo['stars']}")
        SubElement(item, "description").text = " | ".join(desc_parts)

        SubElement(item, "pubDate").text = repo["created_at"]
        SubElement(item, "guid").text = repo["url"]

    return rss


def save_rss(rss_element, filepath):
    """保存 RSS 到文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    rough = tostring(rss_element, encoding="unicode")
    pretty = parseString(rough).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(pretty)
    print(f"[GitHub Stars] RSS 已保存: {filepath} ({os.path.getsize(filepath)} bytes)")


def main():
    repos = fetch_new_repos(DAYS_BACK, MIN_STARS, MAX_ITEMS)
    if not repos:
        print("[GitHub Stars] 未获取到项目，跳过 RSS 生成")
        return

    rss = generate_rss(repos)
    save_rss(rss, OUTPUT_FILE)


if __name__ == "__main__":
    main()
