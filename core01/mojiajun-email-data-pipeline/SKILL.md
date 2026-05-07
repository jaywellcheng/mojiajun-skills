---
name: mojiajun-email-data-pipeline
description: 小墨(Coze)→邮件(QQ邮箱)→CORE-01 cron轮询→JSON解析→MySQL入库。用于小红书数据采集的接收端管道。
category: mojiajun
tags: [email, imap, data-pipeline, xiaohongshu, cron]
---

# 邮件数据管道 — 小墨→小云入库

## 一句话
小墨在Coze平台采集小红书数据→发邮件到76835298@qq.com→CORE-01每10分钟IMAP轮询→解析JSON→入库xhs_sample_library。

## 架构
```
小墨(Coze) → 发送邮件 [XHS_DATA] → QQ邮箱
                                          ↓
                              CORE-01 cron(每10分钟)
                               email_poller.py
                                          ↓
                               xhs_sample_library
```

## 邮件规范
- **收件人**: 76835298@qq.com
- **主题**: 必须含 `[XHS_DATA]`
- **正文**: 纯文本JSON

```json
{
  "task_type": "comic_competitor|women_hotspot|jdz_traffic",
  "search_keyword": "搜索词",
  "items": [{
    "title": "标题", "content": "正文/摘要",
    "source_url": "原始链接", "author": "作者",
    "likes": 1234, "collects": 567, "comments": 89,
    "followers": 10000
  }]
}
```

## 部署要点

### QQ邮箱IMAP
- 服务器: imap.qq.com:993
- 用户: 76835298@qq.com
- 密码: QQ邮箱授权码(非QQ密码)
- 必须先在QQ邮箱网页版开启IMAP/SMTP服务

### cron配置
```
*/10 * * * * python3 /home/ubuntu/mojiajun-queue/agent_outputs/moyuan/email_poller.py >> /tmp/email_poller.log 2>&1
```

## 关键文件
- 入库模块: `agent_outputs/mozi/xhs_data_ingest.py`
- 轮询脚本: `agent_outputs/moyuan/email_poller.py`
- 目标表: `xhs_sample_library`

## 踩坑
- QQ邮箱授权码和QQ密码是两回事
- 小墨和小川可能用不同的授权码
- 首次使用需在QQ邮箱网页版手动登录一次激活IMAP
