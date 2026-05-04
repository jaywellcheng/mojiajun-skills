#!/usr/bin/env python3
"""
墨家军 memdir 管理器
借鉴 Claude Code memdir 设计：独立文件 + INDEX.md索引 + 智能截断

部署位置: /home/ubuntu/mojiajun-queue/knowledge/
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================
# 配置
# ============================================================
KNOWLEDGE_ROOT = Path("/home/ubuntu/mojiajun-queue/knowledge")
ENTRYPOINT_NAME = "INDEX.md"
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000
CATEGORIES = ["content", "user", "system", "market"]

FRONTMATTER_TEMPLATE = """---
type: {category}
created: {created}
updated: {updated}
---
"""

# ============================================================
# 核心：智能截断（借鉴 Claude Code truncateEntrypointContent）
# ============================================================
def truncate_entrypoint(raw: str) -> dict:
    """
    智能截断INDEX.md：先按行→再按字节→在换行处截断
    返回截断后的内容和元数据
    """
    trimmed = raw.strip()
    lines = trimmed.split('\n')
    line_count = len(lines)
    byte_count = len(trimmed.encode('utf-8'))

    was_line_truncated = line_count > MAX_ENTRYPOINT_LINES
    was_byte_truncated = byte_count > MAX_ENTRYPOINT_BYTES

    if not was_line_truncated and not was_byte_truncated:
        return {
            "content": trimmed,
            "line_count": line_count,
            "byte_count": byte_count,
            "was_truncated": False
        }

    # 先按行截断
    content = '\n'.join(lines[:MAX_ENTRYPOINT_LINES]) if was_line_truncated else trimmed

    # 再按字节截断（在最后一个完整换行处切断）
    if len(content.encode('utf-8')) > MAX_ENTRYPOINT_BYTES:
        cut_at = content[:MAX_ENTRYPOINT_BYTES].rfind('\n')
        if cut_at > 0:
            content = content[:cut_at]

    size_kb = byte_count / 1024
    max_kb = MAX_ENTRYPOINT_BYTES / 1024
    reason = ""
    if was_byte_truncated and not was_line_truncated:
        reason = f"{size_kb:.1f}KB (limit: {max_kb:.0f}KB) — index entries are too long"
    elif was_line_truncated and not was_byte_truncated:
        reason = f"{line_count} lines (limit: {MAX_ENTRYPOINT_LINES})"
    else:
        reason = f"{line_count} lines and {size_kb:.1f}KB"

    warning = f"\n\n> WARNING: {ENTRYPOINT_NAME} is {reason}. Only part of it was loaded."
    content += warning

    return {
        "content": content,
        "line_count": line_count,
        "byte_count": byte_count,
        "was_truncated": True,
        "reason": reason
    }


# ============================================================
# 索引管理
# ============================================================
def read_index() -> str:
    """读取当前INDEX.md内容"""
    index_path = KNOWLEDGE_ROOT / ENTRYPOINT_NAME
    if index_path.exists():
        return index_path.read_text(encoding='utf-8')
    return ""


def add_to_index(category: str, filename: str, description: str):
    """向INDEX.md添加一行索引条目"""
    KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
    index_path = KNOWLEDGE_ROOT / ENTRYPOINT_NAME

    existing = read_index()
    new_line = f"- [{filename.replace('.md', '')}]({category}/{filename}) — {description}"

    # 去重：如果已有相同条目，跳过
    if new_line in existing:
        return

    lines = existing.split('\n') if existing else ["# 墨家军知识索引", ""]
    lines.append(new_line)

    # 截断保护
    new_content = '\n'.join(lines)
    result = truncate_entrypoint(new_content)
    index_path.write_text(result["content"], encoding='utf-8')

    if result["was_truncated"]:
        print(f"  ⚠️ INDEX.md reached limit: {result['reason']}")


def rebuild_index():
    """重建整个索引——扫描所有分类目录"""
    entries = []
    for cat in CATEGORIES:
        cat_dir = KNOWLEDGE_ROOT / cat
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.md")):
            # 读取frontmatter中的描述
            content = f.read_text(encoding='utf-8')
            title = f.stem.replace('_', ' ').title()
            # 尝试取第一行非标题内容作为描述
            desc = ""
            in_frontmatter = False
            for line in content.split('\n'):
                if line.strip() == '---':
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter:
                    continue
                if line.startswith('# '):
                    title = line[2:].strip()
                    continue
                if line.strip() and not desc:
                    desc = line.strip()[:80]
                    break
            if not desc:
                desc = f"{title} related memory"
            entries.append((cat, f.name, title, desc))

    # 重建INDEX.md
    lines = [
        "# 墨家军知识索引",
        f"",
        f"_Last rebuilt: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        f"_Entries: {len(entries)}_",
        f"",
    ]

    for cat in CATEGORIES:
        cat_entries = [e for e in entries if e[0] == cat]
        if not cat_entries:
            continue
        lines.append(f"## {cat}")
        lines.append("")
        for _, fname, title, desc in cat_entries:
            lines.append(f"- [{title}]({cat}/{fname}) — {desc}")
        lines.append("")

    result = truncate_entrypoint('\n'.join(lines))
    index_path = KNOWLEDGE_ROOT / ENTRYPOINT_NAME
    index_path.write_text(result["content"], encoding='utf-8')
    print(f"INDEX.md rebuilt: {len(entries)} entries")
    if result["was_truncated"]:
        print(f"  ⚠️ {result['reason']}")


# ============================================================
# 记忆文件CRUD
# ============================================================
def write_memory(category: str, filename: str, title: str, content: str, description: str = ""):
    """写入/更新一个记忆文件，同时更新索引"""
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category: {category}. Must be one of {CATEGORIES}")

    cat_dir = KNOWLEDGE_ROOT / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    if not filename.endswith('.md'):
        filename += '.md'

    filepath = cat_dir / filename
    now = datetime.now().strftime('%Y-%m-%d')

    # 检查是否已存在（更新时保留created）
    created = now
    if filepath.exists():
        old = filepath.read_text(encoding='utf-8')
        m = re.search(r'created:\s*(\S+)', old)
        if m:
            created = m.group(1)

    full_content = f"{FRONTMATTER_TEMPLATE.format(category=category, created=created, updated=now)}\n# {title}\n\n{content}\n"
    filepath.write_text(full_content, encoding='utf-8')

    # 更新索引
    desc = description or content.split('\n')[0][:80]
    add_to_index(category, filename, desc)

    print(f"  ✅ {category}/{filename} written ({len(full_content)} bytes)")


def read_memory(category: str, filename: str) -> Optional[str]:
    """读取一个记忆文件"""
    if not filename.endswith('.md'):
        filename += '.md'
    filepath = KNOWLEDGE_ROOT / category / filename
    if filepath.exists():
        return filepath.read_text(encoding='utf-8')
    return None


def list_memories(category: str = None):
    """列出所有记忆"""
    cats = [category] if category else CATEGORIES
    total = 0
    total_bytes = 0
    for cat in cats:
        cat_dir = KNOWLEDGE_ROOT / cat
        if not cat_dir.exists():
            continue
        files = sorted(cat_dir.glob("*.md"))
        if files:
            print(f"\n## {cat} ({len(files)} files)")
            for f in files:
                size = f.stat().st_size
                total_bytes += size
                # 读取title
                text = f.read_text(encoding='utf-8')
                title = f.stem
                for line in text.split('\n'):
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                print(f"  {f.name:<30} {size:>6}B  {title}")
            total += len(files)
    print(f"\nTotal: {total} files, {total_bytes/1024:.1f}KB")

    # INDEX.md状态
    index_path = KNOWLEDGE_ROOT / ENTRYPOINT_NAME
    if index_path.exists():
        idx_size = index_path.stat().st_size
        idx_lines = len(index_path.read_text(encoding='utf-8').split('\n'))
        print(f"INDEX.md: {idx_lines} lines, {idx_size/1024:.1f}KB "
              f"({'⚠️ OVER LIMIT' if idx_lines > MAX_ENTRYPOINT_LINES or idx_size > MAX_ENTRYPOINT_BYTES else 'OK'})")


def search_memories(query: str):
    """在记忆文件中搜索（简单grep替代）"""
    import subprocess
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.md", query, str(KNOWLEDGE_ROOT)],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout:
            print(result.stdout)
        else:
            print(f"No matches for '{query}'")
    except FileNotFoundError:
        # fallback Python搜索
        for cat in CATEGORIES:
            cat_dir = KNOWLEDGE_ROOT / cat
            if not cat_dir.exists():
                continue
            for f in cat_dir.glob("*.md"):
                content = f.read_text(encoding='utf-8')
                if query.lower() in content.lower():
                    for i, line in enumerate(content.split('\n'), 1):
                        if query.lower() in line.lower():
                            print(f"{cat}/{f.name}:{i}: {line.strip()}")


# ============================================================
# 初始化/迁移
# ============================================================
def init_memdir():
    """初始化memdir目录结构"""
    KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
    for cat in CATEGORIES:
        (KNOWLEDGE_ROOT / cat).mkdir(exist_ok=True)

    # 创建初始INDEX.md
    index_path = KNOWLEDGE_ROOT / ENTRYPOINT_NAME
    if not index_path.exists():
        index_path.write_text(
            "# 墨家军知识索引\n\n"
            "Knowledge entries are organized by category. "
            "Each entry links to a file in the category directory.\n\n"
            "> This index auto-updates when memories are added. "
            "Keep entries concise — one line per file, ~150 chars.\n",
            encoding='utf-8'
        )
    print(f"✅ memdir initialized at {KNOWLEDGE_ROOT}")
    print(f"   Categories: {', '.join(CATEGORIES)}")


def migrate_from_memory_md(source_path: str):
    """
    从现有MEMORY.md迁移到memdir结构
    解析§分隔的条目，按内容分类放入对应目录
    """
    source = Path(source_path)
    if not source.exists():
        print(f"❌ Source file not found: {source_path}")
        return

    content = source.read_text(encoding='utf-8')
    sections = content.split('§')

    # 关键词→分类映射
    category_keywords = {
        "content": ["content", "strategy", "title", "formula", "hot", "pattern", "failure", "content"],
        "user": ["user", "大威", "brand", "style", "persona", "preference", "review"],
        "system": ["system", "architecture", "agent", "deploy", "MySQL", "CORE", "bug", "fix", "worker"],
        "market": ["market", "competitor", "trend", "price", "sales", "customer"],
    }

    migrated = 0
    for i, section in enumerate(sections):
        section = section.strip()
        if not section or len(section) < 20:
            continue

        # 判断分类
        section_lower = section.lower()
        category = "system"  # 默认
        for cat, keywords in category_keywords.items():
            if any(kw.lower() in section_lower for kw in keywords):
                category = cat
                break

        # 取第一行作为标题
        lines = section.split('\n')
        title = lines[0].strip().lstrip('#').strip()[:60]
        if not title:
            title = f"memory_{i}"

        # 生成文件名
        slug = re.sub(r'[^a-z0-9]+', '_', title.lower())[:40]
        filename = f"{slug}.md"

        # 写入
        write_memory(category, filename, title, section, lines[1].strip() if len(lines) > 1 else "")
        migrated += 1

    rebuild_index()
    print(f"\n✅ Migrated {migrated} sections from {source_path}")


# ============================================================
# CLI入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="墨家军 memdir 知识目录管理")
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init", help="初始化memdir目录结构")
    sub.add_parser("list", help="列出所有记忆")
    sub.add_parser("rebuild", help="重建INDEX.md索引")

    add_p = sub.add_parser("add", help="添加记忆")
    add_p.add_argument("category", choices=CATEGORIES)
    add_p.add_argument("filename")
    add_p.add_argument("title")
    add_p.add_argument("content")
    add_p.add_argument("--desc", default="", help="简短描述（用于索引）")

    read_p = sub.add_parser("read", help="读取记忆")
    read_p.add_argument("category", choices=CATEGORIES)
    read_p.add_argument("filename")

    search_p = sub.add_parser("search", help="搜索记忆")
    search_p.add_argument("query")

    migrate_p = sub.add_parser("migrate", help="从MEMORY.md迁移")
    migrate_p.add_argument("source_path")

    args = parser.parse_args()

    if args.command == "init":
        init_memdir()
    elif args.command == "list":
        list_memories()
    elif args.command == "rebuild":
        rebuild_index()
    elif args.command == "add":
        write_memory(args.category, args.filename, args.title, args.content, args.desc)
    elif args.command == "read":
        result = read_memory(args.category, args.filename)
        if result:
            print(result)
        else:
            print(f"Not found: {args.category}/{args.filename}")
    elif args.command == "search":
        search_memories(args.query)
    elif args.command == "migrate":
        migrate_from_memory_md(args.source_path)
    else:
        parser.print_help()
