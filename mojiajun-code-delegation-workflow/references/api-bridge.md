# API Bridge — 子进程操作CORE-01的标准通道

> 参考文件，配套 `mojiajun-code-delegation-workflow` skill 使用

## 背景

子进程（delegate_task/墨码）没有CORE-01 SSH权限。API Bridge通过HTTP提供安全的任务提交通道。

## 架构

```
子进程 → HTTP POST /api/task → CORE-01:8892 Flask → task_queue (MySQL)
子进程 → HTTP GET /api/task/{id}  ← 轮询拿结果
```

## 快速使用

```python
import requests, time

TOKEN = "mjj_api_bridge_2026"
BASE = "http://CORE-01:8892"

# 提交任务
r = requests.post(f"{BASE}/api/task",
    headers={"X-API-Token": TOKEN},
    json={"task_type": "code_exec", "payload": {"command": "echo hi", "timeout": 30}})
task_id = r.json()["task_id"]

# 轮询结果
for i in range(10):
    time.sleep(3)
    r = requests.get(f"{BASE}/api/task/{task_id}",
        headers={"X-API-Token": TOKEN})
    status = r.json()["status"]
    if status in ("completed", "failed", "timeout"):
        print(r.json())
        break
```

## 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/health | GET | 健康检查 + 队列深度 |
| /api/task | POST | 提任务，body: {task_type, payload} |
| /api/task/{id} | GET | 查结果 |

## 限制

- 仅支持 task_type: code_exec, code_review
- systemd相关操作仍需手动sudo
- 速率限制：每token每秒10次

## 故障排查

```bash
# 检查服务状态
sudo systemctl status api-bridge

# 查看日志
sudo journalctl -u api-bridge -n 20

# 手动测试
curl -s http://127.0.0.1:8892/api/health
```
