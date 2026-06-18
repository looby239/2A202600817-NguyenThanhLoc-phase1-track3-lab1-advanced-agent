# Lab 16 Benchmark Report

## Metadata
- Dataset: my_test_set.json
- Mode: mock
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.55 | 1.0 | 0.45 |
| Avg attempts | 1 | 1.45 | 0.45 |
| Avg token estimate | 385 | 761.5 | 376.5 |
| Avg latency (ms) | 200 | 438.5 | 238.5 |

## Failure modes
```json
{
  "react": {
    "wrong_final_answer": 45,
    "none": 55
  },
  "reflexion": {
    "none": 100
  },
  "overall": {
    "wrong_final_answer": 45,
    "none": 155
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
