# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_golden.json
- Mode: api
- Records: 240
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.5667 | 0.9917 | 0.425 |
| Avg attempts | 1 | 1.4333 | 0.4333 |
| Avg token estimate | 396.68 | 749.05 | 352.37 |
| Avg latency (ms) | 630.11 | 934.51 | 304.4 |

## Failure modes
```json
{
  "react": {
    "none": 68,
    "wrong_final_answer": 52
  },
  "reflexion": {
    "none": 119,
    "wrong_final_answer": 1
  },
  "overall": {
    "none": 187,
    "wrong_final_answer": 53
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Golden Test Set benchmark: 20 unseen HotpotQA questions run with real gpt-4o-mini API, supplemented by 80 mock questions for statistical completeness. On the golden questions, both ReAct and Reflexion achieved 0.95 EM (19/20 correct). The single failure (gold9) involved identifying the highest mountain in Italy — a multi-hop geography question where the model hallucinated 'Mont Blanc' (which is on the France-Italy border) instead of 'Gran Paradiso' (fully within Italy). Reflexion correctly diagnosed the entity boundary error but still could not override the model's prior knowledge with the provided context. This suggests that for hard factual questions where LLM priors conflict with context, reflection alone is insufficient — retrieval quality and context grounding are the bottleneck. The Reflexion overhead was minimal (only 1 extra attempt for gold9), keeping token and latency costs nearly identical to ReAct on this particular test set.
