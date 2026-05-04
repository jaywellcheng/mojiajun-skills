---
name: mojiajun-disaster-recovery-modules
description: 小川双活容灾全部5个核心模块——disaster_recovery_sync、compact、heartbeat_monitor、takeover、heartbeat_client，含systemd部署、DB踩坑和端到端验证
version: 2.0.0
tags: [mojiajun, disaster-recovery, memory-sync, compact, 容灾, heartbeat, takeover, systemd]
---

# 小川双活容灾 — 全部核心模块

## 概述

容灾计划 Phase 1 的五个模块，分层架构：

```
Layer 2: Hermes Agent (小川2号) — 接管后的智能指挥
Layer 1: systemd + Python (独立运行) — 心跳检测+自动接管，不依赖Agent框架
```

| 模块 | 文件 | 行数 | 部署位置 | 触发方式 |
|------|------|------|---------|---------|
| 记忆同步 | `disaster_recovery_sync.py` | ~260 | 双端 | 手动/cron |
| 记忆压缩 | `compact.py` | ~230 | 双端 | 手动 |
| 心跳监控 | `heartbeat_monitor.py` | 332 | CORE-01 | systemd timer 每30s |
| 自动接管 | `takeover.py` | 460 | CORE-01 | heartbeat_monitor触发 |
| 心跳上报 | `heartbeat_client.py` | 131 | Mac本地 | crontab 每30s |

---

## 一、disaster_recovery_sync.py

### 五大命令

| 命令 | 用途 | 场景 |
|------|------|------|
| `push` | 本地→CORE-01 推送 | 定时同步（crontab每5分钟） |
| `pull` | CORE-01→本地 拉取 | Mac恢复后拉回最新记忆 |
| `sync` | 双向同步（先pull再push） | 常规维护 |
| `force` | 强制同步（跳过冲突检查） | 接管前强制对齐 |
| `status` | 查看同步状态 | 巡检 |

### 核心设计

- **SHA256增量检测**：只传输变更文件
- **rsync传输**：复用系统rsync，增量+断点续传
- **冲突解决**：Last-Write-Wins + 旧版存conflicts/目录
- **安全排除**：自动排除 credentials.json / .DS_Store / *.log
- **双环境自适应**：自动检测local_mac或core01，切换路径和远程目标

### 部署验证

```bash
python3 ~/.hermes/scripts/disaster_recovery_sync.py status
python3 ~/.hermes/scripts/disaster_recovery_sync.py push
ssh ubuntu@159.75.12.11 "python3 /home/ubuntu/scripts/disaster_recovery_sync.py status"
```

---

## 二、compact.py

### 四层压缩策略

| 层级 | 处理 | 触发条件 |
|------|------|---------|
| 保留区 | 绝不压缩 | 含关键词（大威/小川/CORE-01/密码/关键决策等） |
| 摘要区 | 保留原样 | 重要性评分≥5的行 |
| 折叠区 | 整段折叠为一行摘要 | 章节标题+低重要性内容 |
| 删除区 | 跳过 | 纯日志时间戳行、重复分隔线 |

### 命令

```bash
python3 compact.py compress                    # 压缩全部
python3 compact.py compress --file MEMORY.md   # 压缩指定文件
python3 compact.py status                      # 查看状态
python3 compact.py stats                       # 压缩比统计
```

---

## 三、heartbeat_monitor.py（CORE-01）

### 功能

由 systemd timer 每30秒触发一次，单次执行即退出（无内部循环）：

1. 更新 xiaochuan2 心跳：`UPDATE agent_status SET last_heartbeat=NOW(), status='standby'`
2. 检查 xiaochuan 是否存活：查询 `last_heartbeat`，超过90秒阈值则判定离线
3. 若离线 → 调用 `subprocess.run(['python3', '/home/ubuntu/scripts/takeover.py'])`
4. takeover 成功后 → `UPDATE agent_status SET status='offline' WHERE agent_id='xiaochuan'`（防止重复触发）
5. 全部日志写入 `/home/ubuntu/logs/heartbeat_monitor.log`

### systemd 配置

**Service** (`/etc/systemd/system/xiaochuan2-heartbeat.service`):
```ini
[Unit]
Description=Xiaochuan2 Heartbeat Monitor
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/ubuntu/scripts/heartbeat_monitor.py
User=ubuntu
Group=ubuntu
StandardOutput=journal
StandardError=journal
```

**Timer** (`/etc/systemd/system/xiaochuan2-heartbeat.timer`):
```ini
[Unit]
Description=Trigger Xiaochuan2 Heartbeat every 30s
Requires=xiaochuan2-heartbeat.service

[Timer]
OnBootSec=10
OnUnitActiveSec=30
AccuracySec=1
Unit=xiaochuan2-heartbeat.service

[Install]
WantedBy=timers.target
```

### 启用

```bash
sudo systemctl daemon-reload
sudo systemctl enable xiaochuan2-heartbeat.timer
sudo systemctl start xiaochuan2-heartbeat.timer
```

### 验证

```bash
systemctl status xiaochuan2-heartbeat.timer
journalctl -u xiaochuan2-heartbeat.service --since '2 min ago'
tail -20 /home/ubuntu/logs/heartbeat_monitor.log
```

---

## 四、takeover.py（CORE-01）

### 功能

由 heartbeat_monitor.py 触发，五步接管流程：

| 步骤 | 操作 | 幂等保障 |
|------|------|---------|
| 1 | 获取分布式锁 `commander_lock`（TTL=120s） | `INSERT ... ON DUPLICATE KEY UPDATE` + `IF(expires_at < NOW())` |
| 2 | 双重检查 xiaochuan 是否真的下线 | 锁内再查一次 |
| 3 | `UPDATE tasks SET claimed_by='xiaochuan2' WHERE claimed_by='xiaochuan' AND status IN ('pending','running')` | 首次后全部变为 xiaochuan2，后续影响0行 |
| 4 | `UPDATE agent_status SET status='online' WHERE agent_id='xiaochuan2'` | 幂等 |
| 5 | 尝试 `disaster_recovery_sync.py pull`（失败不阻塞） | subprocess 60s超时 |

### 分布式锁设计

```sql
INSERT INTO distributed_locks (lock_name, holder, acquired_at, expires_at)
VALUES ('commander_lock', 'xiaochuan2', NOW(), DATE_ADD(NOW(), INTERVAL 120 SECOND))
ON DUPLICATE KEY UPDATE
    holder = IF(expires_at < NOW(), VALUES(holder), holder),
    expires_at = IF(expires_at < NOW(), VALUES(expires_at), expires_at);
```

- 锁过期后自动释放（TTL=120秒），防止死锁
- 同一时刻只有一个进程持有锁
- 获取失败直接 exit 0（不报错）

### 日志

`/home/ubuntu/logs/takeover.log` — 每次接管完整记录

---

## 五、heartbeat_client.py（Mac本地）

### 功能

Mac端心跳上报客户端，每30秒执行一次，**通过 SSH 远程执行 MySQL 命令**（零 Python 依赖，不需要 pymysql 或 SSH 隧道）：

```python
# 核心模式：ssh → mysql 远程执行
ssh -o ConnectTimeout=10 -o BatchMode=yes ubuntu@159.75.12.11 \
  'mysql -h 127.0.0.1 -u xiaochuan -pxiaochuan_2026_mjj mojiajun \
   -e "UPDATE agent_status SET last_heartbeat=NOW(), status=\"online\" WHERE agent_id=\"xiaochuan\""'
```

### ⚠️ v1 失败教训（务必跳过）

v1 尝试了两种方案，**均在生产失败**：

| 方案 | 失败原因 |
|------|---------|
| pymysql 直连 `159.75.12.11:3306` | 防火墙阻挡 MySQL 端口（安全策略正确） |
| pymysql 连接 `127.0.0.1:3307`（SSH 隧道） | 需要预先建立持久隧道，crontab 环境无法维持 |

**v2 方案（SSH 远程执行）是唯一可靠方案**：
- 不需要开放 MySQL 端口
- 不需要持久 SSH 隧道
- 不需要安装 pymysql
- 每次执行都是独立的 SSH 连接，用完即断
- 和 `ssh ubuntu@... 'mysql -e "..."'` 手动查库模式完全一致

### Mac 端 crontab 配置

```bash
crontab -e
# 添加（每30秒一次，用 sleep 实现）：
* * * * * python3 ~/.hermes/scripts/heartbeat_client.py
* * * * * sleep 30 && python3 ~/.hermes/scripts/heartbeat_client.py
```

### 日志

`~/.hermes/logs/heartbeat_client.log`

---

## 六、CORE-01 部署路径（完整）

```
/home/ubuntu/scripts/
├── disaster_recovery_sync.py    # 记忆同步（260行）
├── compact.py                   # 记忆压缩（230行）
├── heartbeat_monitor.py         # 心跳监控（332行）★新增
├── takeover.py                  # 自动接管（460行）★新增
├── disk_monitor.sh              # 磁盘监控（已有）
├── mysql_backup.sh              # 数据库备份（已有）
└── xhs_sync.sh                  # 小红书同步（已有）

/home/ubuntu/.claude.server/     # 服务器端记忆目录
├── MEMORY.md                    # (从Mac同步过来)
├── MEMORY.md.compact.md         # (compact生成)
└── sync_state.json              # (同步状态)

/etc/systemd/system/
├── xiaochuan2-heartbeat.service # ★新增
└── xiaochuan2-heartbeat.timer   # ★新增

/home/ubuntu/logs/
├── heartbeat_monitor.log        # ★新增
└── takeover.log                 # ★新增
```

---

## 七、踩坑记录（重要！）

### 1. DB schema ≠ 计划书假设

| 计划书假设 | 实际 | 处理 |
|-----------|------|------|
| tasks 主键为 `id INT AUTO_INCREMENT` | `task_id VARCHAR(64)` UUID格式 | 不影响，只是查询用 task_id |
| tasks 需要新增 `heartbeat_at` 字段 | 已有 `heartbeat` 字段（ON UPDATE CURRENT_TIMESTAMP） | 不新增，复用现有 |
| 需要新建 `agents` 表 | 已有 `agent_status` 表 | **不新建 agents 表**，直接复用 agent_status |
| agent_status.status ENUM 包含 'standby' | 只有 'online','offline','busy' | **必须先 ALTER TABLE 加 'standby'**，否则 INSERT xiaochuan2 失败 |

### 2. agent_status ENUM 陷阱

```sql
-- 插入前必须检查并修复！
ALTER TABLE agent_status 
MODIFY COLUMN status ENUM('online','offline','busy','standby') 
DEFAULT 'offline';
```

这是部署中最容易踩的坑——计划书假设有 'standby'，实际没有。

### 3. takeover.py 记忆同步失败是预期行为

当 Mac 离线时，`disaster_recovery_sync.py pull` 会因为无法解析 Mac 主机名而失败。
**这不是错误**——takeover.py 设计了 graceful degradation，同步失败不阻塞接管流程。

### 4. systemd timer 优于 while True 循环

- `while True + sleep(30)` 会因脚本崩溃而永久停止
- `systemd timer` 每次都是新进程，崩溃后下次仍会触发
- `Type=oneshot` 确保每次执行完就退出

### 5. 时序竞态：monitor 和 client 不同步

monitor 和 client 各自独立触发，存在5-10秒的时间差：
- monitor 可能恰好在 client 更新心跳前检测（看到旧数据）
- 此时 monitor 的 `UPDATE agent_status SET status='offline'` 返回 `affected=0`（因为 status 已经是 'offline'）
- 几秒后 client 更新心跳 → status 回到 'online'
- **这是无害的**：affected=0 不报错，下一轮 monitor 会正确检测到 online

### 6. 分布式锁的 MySQL 实现

用 `distributed_locks` 表代替 Redis/etcd：
- 优势：零额外依赖，MySQL 已有
- 锁释放：依赖 TTL 过期（`expires_at < NOW()`），无需显式释放
- 抢占：只有过期锁可被抢占，防止活锁

### 7. DeepSeek v4 reasoning_content 陷阱

当 context 过大时，DeepSeek v4 会报错：
```
The `reasoning_content` in the thinking mode must be passed back to the API.
```
**解法**：大任务用 `delegate_task` 子进程处理，避免单个 session 上下文膨胀。

---

## 八、端到端验证

```bash
# 1. 确认 timer 运行
systemctl status xiaochuan2-heartbeat.timer

# 2. 确认心跳更新
mysql -h 127.0.0.1 -u xiaochuan -pxiaochuan_2026_mjj mojiajun \
  -e "SELECT agent_id, agent_name, status, last_heartbeat FROM agent_status WHERE agent_id IN ('xiaochuan','xiaochuan2')"

# 3. 查看监控日志
tail -20 /home/ubuntu/logs/heartbeat_monitor.log

# 4. 查看接管日志（如果有）
tail -20 /home/ubuntu/logs/takeover.log

# 5. 模拟故障测试：停止 Mac 心跳 → 等待90秒 → 检查 takeover 是否触发
```
