#!/usr/bin/env python3
"""
将 SakuraFrp 帮助文档 Wiki 转换为机器人关键词自动回复语料库。

用法:
    python3 scripts/generate_corpus.py [--output corpus.json]

输出格式为 JSON，每条语料包含:
- id: 唯一标识符 (来自 Markdown 锚点或自动生成)
- question: 问题/标题文本
- keywords: 关键词列表 (用于机器人匹配)
- answer: 回答内容 (纯文本，已去除 Markdown 格式)
- url: 在线文档链接
- category: 分类 (faq/frpc/launcher/app/bestpractice/offtopic/basics)
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

BASE_URL = "https://doc.natfrp.com/"

# 分类目录映射
CATEGORY_MAP = {
    "faq": "常见问题",
    "frpc": "frpc 客户端",
    "launcher": "SakuraFrp 启动器",
    "app": "应用配置指南",
    "bestpractice": "最佳实践",
    "offtopic": "相关教程",
    "rd": "参考文档",
}

# 顶层文档映射
TOP_LEVEL_CATEGORY = {
    "basics.md": "基础知识",
    "geek.md": "极客用户",
    "about.md": "关于",
    "index.md": "首页",
    "faq.md": "常见问题导航",
}

# 不处理的文件
SKIP_FILES = {"style.md", "devcontainer.md", "README.md"}

# 关键词提取的最小字符长度
MIN_CHINESE_WORD_LENGTH = 2   # 中文词最少字符数
MIN_ENGLISH_WORD_LENGTH = 2   # 英文词最少字符数 (不含首字母)
MIN_ANCHOR_WORD_LENGTH = 3    # 锚点分词最少字符数

# 中文停用词 (用于关键词提取时剔除)
CHINESE_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "但",
    "如果", "可以", "请", "时", "可", "用", "或", "与", "及", "等",
    "为", "以", "而", "这个", "那个", "这些", "那些", "从", "已",
    "还", "将", "被", "对", "其", "他", "她", "它", "此", "该",
    "当", "则", "虽", "虽然", "因为", "所以", "但是", "然后", "如何",
    "怎么", "什么", "哪", "哪个", "哪些", "为什么", "怎样",
}


def get_file_url(rel_path: str, anchor: str = "") -> str:
    """根据相对文件路径生成文档 URL。"""
    # 将文件路径转换为 URL 路径
    url_path = rel_path.replace("\\", "/")
    # 将 .md 替换为 .html
    url_path = re.sub(r"\.md$", ".html", url_path)
    # 去除 index.html 末尾
    url_path = re.sub(r"/index\.html$", "/", url_path)
    if url_path == "index.html":
        url_path = ""
    full_url = BASE_URL + url_path
    if anchor:
        full_url += "#" + anchor
    return full_url


def get_category(rel_path: str) -> str:
    """根据文件路径推断分类。"""
    parts = Path(rel_path).parts
    filename = Path(rel_path).name
    if len(parts) > 1:
        return CATEGORY_MAP.get(parts[0], parts[0])
    return TOP_LEVEL_CATEGORY.get(filename, "其他")


def strip_frontmatter(content: str) -> str:
    """去除 YAML frontmatter。"""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:].lstrip("\n")
    return content


def strip_markdown_syntax(text: str) -> str:
    """将 Markdown 文本转为可读纯文本。"""
    # 去除 VuePress 容器块 (:::: details, ::: tip, 等)
    text = re.sub(r":{2,4}\s*\w*[^\n]*\n?", "", text)
    # 去除 tab 指令
    text = re.sub(r"@tab[^\n]*\n?", "", text)
    # 去除 include 指令
    text = re.sub(r"<!--\s*@include:[^>]*-->\n?", "", text)
    # 去除 HTML 注释
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 去除代码块 (保留内容以便机器人理解命令)
    text = re.sub(r"```[^\n]*\n(.*?)```", lambda m: m.group(1).strip(), text, flags=re.DOTALL)
    # 去除行内代码反引号，保留内容
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 去除加粗/斜体标记
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # 去除链接，只保留文字
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 去除图片
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # 去除表格分隔行
    text = re.sub(r"\|[-: ]+\|[-| :]*\n", "", text)
    # 规范化空白行
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 去除行首多余空格
    text = re.sub(r"^ +", "", text, flags=re.MULTILINE)
    return text.strip()


def extract_keywords(heading: str, anchor_id: str) -> list[str]:
    """从标题文字和锚点 ID 中提取关键词。"""
    keywords = []

    # 从标题中提取词汇 (中文字符块 + 英文单词/数字)
    words = re.findall(
        rf"[\u4e00-\u9fff]{{{MIN_CHINESE_WORD_LENGTH},}}|[A-Za-z][A-Za-z0-9._-]{{{MIN_ENGLISH_WORD_LENGTH},}}",
        heading,
    )
    for word in words:
        word = word.strip()
        if word and word not in CHINESE_STOPWORDS:
            if word not in keywords:
                keywords.append(word)

    # 从锚点 ID 中提取英文关键词 (按 - 分割，过滤常见介词)
    anchor_stopwords = {"to", "in", "on", "at", "of", "a", "an", "the",
                        "and", "or", "for", "is", "are", "not", "with"}
    if anchor_id:
        anchor_words = [w for w in anchor_id.split("-")
                        if len(w) >= MIN_ANCHOR_WORD_LENGTH and w not in anchor_stopwords]
        for word in anchor_words:
            if word not in keywords:
                keywords.append(word)

    return keywords


def parse_heading(line: str) -> tuple[int, str, str] | None:
    """
    解析 Markdown 标题行，返回 (级别, 文字, 锚点ID)。
    例如: '## 一个 frpc 可以连接多条隧道吗 {#frpc-connect-to-multiple-tunnels}'
    返回: (2, '一个 frpc 可以连接多条隧道吗', 'frpc-connect-to-multiple-tunnels')
    """
    m = re.match(r"^(#{1,6})\s+(.+)$", line)
    if not m:
        return None
    level = len(m.group(1))
    rest = m.group(2).strip()

    # 提取 {#anchor-id}
    anchor_match = re.search(r"\{#([^}]+)\}\s*$", rest)
    anchor_id = ""
    if anchor_match:
        anchor_id = anchor_match.group(1)
        rest = rest[:anchor_match.start()].strip()

    # 去除标题中的内联格式
    rest = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", rest)
    rest = re.sub(r"`([^`]+)`", r"\1", rest)
    rest = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", rest)

    return level, rest, anchor_id


def process_file(filepath: Path, wiki_root: Path) -> list[dict]:
    """处理单个 Markdown 文件，提取所有段落为语料条目。"""
    rel_path = filepath.relative_to(wiki_root).as_posix()
    if filepath.name in SKIP_FILES:
        return []

    content = filepath.read_text(encoding="utf-8")
    content = strip_frontmatter(content)
    lines = content.splitlines()

    category = get_category(rel_path)
    entries = []

    current_heading: tuple[int, str, str] | None = None
    current_lines: list[str] = []
    # 用于去重的 ID 计数器
    seen_ids: dict[str, int] = {}

    def flush_entry():
        nonlocal current_heading, current_lines
        if current_heading is None:
            current_lines = []
            return
        level, title, anchor_id = current_heading
        body = "\n".join(current_lines)
        answer = strip_markdown_syntax(body)

        # 生成唯一 ID
        if anchor_id:
            entry_id = anchor_id
        else:
            # 用路径+标题的 slug 作为 ID
            slug = re.sub(r"[^\w\u4e00-\u9fff-]", "-", title.lower())
            slug = re.sub(r"-+", "-", slug).strip("-")
            file_slug = re.sub(r"[/\\.]", "-", rel_path.rsplit(".", 1)[0])
            entry_id = f"{file_slug}-{slug}"

        # 处理重复 ID
        base_id = entry_id
        count = seen_ids.get(base_id, 0)
        if count > 0:
            entry_id = f"{base_id}-{count}"
        seen_ids[base_id] = count + 1

        url = get_file_url(rel_path, anchor_id)
        keywords = extract_keywords(title, anchor_id)

        # 只收录有实质内容的条目，或分级较高的段落
        if answer.strip():
            entries.append({
                "id": entry_id,
                "question": title,
                "keywords": keywords,
                "answer": answer,
                "url": url,
                "category": category,
            })

        current_heading = None
        current_lines = []

    for line in lines:
        heading = parse_heading(line)
        if heading and heading[0] <= 3:
            flush_entry()
            current_heading = heading
        else:
            if current_heading is not None:
                current_lines.append(line)

    flush_entry()
    return entries


def generate_corpus(wiki_root: Path) -> dict:
    """遍历 Wiki 所有 Markdown 文件，生成完整语料库。"""
    all_entries = []

    # 收集所有 .md 文件 (排除 .vuepress、node_modules 等)
    md_files = sorted(
        f for f in wiki_root.rglob("*.md")
        if not any(
            part.startswith(".") or part in ("node_modules", "_usage")
            for part in f.parts
        )
        and f.name not in SKIP_FILES
    )

    for md_file in md_files:
        entries = process_file(md_file, wiki_root)
        all_entries.extend(entries)

    return {
        "version": "1.0",
        "updated_at": date.today().isoformat(),
        "base_url": BASE_URL,
        "description": "SakuraFrp 帮助文档语料库，用于机器人关键词自动回复",
        "total": len(all_entries),
        "entries": all_entries,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="生成 SakuraFrp Wiki 机器人语料库")
    parser.add_argument(
        "--output", "-o",
        default="corpus.json",
        help="输出文件路径 (默认: corpus.json)",
    )
    parser.add_argument(
        "--wiki-root",
        default=None,
        help="Wiki 根目录路径 (默认: 脚本所在目录的父目录)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON 缩进空格数 (默认: 2，设为 0 则压缩输出)",
    )
    args = parser.parse_args()

    if args.wiki_root:
        wiki_root = Path(args.wiki_root)
    else:
        wiki_root = Path(__file__).parent.parent

    if not wiki_root.is_dir():
        print(f"错误: Wiki 根目录不存在: {wiki_root}", file=sys.stderr)
        sys.exit(1)

    print(f"正在处理 Wiki 目录: {wiki_root}")
    corpus = generate_corpus(wiki_root)

    output_path = Path(args.output)
    indent = args.indent if args.indent > 0 else None
    output_path.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=indent) + "\n",
        encoding="utf-8",
    )

    print(f"语料库生成完成: {output_path}")
    print(f"共 {corpus['total']} 条语料")


if __name__ == "__main__":
    main()
