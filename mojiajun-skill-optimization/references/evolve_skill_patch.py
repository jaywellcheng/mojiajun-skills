# evolve_skill.py patch notes — 2026-05-04
#
# Two changes:
# 1. Import SkillFitnessLLM from evolution.core.fitness
# 2. Create llm_fitness = SkillFitnessLLM(skill["body"], config) and pass
#    it to both GEPA and MIPROv2 as the metric parameter
#
# Before (keyword overlap):
#   optimizer = dspy.MIPROv2(metric=skill_fitness_metric, auto="light")
#
# After (LLMJudge):
#   llm_fitness = SkillFitnessLLM(skill["body"], config)
#   optimizer = dspy.MIPROv2(metric=llm_fitness, auto="light")

# Import change:
# from evolution.core.fitness import skill_fitness_metric, LLMJudge, FitnessScore, SkillFitnessLLM

# Metric creation (before the try/except block):
# llm_fitness = SkillFitnessLLM(skill["body"], config)

# Both GEPA and MIPROv2 paths use metric=llm_fitness
