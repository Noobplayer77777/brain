from core.retrieval import hybrid_search
from core.llm import answer_question
import json
import time

def run_test(q):
    print(f"\n[Q] {q}")
    start = time.time()
    hits = hybrid_search(q, k=8)
    if not hits:
        print("No hits found.")
    ans = answer_question(q, hits)
    elapsed = time.time() - start
    print(json.dumps(ans, indent=2))
    print(f"Elapsed: {elapsed:.2f}s")

run_test("What is normalization in DBMS?")
run_test("What is the capital of France?")
run_test("What is Euler's formula in graph theory?")
