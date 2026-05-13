---
name: mojiajun-multi-server-deployment-pitfalls
description: 墨家军运维基础设施全记录——服务器拓扑、SSH隧道(launchd)、API Bridge、fail2ban配置、模型生命周期、部署踩坑
category: mojiajun
---

# 墨家军多服务器部署踩坑全记录

## 服务器拓扑

CORE-01 (159.75.12.11, 腾讯云) — WireGuard wg0 10.100.0.1/24 — MySQL Docker + Flask xhs-api :8890 + 墨家军内部工作流

GW-01 (120.79.167.127, 阿里云) — WireGuard wg0 10.100.0.2/24 — Nginx :80/443 → Flask :8800 + DeepSeek代理 :5001 + 商业网站

本地Mac通过公网 IP 直连服务器（不需要VPN）。**VPN只在访问GitHub等海外资源时才连**——连了VPN后Mac的公网IP会变成北美IP，此时SSH到腾讯云/阿里云服务器会被云安全报警拦截。所以铁律是：**连VPN时不SSH到服务器**。

---

## 坑1：多层SSH引号转义

通过跳板执行命令时，引号层层转义极难调试。

正确做法：复杂脚本先写本地文件，再 cat 传输到目标服务器执行。绝对不要在bash命令行里嵌套Python f-string或多层引号。

---

## 坑2：nohup进程SSH断开即死

ssh server "nohup python3 app.py &" — SSH退出后进程被杀。

正确做法：用 systemd 管理所有服务。Restart=always + RestartSec=3。不要用 nohup/screen/tmux 作为持久化方案。

---

## 坑3：VPN通了但端口不通

GW-01 能 ping 通 CORE-01 VPN IP，但HTTP连不上。原因是iptables INPUT策略DROP，没放行VPN子网。

修复：sudo iptables -I INPUT 1 -s 10.100.0.0/24 -p tcp --dport PORT -j ACCEPT

---

## 坑4：Flask路由写在app.run()后面

Python执行到app.run()就阻塞，后面的@app.route永远不会注册。所有路由必须在app.run()之前。

---

## 坑5：阿里云ICP备案拦截HTTP

未备案域名HTTP请求被阿里云劫持。短期只访问HTTPS，长期完成ICP备案。

---

## 坑6：JS onclick引号冲突静默失败

HTML属性用双引号，JS内部也用双引号导致属性提前闭合。正确做法：用JS函数名代替内联代码。

---

## 坑7：聊天机器人无会话记忆

每次请求独立导致反复问同一问题。修复：前端传session_id，后端JSON存历史，每次带最近10条发给DeepSeek。

---

## 坑8：Flask模板更新不生效

修改 templates/*.html 后 curl 到的仍是旧内容。Flask 在 debug=False 时不会自动重载。重启 Flask（systemctl restart 或 fuser -k + nohup）后生效。验证：curl 后 grep 新内容确认。

## 坑9：CSS overflow:hidden 裁掉绝对定位按钮

聊天窗口关闭按钮用 `position:absolute; top:-12px; right:-12px` 放在对话框外右上角，但父容器有 `overflow:hidden` → 按钮被裁剪只剩一角。修复：`overflow:visible` 或把按钮放在容器内部。

## 坑10：`app.run()` 缩进跑进函数体内

编辑 Flask 代码时 `app.run()` 意外缩进到 `def chat_lead():` 函数内 → 进程启动即退出 → systemd 陷入 auto-restart 循环。确认 `app.run()` 始终在文件顶层（缩进 0）。

## 坑11：fuser -k + cat > file 在同一个SSH管道 → 文件被清空

GW-01 Flask kill后立即在同一个SSH管道里 cat > templates/xxx.html → 文件0字节。

**铁律**：分两步操作，绝不能合并。
```bash
# 第1步：停Flask
ssh server "fuser -k 8800/tcp; sleep 1"

# 第2步：传文件（Flask已停，文件不会被锁）
cat local_file | ssh server "cat > /path/to/file"
wc -c 确认 >0 字节

# 第3步：启Flask
ssh server "cd /path && nohup python3 app.py &"
```

## 坑12：反复sed编辑HTML导致结构崩溃

多次sed inline编辑同一个HTML文件 → div嵌套错乱、class名丢失、section闭合错位。表现为布局全乱、max-width失效、元素跑位。

**正确做法**：复杂修改直接重写整个文件。用 write_file 生成干净版，cat 上传替换。不要修修补补。

## 坑13：AI API Key集中过期

AIMLAPI/PIAPI/ZHIPUAI三个Key同日过期，生图和OCR全挂。
- 生图切 SiliconFlow (Kwai-Kolors/Kolors)，国内直连
- OCR切 Tesseract本地引擎，不依赖外部API
- 备选：OpenRouter中转 → 覆盖所有海外模型

## 坑14：OCR表格列被合并

Tesseract OCR输出中窄列（如全是"1"的列）被合并到旁边。不是代码问题，是OCR精度限制。分辨率高或拍照拉近可缓解。

## 坑15：hosts.deny 里 sshd: ALL 拦截一切 SSH（含自己）

**症状**：从本地 Mac SSH 到服务器报 `Connection refused`，但安全组已放行全部 IPv4:22，从另一台腾讯云内网服务器却能连上。ping 正常，nc 说端口被拒。

**根因**：`/etc/hosts.deny` 里配置了 `sshd: ALL`，TCP Wrappers 在应用层拦截了 SSH 连接。

注意：`hosts.deny` 和 `hosts.allow` 同时存在时，`hosts.allow` 里的白名单规则优先——但如果 `hosts.allow` 没有你的 IP，`hosts.deny` 里的 `sshd: ALL` 会生效。

**诊断方法**：

```bash
# 从能通的机器（如同账号下另一台腾讯云服务器）跳板检查
ssh 跳板机 "cat /etc/hosts.deny"
# → 看到 sshd: ALL 就是它

# 或者从跳板机 nc 测试
ssh 跳板机 "nc -zv 目标服务器 22"
# → 如果跳板机能通但你本地不行，就是防火墙/TCP Wrappers的问题
```

**修复**：

```bash
# 注释掉 sshd: ALL（保留其他规则如 mysqld: ALL 不影响 SSH）
sudo sed -i 's/^sshd: ALL/# sshd: ALL/' /etc/hosts.deny
```

**教训**：
- 配置 hosts.deny 时必须留白名单机制，`sshd: ALL` 会把你自己也锁在外面
- "HERMES Agent System - 默认拒绝规则"（sshd: ALL + ALL: ALL）太激进，不要全盘拒绝
- 安全组 + iptables + TCP Wrappers 是三层不同机制，都要排查
- 从内网另一台服务器做 "跳板测试" 是最快的诊断手段——能通说明是网络层/应用层过滤，不是服务本身问题

## 部署检查清单

- systemd service 创建并 enable，不用 nohup
- 路由全部在 app.run() 之前
- `app.run()` 在文件顶层，缩进 0
- iptables 放行 VPN 子网访问目标端口
- 从对端服务器 curl 测试 VPN IP 可达
- 多 SSH 跳板时不写内联 Python，用 cat 传文件
- 前端 JS 用函数名，不写内联代码
- 聊天类接口有会话记忆机制
- 修改模板后重启 Flask 才生效
- 绝对定位元素检查父容器 overflow
- **停Flask → 传文件 → 验证>0 → 启Flask，三步分开**
- **复杂HTML改动直接重写文件，别sed修补**
- **生图用SiliconFlow，OCR用Tesseract，不依赖过期Key**
- **墨码Agent注册到module_dispatcher：code_execute → mo_code

---

## 关键基础设施（2026-05-13 新增）

### 服务器清单

| 主机名 | IP | 用户 | 用途 |
|:------:|:---:|:----:|:-----|
| CORE-01 | 159.75.12.11 | ubuntu | 聊天API+任务队列+Agent Worker+API Bridge |
| GW-01 | 120.79.167.127 | admin | 商业网站+Flask |
| Mac本地 | — | jaywell | Hermes Agent+CC1脚本 |

> API Bridge 实际在 **159.75.12.11**，不是 120.79.167.127。

### SSH 隧道（launchd 持久化）

API Bridge(:8892)不对外暴露端口，通过 SSH 隧道访问。已用 launchd 做持久化：

```bash
# 检查状态
launchctl list | grep hermes
curl -s http://127.0.0.1:8892/api/health

# 日志
tail -f ~/.hermes/logs/ssh-tunnel.log
```

Plist: `~/Library/LaunchAgents/com.hermes.ssh-tunnel.plist`
- KeepAlive=true（挂了自拉），ThrottleInterval=10s
- dispatch.py 会自动检测隧道状态

### fail2ban 配置（GW-01）

`/etc/fail2ban/jail.local` 的 `[sshd]` 段必须加 ignoreip：
```
ignoreip = 127.0.0.1/8 14.120.46.0/24 159.75.12.11 10.100.0.0/24
```

**SSH 排查顺序**：安全组 → iptables → hosts.deny → fail2ban

### 工具链

| 工具 | Mac本地 | CORE-01 |
|:----|:-------:|:-------:|
| dispatch.py | ✅ `~/.hermes/scripts/` | — |
| cc1.py | ✅ `~/.hermes/scripts/` | — |
| cc2.py | — | ✅ `/home/ubuntu/scripts/` |
| retro.py | ✅ `~/.hermes/scripts/` | ✅ `/home/ubuntu/scripts/`（自动同步） |

### DeepSeek 模型生命周期

| 模型 | 状态 | 备注 |
|:----|:----:|:------|
| deepseek-chat | ❌ 已弃用 | 2026-05-31下线，已全部迁移到 v4-flash |
| deepseek-v4-flash | ✅ 主力快速 | 默认模型 |
| deepseek-v4-pro | ✅ 主力写码 | CC1/CC2 使用 |

所有 `deepseek-chat` 引用已在 2026-05-13 批量替换为 `deepseek-v4-flash`。

### 迭代闭环（retro.py）

L2/L3 任务后强制执行。详见 `xiaochuan-commander-mode` 的 Step 7。核心命令：

```bash
retro.py search <关键词>   # Step 0: 查历史
retro.py start "任务名"     # 开始归档
retro.py add bug/find/lesson/skill/decision <描述>
retro.py report             # 生成+归档+自动同步到CORE-01
retro.py decisions          # 查pending决策
```
