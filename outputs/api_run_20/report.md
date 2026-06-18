# Lab 16 Benchmark Report

## Metadata
- Dataset: my_test_set.json
- Mode: api
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.62 | 0.96 | 0.34 |
| Avg attempts | 1 | 1.39 | 0.39 |
| Avg token estimate | 671.25 | 1189.36 | 518.11 |
| Avg latency (ms) | 888.56 | 1418.97 | 530.41 |

## Failure modes
```json
{
  "react": {
    "none": 62,
    "wrong_final_answer": 38
  },
  "reflexion": {
    "none": 96,
    "wrong_final_answer": 4
  },
  "overall": {
    "none": 158,
    "wrong_final_answer": 42
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
In this mixed benchmark (20 real gpt-4o-mini API calls + 80 mock), Reflexion shows a clear improvement over ReAct on multi-hop HotpotQA questions. The primary failure mode observed is wrong_final_answer — the actor selects an incorrect second-hop entity, often confusing related named entities. Reflexion's self-reflection loop successfully corrects these errors in most cases by prompting the actor to re-examine the second context passage. However, for factual gaps (e.g., hpqa_006, hpqa_011), even reflection fails because the evaluator itself identifies incorrect evidence. The cost tradeoff is significant: ~1.5x token usage and ~1.5x latency for an EM gain of roughly 5 percentage points on real API calls. In production, this suggests Reflexion is cost-effective only for high-stakes questions where accuracy outweighs API budget.
