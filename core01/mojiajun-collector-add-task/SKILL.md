---
name: mojiajun-collector-add-task
description: 为墨家军自主采集管道新增采集任务的标准流程——从COLLECT_TASKS定义到建表到save函数到验证
version: 1.0.0
---

# 墨家军采集管道新增任务标准流程

## 概述

在 `CORE-01:/home/ubuntu/mojiajun-queue/agent_outputs/collector.py` 新增采集任务。
现有9个任务（8个陶瓷相关 + 1个条漫爆款），每天自动跑。

## 标准步骤

### Step 1: 在 COLLECT_TASKS 列表末尾新增任务

```python
{
    "id": "your_task_id",           # 唯一ID，snake_case
    "name": "任务中文名",
    "keywords": [                   # 3-7个搜索关键词
        "关键词1 修饰词",
        "关键词2 修饰词",
        "关键词3 修饰词",
    ],
    "sample_type": "分类标签",      # 用于入库分类 / 条件分发
    "max_results": 5,              # 每个关键词搜几条
    "priority": 下一个数字          # 自增
}
```

### Step 2: 如果数据需要独立表 → 建表

```sql
CREATE TABLE IF NOT EXISTS your_table_name (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500),
    url VARCHAR(500),
    summary TEXT,
    content MEDIUMTEXT,
    source VARCHAR(100) DEFAULT 'tavily',
    keywords VARCHAR(200),
    collect_date DATE,
    content_hash VARCHAR(64),
    is_analyzed TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hash (content_hash),
    INDEX idx_collect_date (collect_date),
    INDEX idx_analyzed (is_analyzed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

建表命令：
```bash
docker exec -i ceramic-mysql mysql -u root -pceramic_2026 \
  --default-character-set=utf8mb4 ceramic_db -e "CREATE TABLE IF NOT EXISTS ..."
```

### Step 3: 如果是独立表 → 新增 save 函数

```python
def save_to_xxx(items, keywords=""):
    if not items:
        return 0
    conn = get_db()
    cur = conn.cursor()
    today = datetime.date.today()
    saved = 0
    for item in items:
        title = (item.get("title") or "")[:500]
        url = (item.get("url") or "")[:500]
        summary = (item.get("summary") or item.get("content", "")[:500] or "")[:1000]
        content = (item.get("content") or "")[:5000]
        hash_raw = f"{title}|{url}"
        content_hash = hashlib.sha256(hash_raw.encode("utf-8")).hexdigest()[:32]
        try:
            cur.execute("""INSERT IGNORE INTO your_table (...) VALUES (...)""", ...)
            if cur.rowcount > 0: saved += 1
        except Exception as e: print(f"入库失败: {e}")
    conn.commit(); cur.close(); conn.close()
    return saved
```

### Step 4: 在 run_collect 中加条件分发

```python
if task["sample_type"] == "你的分类标签":
    saved = save_to_xxx(items, keywords=kw)
else:
    saved = save_to_xhs_library(items, sample_type=task["sample_type"], keywords=kw)
```

### Step 5: 验证

```bash
# 手动跑一次
ssh core01 "cd /home/ubuntu/mojiajun-queue && python3 -c \"
from agent_outputs.collector import execute
print(execute({'action': 'run_tasks', 'task_ids': ['your_task_id']}))
\""

# 查入库
ssh core01 "docker exec -i ceramic-mysql mysql -u root -pceramic_2026 \
  --default-character-set=utf8mb4 ceramic_db \
  -e \"SELECT count(*), collect_date FROM your_table GROUP BY collect_date;\""
```

## 已知坑

- `sample_type` 同时用于入库分类和条件分发，确保值和 save 函数匹配
- 修改前备份：`cp collector.py collector.py.bak`
- 文件在 CORE-01，不在本地。先本地写 patch/新增代码 → scp 上传 → 验证
- collector.py 有 233+ 行，改错会影响每天的8个采集任务
