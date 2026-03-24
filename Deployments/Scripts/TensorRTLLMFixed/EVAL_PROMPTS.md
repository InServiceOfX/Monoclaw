# EVAL_PROMPTS.md — Quick test prompts for new models

Use these to sanity-check any new model after standing it up with trtllm-serve.
Covers: knowledge recall, reasoning, math.

## Sanity / Knowledge

**Architecture knowledge (good for models trained on ML literature):**
> What is the Mamba state space model architecture?

Expected: coherent explanation of SSMs, O(N) complexity, contrast with attention O(N²),
state update recurrence. A 4B+ model should nail this.

**Capital city (baseline):**
> What is the capital of France?

Expected: "Paris". If this fails, something is badly wrong.

## Reasoning / Math

**Combinatorics (without replacement):**
> If I have 3 red balls and 5 blue balls, and I draw 2 without replacement,
> what's the probability both are blue?

Expected: 5/14 ≈ 0.357. Two valid paths: C(5,2)/C(8,2) = 10/28, or sequential
(5/8)×(4/7) = 20/56 = 5/14. Watch the `<think>` trace — good models show
explicit reasoning before the answer.

**Logic (simple):**
> A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball.
> How much does the ball cost?

Expected: $0.05. Common wrong answer is $0.10 — a good reasoning model should
catch this via the `<think>` trace.

## Code

**Single-shot Python:**
> Write a Python function that returns the nth Fibonacci number using memoization.

Expected: clean function with `@functools.lru_cache` or a manual dict cache.

## Benchmark

Run `bench_api.py` after all prompts to get tok/s numbers:
```bash
python3 bench_api.py --model <served_model_name> --runs 3
```
