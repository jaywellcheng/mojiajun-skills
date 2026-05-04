---
name: multi-engine-parallel-fallback
description: 多引擎并行提交+熔断器+自动回退——同时用多个AI生成引擎提交同任务，取最先成功的结果，引擎失败时自动切换
category: mojiajun
tags: [api, fallback, circuit-breaker, parallel, reliability]
---

# Multi-Engine Parallel Submission + Circuit Breaker + Auto-Fallback

## 背景

墨家军有多个AI引擎（MJ/TT API, Crun.AI/GPT Image 2, Fal.ai/FLUX, SiliconFlow, Photoroom），但单个引擎可能失败（配额不足、模型下线、网络超时）。需要一个统一调度层，同时提交到多个引擎，取最先完成的，失败时自动切换。

## 核心架构

```
                      ┌─────────────┐
                      │ Smart Engine │
                      │   Selector   │
                      └──────┬──────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐
        │  Engine 1 │  │  Engine 2 │  │  Engine 3 │
        │  (MJ)     │  │  (GPT2)   │  │  (FLUX)   │
        └─────┬────┘  └─────┬────┘  └─────┬────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                      ┌──────▼──────┐
                      │ Circuit     │
                      │ Breaker     │
                      └─────────────┘
```

## 组件详解

### 1. 智能引擎选择器 (`smart_engine.py`)

根据任务类型选择最佳引擎：

```python
ENGINE_MAP = {
    "high_quality": ["gpt_image_2", "midjourney", "flux_schnell"],
    "fast": ["flux_schnell", "kolors"],
    "portrait": ["ideogram_character", "midjourney"],
    "background_remove": ["photoroom"],
    "video": ["kling", "minimax"],
}
```

### 2. 熔断器 (`circuit_breaker.py`)

每个引擎独立维护状态，连续失败N次后熔断，冷却后自动恢复：

```python
class CircuitBreakerState(Enum):
    CLOSED = "closed"        # 正常运行
    OPEN = "open"            # 已熔断，拒绝请求
    HALF_OPEN = "half_open"  # 冷却中，允许试探请求

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self, engine_name):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            log(f"[⚠️] {engine_name} circuit OPEN (failed {self.failure_count}x)")

    def allow_request(self, engine_name):
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return True  # 试探请求
            return False  # 拒绝
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
```

### 3. 自动回退引擎 (`fallback_engine.py`)

顺序尝试引擎列表，第一个成功的返回：

```python
ENGINE_PRIORITY = {
    "image_gen": [
        ("gpt_image_2", call_crun_gpt2),     # P0: 质量最高
        ("midjourney", call_tt_mj),           # P1: 快速出图
        ("flux_schnell", call_fal_flux),      # P2: 极速备选
        ("kolors", call_siliconflow),         # P3: 最后的备选
    ],
    "portrait": [
        ("ideogram_character", call_fal_ideogram),  # P0: 人脸一致性最好
        ("midjourney_cref", call_tt_mj_cref),       # P1: 备选但人脸不保准
        ("gpt_image_2", call_crun_gpt2),            # P2: 最后备选
    ],
    "video": [
        ("kling", call_kling),              # 只有Kling
    ],
    "background_remove": [
        ("photoroom", call_photoroom),      # 只有Photoroom
    ],
}
```

### 4. 代价监控 (`cost_monitor.py`)

记录每次调用的费用，今天API总消耗一目了然：

```python
TODAY_COST_TABLE = {
    "midjourney":   {"calls": N, "cost": f"${N*0.035:.2f}"},
    "gpt_image_2":  {"calls": N, "cost": f"${N*0.02:.2f}"},
    "flux_schnell": {"calls": N, "cost": f"${N*0.001:.4f}"},
    "ideogram":     {"calls": N, "cost": f"${N*0.018:.2f}"},
    "photoroom":    {"calls": N, "cost": f"${N*0.01:.2f}"},
    "total":        {"calls": ∑, "cost": "$X.XX"},
}
```

## 目录结构

```
agent_outputs/moyuan/api_toolkit/
├── smart_engine.py       # 引擎选择策略
├── circuit_breaker.py    # 熔断器
├── fallback_engine.py    # 自动回退
├── cost_monitor.py       # 代价监控
├── plugin_system.py      # 热插拔插件系统 + MetricsCollector
├── config_manager.py     # 分层配置管理
├── permissions.py        # 按Agent权限控制
└── priority_queue.py     # 5级优先级队列
```

## 完整调用流程

```python
def generate_with_fallback(task_type, args):
    """带熔断器+自动回退的图片生成"""
    engine_list = ENGINE_PRIORITY.get(task_type, [])
    
    for engine_name, engine_fn in engine_list:
        if not circuit_breaker.allow_request(engine_name):
            continue  # 此引擎已熔断，跳过
            
        try:
            result = engine_fn(args)
            circuit_breaker.record_success()
            cost_monitor.record(engine_name, result.get("cost", 0))
            return result
        except Exception as e:
            circuit_breaker.record_failure(engine_name)
            log(f"[⚠️] {engine_name} failed: {e}")
            continue  # 尝试下一个引擎
    
    raise Exception("All engines failed")
```

## 注册到module_dispatcher

在 `module_dispatcher.py` 中新增4种task_type：

```python
DISPATCHER_MAP = {
    # ... 原有的 ...
    "breaker_stats": lambda payload: breaker_stats(),           # 熔断器状态
    "plugin_list":   lambda payload: list_plugins(),            # 插件列表
    "metrics_report": lambda payload: metrics_report(),         # 指标报告
    "config_get":    lambda payload: get_config_value(payload), # 配置查询
}
```

## 查询熔断器状态

```python
def breaker_stats():
    """返回各引擎的熔断状态"""
    stats = {}
    for engine_name, breaker in circuit_breakers.items():
        stats[engine_name] = {
            "state": breaker.state.value,
            "failures": breaker.failure_count,
            "last_failure": datetime.fromtimestamp(breaker.last_failure_time).isoformat() if breaker.last_failure_time else None,
            "recovery_in": max(0, breaker.recovery_timeout - (time.time() - breaker.last_failure_time)) if breaker.last_failure_time and breaker.state == CircuitBreakerState.OPEN else 0,
        }
    return json.dumps(stats, ensure_ascii=False)
```

## 部署验证

1. 在CORE-01上创建所有文件
2. 在 `module_dispatcher.py` 注册新增task_type
3. 重启worker: `systemctl restart agent-worker`
4. 通过task_queue提交测试任务
5. 验证：故意让一个引擎失败，检查自动切换到下一个

## 已知限制

- Kling AI: access_key未启用，需要用户去klingai.com开通
- SiliconFlow: FLUX/SD模型已下架，只有kolors能用
- 无GPU: ComfyUI + IPAdapter推迟部署
