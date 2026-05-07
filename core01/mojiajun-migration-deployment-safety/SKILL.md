---
name: mojiajun-migration-deployment-safety
description: >
  墨家军多文件改进部署到CORE-01的安全流程，包含数据库迁移的部分状态检测、
  CREATE TABLE IF NOT EXISTS陷阱、style_tag回填经验
---

## 墨家军CORE-01安全部署手册

当部署多文件改进（.sql + .py）到CORE-01时，按此流程避免踩坑。

### Step 1：确认SSH连通

```bash
ssh -o ConnectTimeout=10 ubuntu@159.75.12.11 "hostname && uptime"
```

### Step 2：SCP上传文件

```bash
scp -r 05_模块代码/p2-5/ 05_模块代码/p0-2/ ubuntu@159.75.12.11:/home/ubuntu/mojiajun-queue/
```

### Step 3：逐个执行SQL迁移（不要用&&串！）

**关键教训**：用 `&&` 串多个迁移命令时，第一个失败会阻断后续全部执行。
例如 migration_l1.sql 的 ALTER 报 `Duplicate column` 导致 migration_p02.sql 没执行。

**正确做法**：分步执行，每步检查结果：

```bash
# Step 3a: 先检查目标状态
mysql -h127.0.0.1 -uxiaochuan -pxiaochuan_2026_mjj mojiajun -e "DESC notes_published" | grep style_tag

# Step 3b: 如果字段已存在 → 跳过ALTER，直接跑UPDATE部分
# Step 3c: 再跑下一个迁移
mysql -h127.0.0.1 ... < migration_p02.sql
```

### Step 4：CREATE TABLE IF NOT EXISTS 陷阱

`CREATE TABLE IF NOT EXISTS` 对**结构升级**是坑——旧表已存在时静默跳过，新字段不会加上。

**检测方法**：
```bash
mysql ... -e "DESC content_quality_scores" | wc -l
# 如果字段数不对（比如只有8个而不是25个），说明旧表结构挡住了
```

**修复方法**：
1. **优先用 ALTER TABLE ADD COLUMN**（不动旧数据）
2. 如果旧表结构和新需求完全不兼容 → 先备份数据再 DROP+CREATE
3. 确认前永远不要用 DROP（会被拦截）

### Step 5：验证部署结果

```bash
# 验证表结构
mysql ... -e "DESC table_name"
# 验证数据回填
mysql ... -e "SELECT col, COUNT(*) FROM table GROUP BY col"
```

---

## style_tag 回填经验

### 致命错误：把 content_type 当 tone 传

`notes_published.content_type` = "图文笔记"（格式分类），不是风格基调（tone）。

错误代码：
```python
tag_style(title=title, tone=content_type)  # "图文笔记"含"笔记"→命中"干货分享"
```

结果：7条全部误判为"干货分享"。

正确代码：
```python
tag_style(title=title, tone="")  # 没有tone就不要传
```

### 纯关键词打标的边界

当只有标题、没有正文时，规则引擎精度大幅下降：
- 生活化标题（如"天青色烟雨""深圳今天大太阳..."）不堆关键词
- `_MIN_COMBINED_SCORE=1.5` 和 `_TITLE_STYLE_THRESHOLD=2` 阈值下，单关键词命中不触发匹配
- 结果：全部走 L4 兜底 → "实用攻略"

**适用场景**：
- ✅ 标题含明确关键词（如"攻略""教程""笑死"）→ 规则引擎有效
- ✅ 有正文+标题 → 联合打分可用
- ❌ 只有短标题+自然风格 → 需要AI判断

**改进方向**：接入DeepSeek做语义分类，或在 `backfill_style.py` 中先 fetch body 再打标。

---

## SSH Heredoc 引号陷阱

当SQL或Python通过SSH heredoc传输时，多层引号嵌套极易出错。

**错误做法**：
```bash
ssh host 'mysql ... << '\''EOF'\''  # 转义地狱
```

**正确做法**：先写到服务器临时文件再执行
```bash
ssh host "cat > /tmp/script.py << 'PYEOF'
...代码...
PYEOF
python3 /tmp/script.py"
```
