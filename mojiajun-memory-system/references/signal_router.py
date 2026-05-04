#!/usr/bin/env python3
"""
墨家军 TaskSignalExtractor + ModelRouter + RalphGoal
基于小墨补充方案: 信号提取→模型路由→目标导向执行

信号提取器: 不只是 LOW/MEDIUM/HIGH，而是一整套任务画像
模型路由: 复杂度 + 上下文膨胀 + 用户交互模式 三维决策
Ralph目标: 目标导向 vs 步骤导向，"直到X才停止"
"""

import re, json, os
from dataclasses import dataclass, field
from typing import Optional, Callable


# ═══════════════════════════════════════════════════
#  TaskSignalExtractor — 任务画像提取器
# ═══════════════════════════════════════════════════
@dataclass
class TaskProfile:
    """任务画像：不只是复杂度，而是一整套决策依据"""
    # 复杂度
    complexity: str = "medium"        # low / medium / high
    word_count: int = 0
    file_count: int = 0
    estimated_subtasks: int = 1
    
    # 质量要求
    requires_review: bool = False
    requires_test: bool = False
    requires_security_scan: bool = False
    
    # 风险
    is_refactor: bool = False
    affects_production: bool = False
    affects_database: bool = False
    
    # 执行策略
    is_research: bool = False         # 需要探索性工作
    is_iterative: bool = False        # 需要多轮迭代
    is_batch: bool = False            # 可并行处理
    suggested_model: str = "chat"     # flash / chat / reasoner
    suggested_mode: str = "direct"    # direct / ralph / agentic_map
    
    # 上下文
    context_tokens: int = 0
    context_pressure: str = "normal"  # normal / high / critical


class TaskSignalExtractor:
    """从任务描述中提取信号，生成任务画像"""
    
    # ── 关键词映射 ──
    COMPLEXITY_HIGH = [
        "架构", "重构", "debug", "race condition", "死锁", "性能优化",
        "从零开始", "重新设计", "多模块", "跨系统", "architecture", "refactor",
    ]
    COMPLEXITY_LOW = [
        "查看", "读取", "查询", "列表", "统计", "简单", "quick",
        "read", "list", "check", "status",
    ]
    
    REVIEW_KEYWORDS = ["发布", "上线", "生产", "prod", "deploy", "merge", "PR"]
    TEST_KEYWORDS = ["测试", "test", "验证", "verify", "TDD"]
    RESEARCH_KEYWORDS = ["调研", "研究", "探索", "分析", "research", "explore", "调查"]
    ITERATIVE_KEYWORDS = ["直到", "until", "不断", "持续", "循环", "反复", "一直"]
    BATCH_KEYWORDS = ["批量", "全部", "所有", "batch", "all", "each", "多个", "并行"]
    PROD_KEYWORDS = ["生产", "线上", "prod", "production", "CORE-01", "服务器"]
    DB_KEYWORDS = ["数据库", "SQL", "MySQL", "表", "迁移", "migration"]
    
    def extract(self, prompt: str, context: dict = None) -> TaskProfile:
        """从 prompt 和上下文提取任务画像"""
        context = context or {}
        prompt_lower = prompt.lower()
        words = prompt.split()
        
        profile = TaskProfile()
        profile.word_count = len(words)
        profile.file_count = len(context.get("files", []))
        profile.context_tokens = context.get("current_tokens", 0)
        
        # ── 复杂度判断 ──
        high_signals = sum(1 for kw in self.COMPLEXITY_HIGH if kw.lower() in prompt_lower)
        low_signals = sum(1 for kw in self.COMPLEXITY_LOW if kw.lower() in prompt_lower)
        
        if high_signals >= 2 or profile.word_count > 200:
            profile.complexity = "high"
        elif low_signals >= 3 and high_signals == 0:
            profile.complexity = "low"
        else:
            profile.complexity = "medium"
        
        # ── 质量要求 ──
        profile.requires_review = any(kw.lower() in prompt_lower for kw in self.REVIEW_KEYWORDS)
        profile.requires_test = any(kw.lower() in prompt_lower for kw in self.TEST_KEYWORDS)
        
        # ── 风险 ──
        profile.is_refactor = "refactor" in prompt_lower or "重构" in prompt
        profile.affects_production = any(kw.lower() in prompt_lower for kw in self.PROD_KEYWORDS)
        profile.affects_database = any(kw.lower() in prompt_lower for kw in self.DB_KEYWORDS)
        
        # ── 执行策略 ──
        profile.is_research = any(kw.lower() in prompt_lower for kw in self.RESEARCH_KEYWORDS)
        profile.is_iterative = any(kw.lower() in prompt_lower for kw in self.ITERATIVE_KEYWORDS)
        profile.is_batch = any(kw.lower() in prompt_lower for kw in self.BATCH_KEYWORDS)
        
        # ── 上下文压力 ──
        if profile.context_tokens > 32000:
            profile.context_pressure = "critical"
        elif profile.context_tokens > 16000:
            profile.context_pressure = "high"
        
        # ── 智能推荐 ──
        profile.suggested_model = self._recommend_model(profile)
        profile.suggested_mode = self._recommend_mode(profile)
        
        return profile
    
    def _recommend_model(self, p: TaskProfile) -> str:
        """推荐模型: flash(快) / chat(平衡) / reasoner(强推理)"""
        if p.context_pressure == "critical":
            return "flash"  # 上下文快爆了，降级
        if p.complexity == "high" or p.is_refactor or p.affects_production:
            return "reasoner"
        if p.complexity == "low" and not p.requires_review:
            return "flash"
        return "chat"
    
    def _recommend_mode(self, p: TaskProfile) -> str:
        """推荐执行模式: direct / ralph / agentic_map"""
        if p.is_iterative:
            return "ralph"
        if p.is_batch and p.complexity != "high":
            return "agentic_map"
        if p.is_research:
            return "ralph"  # 研究工作天生是迭代的
        return "direct"
    
    def explain(self, profile: TaskProfile) -> str:
        """生成人类可读的决策解释"""
        lines = [
            f"📊 任务画像: 复杂度={profile.complexity}, 词数={profile.word_count}, "
            f"子任务估算={profile.estimated_subtasks}",
            f"🎯 推荐模型: {profile.suggested_model} | 执行模式: {profile.suggested_mode}",
            f"📋 质量要求: review={profile.requires_review}, test={profile.requires_test}",
            f"⚠️ 风险: refactor={profile.is_refactor}, prod={profile.affects_production}, "
            f"db={profile.affects_database}",
            f"🔁 执行: research={profile.is_research}, iterative={profile.is_iterative}, "
            f"batch={profile.is_batch}",
            f"💾 上下文: {profile.context_tokens}tokens ({profile.context_pressure})",
        ]
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════
#  ModelRouter — 三维模型路由
# ═══════════════════════════════════════════════════
@dataclass
class RoutingDecision:
    model: str           # flash / chat / reasoner
    tier: str            # LOW / MEDIUM / HIGH
    reasons: list        # 决策原因
    confidence: float    # 置信度
    escalated: bool      # 是否升级
    interaction_mode: str  # quick_iteration / careful / normal


class ModelRouter:
    """
    三维路由决策:
    1. 任务复杂度（信号提取器输出）
    2. 上下文膨胀（动态降级）
    3. 用户交互模式（快速迭代 vs 谨慎执行）
    """
    
    MODEL_MAP = {
        "flash": "deepseek-chat",       # 快且便宜
        "chat": "deepseek-chat",        # 平衡
        "reasoner": "deepseek-reasoner", # 强推理
    }
    
    # 代理特定覆盖
    AGENT_OVERRIDES = {
        "moyuan": "reasoner",   # 数据分析用强推理
        "moqing": "chat",       # 出图用平衡模型
        "molan": "chat",        # 内容创作用平衡
        "mohong": "flash",      # 任务执行用快的
        "mocheng": "flash",     # 质量监控用快的
    }
    
    def __init__(self, extractor: TaskSignalExtractor = None):
        self.extractor = extractor or TaskSignalExtractor()
        self.routing_log = []
    
    def route(self, prompt: str, agent_type: str = None, 
              context: dict = None, interaction_mode: str = "normal") -> RoutingDecision:
        """主路由函数"""
        profile = self.extractor.extract(prompt, context)
        reasons = []
        
        # 1. 代理特定覆盖
        if agent_type and agent_type in self.AGENT_OVERRIDES:
            model = self.AGENT_OVERRIDES[agent_type]
            reasons.append(f"agent_override: {agent_type} → {model}")
            tier = self._model_to_tier(model)
            confidence = 0.85
        
        # 2. 上下文膨胀降级
        elif profile.context_pressure == "critical":
            model = "flash"
            tier = "LOW"
            reasons.append("context_pressure: critical → forced flash")
            confidence = 0.95
        
        elif profile.context_pressure == "high" and profile.complexity != "high":
            model = "flash"
            tier = "LOW"
            reasons.append("context_pressure: high → downgraded to flash")
            confidence = 0.80
        
        # 3. 用户交互模式
        elif interaction_mode == "quick_iteration":
            model = "flash"
            tier = "LOW"
            reasons.append("interaction: quick_iteration → flash")
            confidence = 0.90
        
        elif interaction_mode == "careful":
            model = "reasoner"
            tier = "HIGH"
            reasons.append("interaction: careful → reasoner")
            confidence = 0.90
        
        # 4. 标准路由
        else:
            model = profile.suggested_model
            tier = self._model_to_tier(model)
            reasons.append(f"standard: complexity={profile.complexity} → {model}")
            confidence = 0.75
        
        # 记录
        decision = RoutingDecision(
            model=model,
            tier=tier,
            reasons=reasons,
            confidence=confidence,
            escalated=False,
            interaction_mode=interaction_mode,
        )
        self.routing_log.append({
            "prompt_preview": prompt[:80],
            "agent": agent_type,
            "decision": decision,
        })
        
        return decision
    
    def _model_to_tier(self, model: str) -> str:
        if model == "reasoner": return "HIGH"
        if model == "flash": return "LOW"
        return "MEDIUM"
    
    def get_actual_model(self, decision: RoutingDecision) -> str:
        """获取实际API模型名"""
        return self.MODEL_MAP.get(decision.model, "deepseek-chat")
    
    def get_stats(self) -> dict:
        """路由统计"""
        if not self.routing_log:
            return {"total": 0}
        
        models = {}
        for entry in self.routing_log:
            m = entry["decision"].model
            models[m] = models.get(m, 0) + 1
        
        return {
            "total": len(self.routing_log),
            "distribution": models,
            "estimated_savings": f"{models.get('flash', 0) * 0.7 + models.get('chat', 0) * 0.3:.0f} vs all-reasoner",
        }


# ═══════════════════════════════════════════════════
#  RalphGoal — 目标导向执行
# ═══════════════════════════════════════════════════
@dataclass
class RalphGoal:
    """目标导向：定义"什么算完成"而不是"怎么做" """
    description: str              # "找出5个小红书标题公式"
    success_criteria: str         # "extracted_formulas >= 5 且每个有3个案例"
    max_iterations: int = 20
    checkpoint_file: str = ".ralph_progress.json"
    
    # 运行时状态
    iteration: int = 0
    context: dict = field(default_factory=dict)
    learnings: list = field(default_factory=list)
    patterns: list = field(default_factory=list)
    
    def check_success(self, result: dict) -> bool:
        """
        检查是否达成目标。
        子类可覆盖此方法实现自定义判定逻辑。
        """
        if self.iteration >= self.max_iterations:
            return True  # 达到最大迭代数，强制退出
        
        # 默认：检查 result 中的 success 标志
        return result.get("success", False)
    
    def plan_next(self, context: dict) -> str:
        """根据当前进展规划下一步"""
        if self.iteration == 0:
            return f"开始执行: {self.description}"
        
        learnings_str = '; '.join(self.learnings[-3:]) if self.learnings else '无'
        return (f"第{self.iteration}轮完成。所学: {learnings_str}。"
                f"继续目标: {self.description}。"
                f"成功标准: {self.success_criteria}")
    
    def record_learning(self, learning: str):
        self.learnings.append(learning)
    
    def record_pattern(self, pattern: str):
        if pattern not in self.patterns:
            self.patterns.append(pattern)
    
    def save_checkpoint(self):
        data = {
            "iteration": self.iteration,
            "description": self.description,
            "learnings": self.learnings[-10:],  # 保留最近10条
            "patterns": self.patterns,
            "context_keys": list(self.context.keys()),
        }
        os.makedirs(os.path.dirname(self.checkpoint_file) or ".", exist_ok=True)
        json.dump(data, open(self.checkpoint_file, "w"), ensure_ascii=False, indent=2)
    
    def load_checkpoint(self) -> bool:
        if os.path.exists(self.checkpoint_file):
            data = json.load(open(self.checkpoint_file))
            self.iteration = data.get("iteration", 0)
            self.learnings = data.get("learnings", [])
            self.patterns = data.get("patterns", [])
            return True
        return False


def run_ralph_loop(goal: RalphGoal, task_fn: Callable) -> dict:
    """
    Ralph Loop 执行器: 循环执行直到目标达成
    
    Args:
        goal: 目标定义
        task_fn: 每轮执行函数，接受 (goal, context) → 返回 result dict
    
    Returns:
        最终上下文
    """
    # 尝试恢复检查点
    goal.load_checkpoint()
    
    while goal.iteration < goal.max_iterations:
        goal.iteration += 1
        print(f"\n🔄 Ralph Loop 第 {goal.iteration}/{goal.max_iterations} 轮")
        
        # 规划这轮做什么
        next_step = goal.plan_next(goal.context)
        print(f"  📋 {next_step[:100]}")
        
        # 执行
        result = task_fn(goal, goal.context)
        goal.context.update(result)
        
        # 学习
        if result.get("learning"):
            goal.record_learning(result["learning"])
        if result.get("pattern"):
            goal.record_pattern(result["pattern"])
        
        # 检查点
        goal.save_checkpoint()
        
        # 达成？
        if goal.check_success(result):
            print(f"  ✅ 目标达成! ({goal.iteration} 轮)")
            break
    else:
        print(f"  ⚠️ 达到最大迭代数 {goal.max_iterations}")
    
    return goal.context


# ═══════════════════════════════════════════════════
#  CLI 测试
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    extractor = TaskSignalExtractor()
    router = ModelRouter(extractor)
    
    # 测试用例
    tests = [
        ("简单查询", "查看今天的陶瓷热点数据", None, "normal"),
        ("复杂重构", "重构墨家军的记忆压缩系统，涉及dag_nodes表和lcm_tools模块的大幅改动", "moyuan", "careful"),
        ("批量处理", "把所有采集到的300条小红书笔记批量分类", None, "normal"),
        ("研究任务", "调研景德镇陶瓷市场，直到找出3个可行的产品切入方向", None, "normal"),
        ("生产部署", "把新版本部署到CORE-01生产环境", None, "careful"),
        ("上下文高压", "简单查个状态", None, "quick_iteration"),
    ]
    
    for name, prompt, agent, mode in tests:
        ctx = {"current_tokens": 40000} if "高压" in name else {"current_tokens": 5000}
        profile = extractor.extract(prompt, ctx)
        decision = router.route(prompt, agent, ctx, mode)
        
        print(f"\n{'='*60}")
        print(f"📝 {name}: {prompt[:60]}...")
        print(f"   代理={agent or 'auto'}, 交互={mode}")
        print(extractor.explain(profile))
        print(f"   路由: {decision.model} (tier={decision.tier}, "
              f"confidence={decision.confidence})")
        print(f"   原因: {decision.reasons}")
