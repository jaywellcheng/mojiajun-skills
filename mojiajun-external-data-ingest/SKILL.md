---
name: mojiajun-external-data-ingest
description: 外部Agent→CORE-01数据管道：webhook+邮件双通道，小红书热点数据入库。小墨在Coze采集→POST到9600端口→自动入xhs_hotspot_data表。
category: mojiajun
tags: [data-ingest, webhook, email, xiaohongshu, coze, pipeline]
---

# 外部数据接入管道

## 一句话
外部Agent（Coze小墨）采集的数据 → webhook POST → CORE-01仪表盘 → 自动入库

## 架构

```
小墨(Coze) → POST /api/ingest/xhs → dashboard.py → xhs_data_ingest.py → xhs_hotspot_data表
                                     ↑ port 9600
备选: 小墨 → 邮件 [XHS_DATA] → IMAP轮询脚本 → 同入库逻辑
```

## Webhook端点

```
POST http://159.75.12.11:9600/api/ingest/xhs
Content-Type: application/json
```

## JSON格式

```json
{
  "task_type": "comic_competitor | women_hotspot | jdz_traffic",
  "search_keyword": "搜索词",
  "batch_id": "可选批次ID",
  "items": [
    {
      "title": "标题",
      "content": "正文摘要",
      "source_url": "原文链接",
      "author": "作者",
      "likes": 1234,
      "collects": 567,
      "comments": 89,
      "followers": 10000,
      "extra": {"comment_keywords": ["关键词1","关键词2"]}
    }
  ]
}
```

## 数据库表

`xhs_hotspot_data` — 字段：task_type, search_keyword, source_url, title, content, author, likes, collects, comments, followers, extra(JSON), collected_at, batch_id

## 部署文件

- 入库模块: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/xhs_data_ingest.py`
- Webhook路由: 已注入 `dashboard.py` (`/api/ingest/xhs` POST)
- 邮件轮询: `check_email_inbox()` 函数（备选，需配置IMAP_HOST/USER/PASS环境变量）

## 查询

```python
from agent_outputs.mozi.xhs_data_ingest import get_latest, get_stats
get_latest(20, task_type="comic_competitor")  # 最近数据
get_stats()  # 按task_type统计
```

## 邮件轮询（主通道，2026-05-06 启用）

Webhook被腾讯云安全组拦截 → 切邮件通道。

```
小墨(Coze) → 发邮件到 76835298@qq.com
             主题: [XHS_DATA]
             正文: JSON
                ↓
CORE-01 cron(每10分钟) → email_poller.py → IMAP收信 → xhs_data_ingest.ingest_batch()
                                                    → xhs_sample_library 表
```

### QQ邮箱IMAP配置
- 服务器: imap.qq.com:993
- 用户: 76835298@qq.com
- 密码: 授权码（不是QQ密码！）
- 授权码存放: `/home/ubuntu/mojiajun-queue/.env` 中 `QQ_MAIL_PASS=xxx`

### 轮询脚本
- 位置: `/home/ubuntu/mojiajun-queue/agent_outputs/moyuan/email_poller.py`
- Cron: `*/10 * * * * python3 /home/ubuntu/mojiajun-queue/agent_outputs/moyuan/email_poller.py >> /tmp/email_poller.log 2>&1`

### 字段映射（小墨邮件JSON → xhs_sample_library）
| 邮件字段 | DB字段 |
|----------|--------|
| title | title |
| content | content |
| source_url | source_url（2026-05-06新增） |
| url | url（2026-05-06新增） |
| author | author |
| likes | likes |
| collects | collects |
| comments | comments |
| followers | author_fans |
| task_type | sample_type |
| - | image_style（风格标签） |

### 踩坑
- QQ邮箱授权码：小云和小川拿到的是不同的授权码（`aovykowpeghibgje` 有效，`RLfHppw6cjR9DQmJ` 无效）。原因：每个设备/应用申请的授权码可能不同。
- IMAP登录失败排查：先确认QQ邮箱网页版→设置→账户→IMAP/SMTP服务→已开启
