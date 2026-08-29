# Issue Report: Prompt Engineering

## Summary
Designed and implemented a specialized `SYSTEM_PROMPT` in `orchestrator/prompts.py`. This prompt transforms the LLM into a "JSON-only Router," ensuring that user commands are reliably translated into structured tool calls for the VISION ecosystem.

## Files Changed
- `orchestrator/prompts.py`: New file containing the `SYSTEM_PROMPT` constant and dynamic tool manifest injection logic.

## Validation Performed
- **Manifest Integration**: Verified that the `TOOL_MANIFEST` from `orchestrator/manifest.py` is correctly formatted as a JSON string and injected into the prompt.
- **Strict Formatting**: The prompt includes explicit constraints to return ONLY JSON, with no conversational filler or markdown blocks.
- **Example-Based Learning**: Included few-shot examples (Apollo project creation and task assignment) to guide the model's output format.
- **Output Validation**: Created a test script to preview the final prompt and confirm that all core tools and the target JSON structure are present.

## Known Limitations
- The prompt's effectiveness depends on the specific LLM being used (e.g., Llama 3.1 vs. Phi-3.5).
- Complex multi-step intents might still require additional orchestration logic beyond a single prompt-response cycle.

## Follow-up Recommendations
- Test the prompt with live LLM calls in the next phase (`03_orchestrator_class_impl.md`).
- Refine the prompt if the model fails to correctly infer parameters from ambiguous natural language.
