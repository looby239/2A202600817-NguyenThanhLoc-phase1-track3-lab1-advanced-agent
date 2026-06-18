"""
Convert 100 samples from hotpot_dev_distractor_v1.json to QAExample format
and save to data/my_test_set.json
"""
import json
import random
from collections import Counter

random.seed(42)

# Load source data
with open("data/hotpot_dev_distractor_v1.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

print(f"Total records in source: {len(raw_data)}")

# Sample 100 records
samples = random.sample(raw_data, 100)

# Map HotpotQA level -> difficulty
level_map = {
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
}


def convert(item, idx):
    """Convert a HotpotQA item to QAExample format."""
    # context in hotpot: list of [title, [sentence1, sentence2, ...]]
    context_chunks = []
    for entry in item.get("context", []):
        title = entry[0]
        sentences = entry[1] if len(entry) > 1 else []
        text = " ".join(sentences).strip()
        context_chunks.append({"title": title, "text": text})

    difficulty = level_map.get(item.get("level", "medium"), "medium")

    return {
        "qid": f"hpqa_{idx:03d}",
        "difficulty": difficulty,
        "question": item["question"],
        "gold_answer": item["answer"],
        "context": context_chunks,
    }


converted = [convert(item, i + 1) for i, item in enumerate(samples)]

# Save
with open("data/my_test_set.json", "w", encoding="utf-8") as f:
    json.dump(converted, f, indent=2, ensure_ascii=False)

print(f"Saved {len(converted)} records to data/my_test_set.json")

# Stats
diff_counts = Counter(r["difficulty"] for r in converted)
print("Difficulty distribution:", dict(diff_counts))

# Preview first record
first = converted[0]
print("\nFirst record preview:")
print(f"  qid:          {first['qid']}")
print(f"  difficulty:   {first['difficulty']}")
print(f"  question:     {first['question'][:80]}...")
print(f"  gold_answer:  {first['gold_answer']}")
print(f"  context chunks: {len(first['context'])}")
for i, chunk in enumerate(first["context"][:3]):
    print(f"    [{i}] {chunk['title']}: {chunk['text'][:60]}...")
