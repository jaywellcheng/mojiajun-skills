---
name: mojiajun-backup-automation
description: 墨家军自动备份——每次部署前备份小川数据+墨家军资料库，保留7天，macOS/Linux兼容
version: 1.0.0
tags:
  - mojiajun
  - backup
  - automation
---

# 墨家军自动备份

## 使用

```bash
bash /Users/jaywell/Desktop/墨家军资料库/05_模块代码/小川本地/backup_xiaochuan.sh
```

## 备份范围

- 整个墨家军资料库目录（排除备份子目录避免自引用）
- 输出到 `墨家军资料库/备份/xiaochuan_backup_YYYYMMDD_HHMMSS.tar.gz`

## 自动清理

保留最近7天备份，旧备份自动删除（find -mtime +7）

## 恢复

```bash
tar -xzf xiaochuan_backup_YYYYMMDD_HHMMSS.tar.gz -C /Users/jaywell/Desktop/
```

## 位置

- 脚本: `05_模块代码/小川本地/backup_xiaochuan.sh`
- 备份目录: `备份/`
