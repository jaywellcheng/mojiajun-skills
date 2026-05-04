# MIPROv2+LLMJudge 补丁操作指南

## 何时需要

对墨家军 Skill 跑 MIPROv2 优化时，默认关键词评分器对复杂 Skill 无效（卡30%不动）。必须换 LLM-as-judge。

## 两处代码修改

### 修改1: fitness.py — 新增 SkillFitnessLLM 类

在 `skill_fitness_metric` 函数后面追加一个类，包装 `LLMJudge` 使其兼容 MIPROv2 的 metric 签名。核心逻辑：

- `__call__` 接收 example + prediction，调 LLMJudge.score() 做三维打分
- 失败时 fallback 到关键词重叠
- 截断过长文本（agent_output[:2000], skill_text[:3000]）

### 修改2: evolve_skill.py — 替换 metric

```python
# 导入处加 SkillFitnessLLM
from evolution.core.fitness import ..., SkillFitnessLLM

# 优化段：创建 llm_fitness 实例，同时传给 GEPA 和 MIPROv2
llm_fitness = SkillFitnessLLM(skill["body"], config)
# GEPA 优先，失败自动 fallback 到 MIPROv2 + llm_fitness
```

### 运行

```bash
# 需先设置 API key 环境变量
cd ~/code/hermes-agent-self-evolution
python3 -m evolution.skills.evolve_skill \
  --skill <skill-name> \
  --hermes-repo ~/.hermes \
  --iterations 5 \
  --eval-source synthetic \
  --optimizer-model deepseek/deepseek-chat \
  --eval-model deepseek/deepseek-chat
```

**注意**：不要用 bash 取 `.env` 里的 key（嵌套引号会炸），用 Python 脚本导出到环境变量。
