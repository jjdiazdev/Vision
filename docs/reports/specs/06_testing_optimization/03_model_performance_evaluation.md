# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want to use the most efficient AI model so that the dashboard is fast and uses minimal system resources.

## Goal
Compare performance (speed vs reasoning) between Llama 3.1 and Phi-3.5 to determine the best default model.

## Context
Different models have different strengths. Phi-3.5 is smaller and faster, while Llama 3.1 might have better instruction following.

## Scope
### Files to Create/Update:
- `docs/reports/MODEL_EVALUATION.md` (New)

### Events/Triggers (if applicable):
- Manual performance benchmark.

## Expected Behavior
- Run the intent test suite against both models.
- Measure average response time (latency).
- Document accuracy and reliability for each.
- Recommend a default model for the `.env.example`.

## Future Contract
Guides future model selection as newer versions (e.g., Llama 4) are released.

## Out of Scope
- Training custom models.
- Quantization.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Benchmarks must be reproducible.

## Definition of Done (DoD)
- [ ] Benchmarks completed for both models.
- [ ] `MODEL_EVALUATION.md` report created.
- [ ] `.env.example` updated with the recommended model.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/21-model-performance-evaluation.md`
Structure:
# Issue Report: Model Performance Evaluation
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Switch `OLLAMA_MODEL` in `.env` and run `tests/test_intents.py`. Note the time taken and the accuracy for each model. Write your findings in `docs/reports/MODEL_EVALUATION.md`.
