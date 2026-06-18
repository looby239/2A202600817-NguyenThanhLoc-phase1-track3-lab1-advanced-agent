from __future__ import annotations
import os
import json
import re
import urllib.request
import urllib.error
import time
from dotenv import load_dotenv
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .utils import normalize_answer
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM

# Load environment variables
load_dotenv()

FIRST_ATTEMPT_WRONG = {"hp2": "London", "hp4": "Atlantic Ocean", "hp6": "Red Sea", "hp8": "Andes"}
FAILURE_MODE_BY_QID = {"hp2": "incomplete_multi_hop", "hp4": "wrong_final_answer", "hp6": "entity_drift", "hp8": "entity_drift"}

LAST_CALL_METRICS = {"tokens": 0, "latency_ms": 0}

def get_and_reset_last_metrics() -> tuple[int, int]:
    tokens = LAST_CALL_METRICS["tokens"]
    latency = LAST_CALL_METRICS["latency_ms"]
    LAST_CALL_METRICS["tokens"] = 0
    LAST_CALL_METRICS["latency_ms"] = 0
    return tokens, latency

def parse_json_from_response(text: str) -> dict | None:
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0).strip())
        except Exception:
            pass
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    return None

def call_llm(system_prompt: str, user_prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        return ""
        
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key and provider in ["openai", "gemini"]:
        return ""
        
    api_base = os.getenv("LLM_API_BASE", "")
    model = os.getenv("LLM_MODEL", "")
    
    start_time = time.perf_counter()
    total_tokens = 0
    response_text = ""
    
    try:
        if provider == "gemini":
            if not model:
                model = "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req_data = {
                "contents": [{"parts": [{"text": user_prompt}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]}
            }
            req_body = json.dumps(req_data).encode("utf-8")
            req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as response:
                res = json.loads(response.read().decode("utf-8"))
                response_text = res["candidates"][0]["content"]["parts"][0]["text"]
                usage = res.get("usageMetadata", {})
                total_tokens = usage.get("totalTokenCount", 0)
                
        elif provider in ["openai", "ollama"]:
            if not model:
                model = "gpt-4o-mini" if provider == "openai" else "llama3"
            if not api_base:
                api_base = "https://api.openai.com/v1" if provider == "openai" else "http://localhost:11434/v1"
                
            url = f"{api_base.rstrip('/')}/chat/completions"
            req_data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }
            req_body = json.dumps(req_data).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as response:
                res = json.loads(response.read().decode("utf-8"))
                response_text = res["choices"][0]["message"]["content"]
                usage = res.get("usage", {})
                total_tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    except Exception as e:
        print(f"Error calling LLM provider {provider}: {e}")
        return ""
        
    end_time = time.perf_counter()
    latency_ms = int((end_time - start_time) * 1000)
    
    LAST_CALL_METRICS["tokens"] += total_tokens
    LAST_CALL_METRICS["latency_ms"] += latency_ms
    
    return response_text

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> str:
    # 1. Try real LLM first
    context_text = "\n\n".join(f"Title: {chunk.title}\n{chunk.text}" for chunk in example.context)
    reflection_text = ""
    if reflection_memory:
        reflection_text = "Previous failed attempts and feedback:\n" + "\n".join(f"- {ref}" for ref in reflection_memory) + "\n\n"
        
    user_prompt = f"Context:\n{context_text}\n\nQuestion: {example.question}\n\n{reflection_text}Provide the final answer as concisely as possible."
    
    res = call_llm(ACTOR_SYSTEM, user_prompt)
    if res:
        return res.strip()
        
    # 2. Fallback to Generalized Mock Logic
    # Deterministic mock cases:
    if example.qid in FIRST_ATTEMPT_WRONG:
        if agent_type == "react":
            return FIRST_ATTEMPT_WRONG[example.qid]
        if attempt_id == 1 and not reflection_memory:
            return FIRST_ATTEMPT_WRONG[example.qid]
        return example.gold_answer
        
    # Generalized mock cases:
    is_failing_q = hash(example.qid) % 2 == 0
    if is_failing_q:
        if agent_type == "react":
            return f"Wrong candidate answer for {example.question[:20]}"
        if attempt_id == 1 and not reflection_memory:
            return f"Wrong candidate answer for {example.question[:20]}"
    return example.gold_answer

def evaluator(example: QAExample, answer: str) -> JudgeResult:
    # 1. Try real LLM first
    user_prompt = f"Question: {example.question}\nGold Answer: {example.gold_answer}\nPredicted Answer: {answer}"
    res = call_llm(EVALUATOR_SYSTEM, user_prompt)
    if res:
        parsed = parse_json_from_response(res)
        if parsed and "score" in parsed and "reason" in parsed:
            return JudgeResult(
                score=parsed["score"],
                reason=parsed["reason"],
                missing_evidence=parsed.get("missing_evidence", []),
                spurious_claims=parsed.get("spurious_claims", [])
            )
            
    # 2. Fallback to Generalized Mock Logic
    if normalize_answer(example.gold_answer) == normalize_answer(answer):
        return JudgeResult(score=1, reason="Final answer matches the gold answer after normalization.")
    if "Wrong candidate answer" in answer or example.qid in FIRST_ATTEMPT_WRONG:
        if example.qid == "hp2" or "Ada Lovelace" in example.question:
            return JudgeResult(
                score=0,
                reason="The answer stopped at the birthplace city and never completed the second hop to the river.",
                missing_evidence=["Need to identify the river that flows through London."],
                spurious_claims=[]
            )
        return JudgeResult(
            score=0,
            reason="The final answer selected the wrong second-hop entity.",
            missing_evidence=["Need to ground the answer in the second paragraph."],
            spurious_claims=[answer]
        )
    return JudgeResult(score=0, reason="The answer is incorrect.", missing_evidence=[], spurious_claims=[answer])

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> ReflectionEntry:
    # 1. Try real LLM first
    context_text = "\n\n".join(f"Title: {chunk.title}\n{chunk.text}" for chunk in example.context)
    wrong_ans = judge.spurious_claims[0] if judge.spurious_claims else "Unknown"
    user_prompt = f"Question: {example.question}\nContext:\n{context_text}\n\nPrevious Wrong Answer: {wrong_ans}\nEvaluator Feedback: {judge.reason}"
    res = call_llm(REFLECTOR_SYSTEM, user_prompt)
    if res:
        parsed = parse_json_from_response(res)
        if parsed and "failure_reason" in parsed and "lesson" in parsed and "next_strategy" in parsed:
            return ReflectionEntry(
                attempt_id=attempt_id,
                failure_reason=parsed["failure_reason"],
                lesson=parsed["lesson"],
                next_strategy=parsed["next_strategy"]
            )
            
    # 2. Fallback to Generalized Mock Logic
    strategy = "Verify the final entity against the second paragraph before answering."
    if "birthplace city" in judge.reason:
        strategy = "Do the second hop explicitly: birthplace city -> river through that city."
    return ReflectionEntry(
        attempt_id=attempt_id,
        failure_reason=judge.reason,
        lesson="A partial first-hop answer is not enough; the final answer must complete all hops.",
        next_strategy=strategy
    )
