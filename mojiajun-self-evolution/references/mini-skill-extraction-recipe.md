# Mini-Skill Extraction + LLMJudge Optimization Recipe

## When to Use

When a large Skill (5000+ chars, multi-section) fails to show improvement under MIPROv2 optimization (score flatlines at 30%).

## Root Cause

The default `skill_fitness_metric` uses **keyword overlap** between expected_behavior and agent_output:
```python
overlap = len(expected_words & output_words) / len(expected_words)
score = 0.3 + (0.7 * overlap)
```

For complex orchestration skills, keyword overlap is meaningless — it can't differentiate between "followed the correct workflow" and "mentioned the right words."

## Solution: LLMJudge Injection

The `evolution/core/fitness.py` file already has a full `LLMJudge` class that scores on 3 dimensions (correctness 0.5 + procedure_following 0.3 + conciseness 0.2). But it's only used in the GEPA path. To use it with MIPROv2:

### Step 1: Create SkillFitnessLLM wrapper class

```python
class SkillFitnessLLM:
    """LLM-as-judge metric for MIPROv2 — replaces keyword overlap."""
    def __init__(self, skill_text, config):
        self.skill_text = skill_text
        self.judge = LLMJudge(config)
    
    def __call__(self, example, prediction, trace=None):
        agent_output = getattr(prediction, "output", "") or ""
        expected = getattr(example, "expected_behavior", "") or ""
        task = getattr(example, "task_input", "") or ""
        if not agent_output.strip():
            return 0.0
        score = self.judge.score(
            task_input=task,
            expected_behavior=expected,
            agent_output=agent_output[:2000],
            skill_text=self.skill_text[:3000],
        )
        return score.composite
```

### Step 2: Inject into evolve_skill.py

In `evolve_skill.py`, before the try/except block:
```python
llm_fitness = SkillFitnessLLM(skill["body"], config)
```

Then change both GEPA and MIPROv2 metrics:
```python
optimizer = dspy.GEPA(metric=llm_fitness, ...)  # was skill_fitness_metric
optimizer = dspy.MIPROv2(metric=llm_fitness, ...)  # was skill_fitness_metric
```

## Results

| Skill | Chars | Keyword Score | LLMJudge Score | Improvement |
|:---|:---:|:---:|:---:|:---:|
| mojiajun-xiaohongshu (full) | 5541 | 30% flat | 70-95% range | +0% (too large) |
| title-crafter (mini) | 1880 | 30% flat | 56-73% | **+30.3%** |
| comic-script-crafter (mini) | 2214 | — | 72-86% | **+18.6%** |
| note-body-crafter (mini) | 4201 | 78-90% | 83-90% | **+8.1%** |
| cover-prompt-crafter (mini) | 3887 | — | 87-92% | **+5.4%** |
| comment-crafter (mini) | 1980 | — | 98% | +0% (already optimal) |

## Key Insight

The LLMJudge works but MIPROv2 can only mutate small skills (1000-2000 chars). Large skills (>4000 chars) need decomposition first. The optimization improvement comes from **better few-shot example selection**, not text changes to the skill file.

## Python 3.9 Limitation

GEPA requires dspy 3.0+ which requires Python 3.10+. On Python 3.9, MIPROv2 is the fallback. To access GEPA (ICLR 2026 Oral, +10% over MIPROv2), upgrade Python.