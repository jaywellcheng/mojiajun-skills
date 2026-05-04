---
name: book-insights-to-core-kb
description: 从读书笔记中提取洞察并写入墨家军核心知识库的完整工作流。包含解析→分析→审核清单→写入core_knowledge_items全流程。
version: 1.1.0
tags:
  - mojiajun
  - knowledge-base
  - books
  - core-kb
---

# 书籍洞察 → 核心知识库工作流

## 概述

将读书笔记中与天青浅业务相关的洞察提炼出来，经大威审核后写入核心知识库（`core_knowledge_items`表），供所有Agent引用。

## 前置条件

- CORE-01: 159.75.12.11, MySQL mojiajun
- 书籍笔记源文件（如 `reading-notes.md`）
- `core_knowledge_items` 和 `core_library_log` 表已建

## 完整流程

### Step 1: 分析源文件结构
```bash
grep "^## 《" reading-notes.md | wc -l  # 总书数
grep "^## 《书名》" reading-notes.md      # 查特定书
```

### Step 2: 交叉比对现有KB
```bash
# 导出KB已有书名
ssh ubuntu@159.75.12.11 "mysql -h127.0.0.1 -uxiaochuan -pxiaochuan_2026_mjj mojiajun -N -e 'SELECT title FROM knowledge_base'" > kb_existing.txt
```

### Step 3: 针对缺失书籍解析笔记
提取：书名、作者、核心观点、金句、分类

### Step 4: 分析业务相关性
筛选与天青浅相关的书（营销心理、品牌战略、内容创作、文化素材）
提炼为可操作的业务洞察（非纯学术摘抄）

### Step 5: 生成审核清单
格式见 `core-knowledge-base-guardian` skill
每个洞察标注：分类、标题、内容、来源、证据

### Step 6: 大威审核通过后写入核心库
```sql
INSERT INTO core_knowledge_items (category, title, content, source, evidence, status, reviewed_by, reviewed_at)
VALUES (...);
```

### Step 7: 记录审核日志
```sql
INSERT INTO core_library_log (action_type, target_table, summary, reviewed_by, reviewed_at)
VALUES ('INSERT', 'core_knowledge_items', '...', '大威', NOW());
```

## 有效分类（category）

| 分类 | 用途 |
|------|------|
| psych_switch | 心理开关/决策心理 |
| content_principle | 内容创作原则 |
| style_guide | 风格指南/文化素材 |
| title_formula | 标题公式 |
| topic | 话题方向 |

## 产出物

1. `missing_books_data.json` — 缺失书籍结构化数据
2. `核心知识库审核清单_书籍洞察_YYYYMMDD.md` — 审核清单
3. `insert_core_knowledge.py` — 写入脚本（scp到CORE-01执行）
4. 源文件归档到 `墨家军资料库/书籍笔记_小艾/`

## 两种书籍笔记格式

### 格式A：通用阅读笔记（小艾 reading-notes.md）
```
## 《书名》- 作者
> ⭐ 推荐指数：★★★★★
### 核心观点
1. 观点...
### 经典金句
> "金句..."
```

### 格式B：实战定制笔记（大威 new-books 系列）
```
### 《书名》- 作者
**推荐指数：** ★★★★★
**一句话总结：** ...
### 核心观点
### 大威业务启示    ← 专属字段
### 我的思考
### 一句话行动        ← 专属字段
```

解析时需分别处理。格式B用 `### 《` 分割（不是 `## 《`），且字段名不同。

## 大文件上传：gzip + SSH 管道

当 JSON 超过 ~50KB 时，base64 命令行参数会爆 "Argument list too long"。替代方案：

```bash
# ✅ 压缩后管道传输（130KB 都能过）
gzip -c data.json | ssh user@host "cat > /tmp/data.json.gz && gunzip -f /tmp/data.json.gz"

# ✅ 小文件可用 SSH heredoc 直接写脚本
ssh user@host "cat > /tmp/script.py << 'PYEOF'
...Python code...
PYEOF
"

# ✅ SSH python3 -c 时避免 f-string 里的 dict['key']（引号会被 shell 吃掉）
# 改用 .get() 方法：
ssh host "python3 -c \"
t = b.get('title','')  # 不要用 b['title']
print('OK', t)
\""
```

## 两种书籍笔记格式

### 格式A：通用阅读笔记（小艾 reading-notes.md）
```
## 《书名》- 作者
> ⭐ 推荐指数：★★★★★
### 核心观点
1. 观点...
### 经典金句
> "金句..."
```

### 格式B：实战定制笔记（大威 new-books 系列）
```
### 《书名》- 作者
**推荐指数：** ★★★★★
**一句话总结：** ...
### 核心观点
### 大威业务启示    ← 专属字段
### 我的思考
### 一句话行动        ← 专属字段
```

解析时需分别处理。格式B用 `### 《` 分割（不是 `## 《`），且字段名不同。

## 大文件上传：gzip + SSH 管道（★重要）

当 JSON 超过 ~50KB 时，base64 命令行参数会爆 `Argument list too long`。scp 也可能被 blocked。

```bash
# ✅ 正确：压缩后管道传输（130KB 都能过）
gzip -c data.json | ssh user@host "cat > /tmp/data.json.gz && gunzip -f /tmp/data.json.gz"

# ✅ SSH heredoc 写小脚本（数据本身不在脚本里）
ssh user@host "cat > /tmp/script.py << 'PYEOF'
import json, pymysql
with open('/tmp/data.json') as f:
    books = json.load(f)
# ... insert logic ...
PYEOF
"

# ✅ SSH python3 -c 传参时避免 f-string 里的 dict['key']
# 单引号会被 shell 吃掉！b['title'] → b[title] → NameError
# 改用 .get() 方法：
ssh host "python3 -c \"
t = b.get('title','')  # 安全写法
print('OK', t)
\""
```

## 踩坑

1. **书名匹配不精确**：中文书名可能有《》包裹、英文副标题、作者名、"或同类替代"等变体。用 `re.sub(r'\s*（或.*?）', '', title)` 先清洗再比对
2. **core_knowledge_items表可能不存在**：先 `CREATE TABLE IF NOT EXISTS`（本会话首次写入时即遇到）
3. **Shell传JSON/大参数必崩**：数据超过 50KB 用 gzip+SSH 管道，入库脚本一律 Python pymysql
4. **书籍洞察不是学术摘抄**：必须转化为天青浅/墨家军可用的业务知识，而非原文罗列
5. **SSH f-string 引号陷阱**：`f"OK {b['title']}"` 通过 SSH 时单引号被 shell 剥离 → NameError。一律用 `b.get('title','')` 或先赋值变量
6. **MySQL 只绑 127.0.0.1**：本地 Mac 无法直连 CORE-01 的 MySQL，所有入库操作必须在服务器端执行
5. **SSH f-string 引号陷阱**：`f"OK {b['title']}"` 通过 SSH 时 `['title']` 的单引号会被 shell 剥离变成 `b[title]` NameError。改用 `b.get('title','')` 或变量中转
6. **★ 评级字符匹配**：非ASCII星号可能匹配失败导致rating=0，用 `[★☆]` 字符类 + `.count('★')` 兜底
7. **MySQL 只绑 127.0.0.1**：本地Mac无法直连，所有入库操作必须在服务器端执行
