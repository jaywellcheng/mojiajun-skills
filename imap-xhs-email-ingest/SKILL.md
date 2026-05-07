---
name: imap-xhs-email-ingest
description: 小云IMAP邮件轮询入库方案 — 收小墨凌晨发的[XHS_DATA]邮件，解析JSON入库到MySQL。含字段映射对齐、去重、cron调度全流程。
version: 1.0.0
author: 小云
metadata:
  hermes:
    tags: [IMAP, Email, MySQL, 数据入库, 墨家军]
---

# IMAP邮件轮询入库 — [XHS_DATA] 数据采集邮件

## 适用场景
小墨（程墨白）每天凌晨1点通过邮件发送小红书内容采集数据，小云（CORE-01）自动轮询收信并入库到 `ceramic_db.xhs_sample_library` 表。

## 邮件格式
- **主题（两种格式都可能）:** 
  - 格式A: `[XHS_DATA] YYYY-MM-DD 内容采集数据`
  - 格式B: `每日内容采集数据入库 - YYYYMMDD`
- **数据位置（两种都可能）:**
  - **正文:** 按 `sample_type` 分段JSON记录（之前的方式）
  - **附件TXT:** 文件名 `content_fetch_YYYYMMDD.txt`，内含完整JSON（⚠️ 新方式，2026-05-07开始使用）
- **发送时间:** 每天凌晨1:00~1:35
- **收件箱:** 76835298@qq.com（QQ邮箱，授权码登录）

### ⚠️ 数据结构（来自邮件附件）
数据包外层有包装结构，不是直接JSON数组：
```json
{
  "fetch_date": "2026-05-07",
  "fetch_time": "01:28:25",
  "total_samples": 42,
  "samples": [
    {
      "sample_type": "comic_competitor",
      "items": [ ... ]
    },
    {
      "sample_type": "小红书爆款",
      "items": [ ... ]
    }
  ]
}
```
即数据在 `samples` 数组里，每项有 `sample_type` 和 `items`（具体记录列表）。脚本需解析这个嵌套结构。

## JSON字段映射

| 邮件字段 | 入库字段 | 说明 |
|---------|---------|------|
| title | title | 标题 |
| content | summary | 正文内容 |
| source_url | source_url | 笔记原始链接（需先ALTER TABLE加字段） |
| url | url | 笔记短链接 |
| author | author | 作者名 |
| likes | likes | 点赞数 |
| collects | favorites | 收藏数 |
| comments | comments | 评论数 |
| author_fans | author_fans | 作者粉丝数 |
| sample_type | sample_type | 采集类型 |
| image_style | tags | 风格标签 |
| — | source | 固定填"邮件采集" |
| — | collect_date | 当天日期 |
| — | content_hash | sha256去重哈希 |

## 前置条件

### 1. 数据库加字段
如果 `xhs_sample_library` 表没有 `source_url` 字段：
```sql
ALTER TABLE xhs_sample_library 
ADD COLUMN source_url varchar(500) DEFAULT NULL COMMENT '笔记原始链接' AFTER url;
```

### 2. IMAP配置
QQ邮箱需开启IMAP服务，使用授权码登录（非密码）。
配置信息：
- IMAP_HOST: imap.qq.com
- IMAP_PORT: 993
- 授权码: aovykowpeghibgje

### 3. Python依赖
```bash
pip install pymysql
```

## 完整流程

### 1. 收信
```python
import imaplib, email
mail = imaplib.IMAP4_SSL('imap.qq.com', 993)
mail.login('76835298@qq.com', '授权码')
mail.select('INBOX')
# 搜两种主题格式
status, msgs = mail.search(None, '(OR SUBJECT "[XHS_DATA]" SUBJECT "每日内容采集数据入库")')
```

### 2. 解析邮件（正文 + 附件）
**关键：必须同时处理正文和附件！**
```python
records = []

# 提取正文
body_text = ""
if msg.is_multipart():
    for part in msg.walk():
        ct = part.get_content_type()
        payload = part.get_payload(decode=True)
        if payload:
            decoded = payload.decode("utf-8", errors="replace")
            if ct == "text/plain":
                body_text = decoded
                break
            elif ct == "text/html" and not body_text:
                body_text = decoded

# 提取附件
for part in msg.walk():
    fn = part.get_filename()
    if fn and (fn.endswith(".txt") or "content_fetch" in fn):
        payload = part.get_payload(decode=True)
        if payload:
            data = json.loads(payload.decode("utf-8", errors="replace"))
            # 处理包装结构：data["samples"] 是数组
            for sample_group in data.get("samples", []):
                sample_type = sample_group.get("sample_type", "小红书")
                for item in sample_group.get("items", []):
                    item["sample_type"] = sample_type
                    records.append(item)
```

- 先尝试正文提取JSON（支持 ```json 代码块、纯JSON数组、单行JSON对象）
- 再提取附件TXT（新格式）
- 附件里的JSON是**嵌套结构**：`{"samples": [{"sample_type":"...", "items":[...]}]}`
- 需将 `items` 展开，每条记录补上 `sample_type` 字段

### 3. 去重入库
- 用 `content_hash`（sha256(title|source_url|url)[:32]）去重
- INSERT到 `xhs_sample_library` 表
- 统计新增/跳过条数

### 4. 调度
cron定时，每天凌晨1:10执行（给小墨留10分钟发件时间）：
```cron
10 1 * * * cd /path/to/scripts && python3 imap_xhs_poller.py >> /path/to/logs/imap_cron.log 2>&1
```

## 脚本位置
- 主脚本: `/home/ubuntu/mojiajun/scripts/imap_xhs_poller.py`
- 日志: `/home/ubuntu/mojiajun/logs/imap_xhs_poller.log`
- 状态: `/home/ubuntu/mojiajun/status/imap_xhs_poller.json`

## 重要坑点

1. **QQ邮箱授权码** — 不是QQ密码，需在QQ邮箱设置→账户→生成授权码。多人共用同一邮箱时，授权码变化需同步更新。
2. **IMAP端口** — QQ邮箱IMAP SSL端口是993，不是143。
3. **HTML vs 纯文本** — 邮件可能只有HTML正文，需要从HTML中提取纯文本再解析JSON。
4. **字段对齐** — 小墨的邮件字段和DB字段名称可能不同（如 `collects` → `favorites`），每次改字段需两边同步确认。
5. **去重** — 用 `content_hash` 比用 title+url 更可靠，但哈希算法变了会重新入库重复数据。
6. **⚠️ 附件数据 — 最关键坑点** 2026-05-07起小墨改为用附件TXT发送数据。脚本必须处理附件（`application/octet-stream` 或 `text/plain` 类型的附件），不能只看正文。附件JSON有**两层包装**：`{"samples": [{"sample_type":"...", "items":[...]}]}` — 需展开items并注入sample_type。
7. **⚠️ 主题格式不确定** — 小墨可能用 `[XHS_DATA]` 或 `每日内容采集数据入库 - ` 两种主题格式。搜信用 `OR` 组合两条件。如果用 `SINCE` 日期过滤搜不到，试试 `OR SUBJECT "A" SUBJECT "B"` 语法（QQ邮箱IMAP的SINCE有时不兼容中文日期）。
8. **邮件正文可能是空的** — 如果数据在附件里，`text/plain` 和 `text/html` 正文可能都是空的，不要因此跳过邮件。

## 调试技巧
### 快速检查今天有没有收到邮件
```python
mail.search(None, 'ALL')  # 扫所有邮件（不依赖主题关键词）
all_ids = msgs[0].split()
recent = all_ids[-5:]  # 最近5封
for mid in recent:
    # 查看主题和发件人
```

### 检查邮件结构（附件是否在）
```python
for part in msg.walk():
    fn = part.get_filename()
    ct = part.get_content_type()
    payload = part.get_payload(decode=True)
    print(f"  Part: ct={ct}, filename={fn}, payload_len={len(payload) if payload else 0}")
```

### 检查数据库入库结果
```sql
SELECT sample_type, COUNT(*) as cnt 
FROM xhs_sample_library 
WHERE collect_date = CURDATE() 
GROUP BY sample_type;
```

## 测试方法
收到邮件后检查日志确认入库结果。
- 查看日志: `cat /home/ubuntu/mojiajun/logs/imap_xhs_poller.log`
- 查看状态: `cat /home/ubuntu/mojiajun/status/imap_xhs_poller.json`
