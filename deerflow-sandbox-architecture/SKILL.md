---
name: deerflow-sandbox-architecture
description: DeerFlow 2.0 Sandbox沙箱架构设计精华——三层抽象+DIP/SRP+生命周期管理，墨家军架构参考
category: mojiajun
tags: [deerflow, sandbox, architecture, dip, srp, 架构思维]
created: 2026-05-09
author: 小川
---

# DeerFlow 2.0 Sandbox 架构精华

> 来源：尼恩《Harness架构与源码学习圣经》第九章，字节跳动DeerFlow 2.0

## 核心架构思维

### DIP 依赖倒置原则
上层依赖抽象接口，不依赖具体实现。SandboxMiddleware→Sandbox接口←LocalSandbox/DockerSandbox/K8sSandbox。
价值：切换底层实现无需改上层代码，配置即切换。

### SRP 单一职责原则
三层各司其职：
- **SandboxMiddleware**：生命周期管理（创建/复用/销毁），绑定Agent执行流程
- **SandboxProvider**：实例工厂+池化管理（acquire/get/release）
- **Sandbox**：操作接口契约（execute_command/read_file/write_file/search）

## 三层抽象架构

```
SandboxMiddleware (生命周期)
    ↓ 依赖
SandboxProvider (工厂+池)
    ↓ 依赖
Sandbox (操作接口)
    ↑ 实现
LocalSandbox / DockerSandbox / K8sSandbox
```

### 中间件层：生命周期三阶段闭环
1. **获取**：懒加载（默认，初次调用才创建）或饿加载（before_agent提前创建）
2. **注入**：sandbox_id写入runtime.state（持久化）+ runtime.context（快速引用）
3. **释放**：after_agent归还资源。Local=空操作，Docker=放回热池，K8s=标记可复用

### Provider层：三种实现
| Provider | 隔离级别 | 启动速度 | 适用场景 |
|----------|---------|---------|---------|
| LocalSandbox | 无隔离 | 毫秒级 | 本地开发调试 |
| aio-sandbox(Docker) | Namespace+Cgroups | 热池小于1秒 | 单机生产 |
| aio-sandbox(K8s) | Pod级隔离 | 容器冷启动5-10秒 | 多租户/高可用 |

### 确定性ID生成（跨进程复用）
sandbox_id = SHA256(thread_id)[:8]
多进程不共享状态，同thread_id映射同sandbox_id，复用同一容器。

### 热池设计
用完放回热池，空闲600秒自动回收。三层获取策略：内存缓存(最快)→热池复用→后端创建(最慢)。

## /mnt/ 命名哲学——对齐LLM认知

- Linux惯例：/mnt/=外部挂载点，LLM训练数据中已内化此语义
- Agent看到 /mnt/user-data/ 会理解成"持久外部存储"，减少误操作
- 三个子目录：uploads/ (只读), workspace/ (读写), outputs/ (读写)
- 另有 /mnt/skills/ 挂载技能脚本
- Claude的Mount drive也用同样命名惯例

## 路径映射：虚拟↔物理双向转换

LocalSandbox核心挑战是虚拟路径与物理路径不一致。
- 正向解析：虚拟→物理，命令执行用
- 反向解析：物理→虚拟，命令输出回译给Agent保持上下文一致
- 最长前缀匹配：更具体映射优先

## 五大标准沙箱工具

| 工具 | 功能 |
|------|------|
| bash | 命令执行（高危命令自动拦截） |
| ls | 目录浏览 |
| read | 文件读取 |
| write | 文件写入 |
| glob/grep | 文件搜索 |

## 对墨家军的参考价值

1. /mnt/命名：设计Agent工具路径时对齐LLM认知惯例
2. 懒加载：Worker工具按需初始化，不用不创建
3. 三层抽象：与module_dispatcher模式一致，可借鉴更干净的分层
4. 生命周期闭环：获取→注入→释放三阶段，防止资源泄漏
5. 配置驱动切换：provider通过config切换，不改代码

**现阶段不落地**：墨家军单环境运行，不需要Docker/K8s级沙箱隔离。待多租户/不可信代码执行场景再启用。
