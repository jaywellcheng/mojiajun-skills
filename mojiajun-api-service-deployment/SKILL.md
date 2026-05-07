---
name: mojiajun-api-service-deployment
description: 将墨家军能力打包为 Flask REST API 的部署模式。含服务器端口排查、Flask骨架、子进程并行开发、cron定时任务。适用于任何"把Agent模块抽成API卖钱"的场景。
---

# 墨家军 API 服务部署模式

## 适用范围

把墨家军现有 Agent 模块（笔记生成、内容审核、数据分析等）打包为 REST API，对外提供服务。

## 端口开通三步排查

腾讯云轻量服务器有**两层防火墙**——安全组（云控制台）和 iptables/UFW（服务器本地）。端口不通时必须两层都查。

```
第1层：腾讯云安全组（网页控制台 → 防火墙 → 添加规则）
      ← 这一层在 iptables 之前！安全组没开，本地 iptables 开放也没用
第2层：iptables（服务器本地）
      iptables -L INPUT -n --line-numbers
      注意 YJ-FIREWALL-INPUT 链（腾讯云盾自动管理的黑名单IP）
第3层：UFW
      ufw status / ufw allow PORT
```

**排查顺序（实际验证过的）**：
```bash
# 1. 先确认服务在跑
curl localhost:PORT/api/health

# 2. 确认绑定到 0.0.0.0（不是 127.0.0.1）
ss -tlnp | grep PORT

# 3. 检查 iptables 是否有显式 ACCEPT 规则
iptables -L INPUT -n --line-numbers | grep -E "ACCEPT.*dpt:PORT"

# 4. 检查 UFW
ufw status | grep PORT

# 5. 如果以上全通但外部访问超时 → 100%是安全组问题
#    必须登录腾讯云控制台操作，没有命令行解法
```

**快速方案：复用已有 iptables ACCEPT 规则的端口**，只开一层安全组：

```bash
# 先找哪些端口有显式 iptables ACCEPT（说明这些端口曾被开通过）
iptables -L INPUT -n | grep ACCEPT | grep dpt
# 再确认端口空闲
ss -tlnp | grep PORT
```

已验证端口状态：
- 8890: iptables 有 ACCEPT 规则，安全组需控制台开启
- 8765: iptables ACCEPT + 安全组已开（Hermes Gateway）
- 22, 80, 8088: 可用
- **教训**：9700 端口我们试了→服务跑起来了→iptables/UFW都开了→外部不通→结论：安全组默认只放行22/80/443等常见端口，新端口必须去控制台开

## Flask API 骨架结构

```
~/mojiajun-queue/xhs_api/
├── app.py          # Flask 主应用（路由注册 + 认证）
├── auth.py         # API Key 装饰器
├── audit.py        # 产品模块A
├── reverse.py      # 产品模块B
├── monitor.py      # 产品模块C
└── daily_runner.py # 独立运行脚本（给 cron 用）
```

### app.py 模板

```python
from flask import Flask, jsonify, request
from auth import require_api_key

app = Flask(__name__)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "xhs_api", "version": "0.1.0"})

@app.route("/api/xxx", methods=["POST"])
@require_api_key
def xxx():
    data = request.get_json()
    if not data or "field" not in data:
        return jsonify({"status": "error", "message": "缺少 field 参数"}), 400
    result = some_module.do_work(data["field"])
    return jsonify({"status": "ok", "service": "xxx", "result": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8890, debug=False)
```

### auth.py

```python
from functools import wraps
from flask import request, jsonify

API_KEY = "xhs_mojiajun_2026"

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not key:
            return jsonify({"status": "error", "message": "Missing X-API-Key header"}), 401
        if key != API_KEY:
            return jsonify({"status": "error", "message": "Invalid API Key"}), 401
        return f(*args, **kwargs)
    return decorated
```

## 子进程并行开发模式

复杂项目用 `delegate_task(tasks=[...])` 并行派发：

- 互不依赖的模块 → 同一批并行（最多3个）
- 有依赖的 → 串行：先骨架 → 再产品模块
- context 必须自包含（子进程不知道对话历史）
- 每个子进程负责一个模块的创建+测试+验证

## 服务保活

```bash
# 手动启动
cd ~/mojiajun-queue/xhs_api && nohup python3 app.py > /tmp/xhs_api.log 2>&1 &

# 重启
kill $(lsof -ti:8890) 2>/dev/null
cd ~/mojiajun-queue/xhs_api && nohup python3 app.py > /tmp/xhs_api.log 2>&1 &

# 开机自启（crontab）
@reboot cd /home/ubuntu/mojiajun-queue/xhs_api && nohup python3 app.py > /tmp/xhs_api.log 2>&1 &

# 定时任务
0 9 * * * cd /home/ubuntu/mojiajun-queue/xhs_api && python3 daily_runner.py >> /tmp/monitor_daily.log 2>&1
```

## 常见踩坑

1. **端口不通**：先 curl localhost 确认服务在跑，再按"安全组→iptables→UFW"顺序排查
2. **安全组是独立层**：新端口必须去腾讯云控制台开，命令行改不了安全组。我们试了9700端口→两层防火墙全开→外部仍不通→就是安全组没放行
3. **子进程改了 app.py 后 Flask 没生效**：生产模式 Flask 不自动 reload。必须 `kill $(lsof -ti:PORT)` 再重启
4. **DeepSeek Key 读不到**：`os.getenv()` 从 crontab 启动时可能读不到 .env，需手动读取
5. **模块导入失败**：确认 PYTHONPATH 或使用绝对 import
6. **邮件发送**：QQ 邮箱 SMTP smtp.qq.com:587，授权码不是密码
7. **Swap 打满**：部署前检查 `free -h`。如果 swap>80%：
   - 先 `docker stop prometheus grafana` 等非核心容器
   - 再 `swapoff -a && swapon /swap.img` 刷新 swap
   - 可用内存会暂时下降（换出页面回到RAM），swap 使用量重置
