Vyom — STEP 1: AI Reasoning Gateway v1.0
Updated files in this package:
ai_core/reasoning_gateway.py — new validated AI-only boundary.
ai_core/deep_reasoner.py — routes configured real-model reasoning through the gateway; deterministic local fallback remains.
tests/test_reasoning_gateway.py — offline validation tests.
The existing ModelGateway remains the provider transport. It is configured by:
VYOM_AI_API_KEY
VYOM_AI_API_URL
VYOM_AI_MODEL
No Windows executor, ToolManager, SkillBuilder, SkillRegistry, voice engine, or application launcher is modified by this step.
A configured model must return the structured JSON contract already defined by ModelGateway. The new gateway validates the contract before the result can reach the existing ReasoningEngine.
If the configured model is unavailable or returns invalid structured output, Vyom uses the existing deterministic local reasoner rather than executing an unvalidated AI decision.
