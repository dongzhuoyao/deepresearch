# Early Exit Self-Speculative Decoding

**Date:** 2026-04-07
**Status:** Design complete, ready for implementation
**Target:** Workshop paper (4p) -> Conference paper (8p)

## Problem

Speculative decoding requires a separate small draft model that must be trained, stored, and aligned with the target model. This adds deployment complexity and the draft-target distribution mismatch limits acceptance rates.

## Core Idea

Make the model its own drafter via early exit. During the draft phase, run only the first K layers and use a lightweight prediction head to emit draft tokens. During verification, run all layers on the drafted sequence in parallel. No extra model, no extra parameters beyond a tiny exit head.

## Key Research Questions

1. Where to place exit points and how to measure confidence?
2. How many layers are enough for drafting on "easy" vs "hard" tokens?
3. What's the speedup vs. quality tradeoff compared to standard decoding and two-model speculative decoding?

## Method

### Architecture (zero extra training)

**Exit heads:** Attach a small linear projection (hidden_dim -> vocab_size) at layers L/4, L/2, 3L/4 (e.g., layers 6, 12, 18 for a 24-layer model). Can be trained with <100 steps of distillation on a calibration set, or used zero-shot by reusing the final LM head.

### Draft Phase

1. Run input through layers 1..K (default K = L/4, the shallowest exit)
2. Exit head produces next-token distribution
3. If confidence (top-1 probability) > threshold tau, emit token and continue drafting
4. If confidence < tau, stop drafting (this token is "hard")
5. Draft up to gamma tokens (e.g., gamma=5)

### Verify Phase

1. Take the gamma drafted tokens, run full model forward pass on the entire sequence (parallel, single pass)
2. Standard speculative decoding rejection sampling: accept prefix of tokens that match full model's distribution
3. Resume from first rejected position

### Adaptive Exit Depth (Conference Extension)

- If shallowest exit is not confident but mid exit (L/2) is, use mid exit for that token
- Creates a cascade: shallow -> mid -> deep -> full verify
- More exit points = finer granularity, but more LM heads to maintain

### Key Hyperparameters

- Exit layer K
- Confidence threshold tau
- Max draft length gamma

## Experiments

### Target Models

- Llama 3.2 1B, Llama 3.2 3B
- Qwen2.5 1.5B, Qwen2.5 3B
- (Conference: scale to 7-8B)

### Baselines

- Autoregressive decoding (no speculation)
- Standard speculative decoding with separate draft model (e.g., 1B drafting for 3B)
- LayerSkip (Meta's self-speculative method, closest prior work)

### Metrics

- **Tokens/second** — wall-clock throughput
- **Acceptance rate** — % of drafted tokens accepted
- **Draft overhead** — time spent drafting vs verifying
- **Output quality** — validate empirically with perplexity on held-out data

### Tasks

**Workshop (3 tasks):**
- Open-ended generation (MT-Bench / AlpacaEval)
- Summarization (CNN/DailyMail)
- Code generation (HumanEval)

**Conference (6+ tasks):**
- Add: math reasoning (GSM8K), QA (TriviaQA), translation
- Token-difficulty analysis: which tasks/domains have more "easy" tokens

### Ablations

- Exit layer depth (L/4 vs L/2 vs 3L/4)
- Confidence threshold tau sweep (0.5 to 0.95)
- Max draft length gamma (3, 5, 8, 12)
- Exit head: zero-shot (reuse LM head) vs distilled (100 steps)

## GPU Plan

- All experiments on single RTX 4090 (24GB), RunPod Secure Cloud
- Llama 3.2 3B in fp16 = ~6GB VRAM, plenty of room
- Estimated cost: ~$5-10 (workshop), ~$20-30 (conference with 7B+ scaling)
- Docker image: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`

## Timeline

### Phase 1 — Workshop Paper (2-3 weeks)

- Week 1: Implement early exit heads on Llama 3.2 1B/3B, baseline measurements
- Week 2: Core experiments (3 tasks, ablations on tau and gamma)
- Week 3: Write 4-page paper, figures, submit

### Phase 2 — Conference Paper (4-6 weeks after workshop)

- Weeks 4-5: Adaptive cascade (multi-exit depth), scaling to 7-8B models
- Weeks 6-7: Expanded benchmarks (6+ tasks), token difficulty analysis
- Weeks 8-9: Full 8-page paper with thorough ablations

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Shallow exit head quality is poor zero-shot | Cheap distillation (~100 steps, minutes on RTX 4090) |
| Speedup is marginal for small models | Focus metric on acceptance rate; speedup matters more at 7B+ in conference version |
| LayerSkip already covers this space | Differentiate via adaptive confidence threshold + cascade exits (LayerSkip uses fixed skip patterns) |

## Differentiation from LayerSkip

LayerSkip (Meta, 2024) uses fixed layer-skipping patterns during drafting. Our approach differs:
1. **Confidence-based adaptive exit** — stop at different depths per token based on prediction confidence, rather than a fixed skip pattern
2. **Cascade exits** — multiple exit ramps (L/4, L/2, 3L/4) instead of a single early exit
3. **Token difficulty awareness** — easy tokens exit shallow, hard tokens use more layers, creating a natural compute-allocation mechanism
