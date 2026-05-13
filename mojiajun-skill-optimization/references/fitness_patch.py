# fitness.py patch notes — 2026-05-04
#
# Added SkillFitnessLLM class (lines 139-185) that wraps LLMJudge as a
# MIPROv2-compatible metric. The original skill_fitness_metric (keyword
# overlap) is preserved as fallback.
#
# Key change:
# - SkillFitnessLLM.__call__() calls judge.score() with task_input,
#   expected_behavior, agent_output, skill_text
# - Returns composite score: 0.5*correctness + 0.3*procedure + 0.2*conciseness
# - Falls back to keyword overlap on LLM error

class SkillFitnessLLM:
    """LLM-as-judge metric for MIPROv2/GEPA optimization.
    Replaces the fast keyword-overlap heuristic with full LLM judging
    (correctness + procedure_following + conciseness).
    Use when the skill is complex enough that keyword overlap is meaningless.
    """

    def __init__(self, skill_text: str, config: EvolutionConfig):
        self.skill_text = skill_text
        self.config = config
        self.judge = LLMJudge(config)
        self._call_count = 0
        self._error_count = 0

    def __call__(self, example, prediction, trace=None) -> float:
        agent_output = getattr(prediction, "output", "") or ""
        expected = getattr(example, "expected_behavior", "") or ""
        task = getattr(example, "task_input", "") or ""

        if not agent_output.strip():
            return 0.0

        self._call_count += 1
        try:
            score = self.judge.score(
                task_input=task,
                expected_behavior=expected,
                agent_output=agent_output[:2000],
                skill_text=self.skill_text[:3000],
            )
            return score.composite
        except Exception:
            self._error_count += 1
            expected_words = set(expected.lower().split())
            output_words = set(agent_output.lower().split())
            if expected_words:
                overlap = len(expected_words & output_words) / len(expected_words)
                return 0.3 + (0.7 * overlap)
            return 0.5
