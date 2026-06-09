import os
from dotenv import load_dotenv

# Only load .env if it exists and don't override existing env vars set by Docker
# This allows Docker compose environment variables to take precedence
load_dotenv(override=False)

# Provider-agnostic LLM configuration
LLM_PROVIDER_TYPE = os.getenv("LLM_PROVIDER_TYPE", "fake")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "default-model")
LLM_FAKE_SCENARIO = os.getenv("LLM_FAKE_SCENARIO", "default")

# LLM debugging settings
LOG_LLM_PROMPTS = os.getenv("LOG_LLM_PROMPTS", "false").lower() == "true"

# LLM reasoning effort — single user-facing knob for model thinking/reasoning.
# Values:
#   "none" (default) — nothink mode. No reasoning/thinking parameters sent to API.
#   "low"             — low reasoning effort (OpenAI o-series: reasonin_effort="low").
#   "medium"          — medium reasoning effort (OpenAI o-series: reasonin_effort="medium").
#   "high"            — high reasoning effort (OpenAI o-series: reasonin_effort="high").
# Internal mapping:
#   "none"      → sends `thinking: {type: "disabled"}` in extra_body (DeepSeek nothink)
#   "low/high"  → sends `reasoning_effort` (OpenAI o-series) + `thinking: {type: "enabled"}` (DeepSeek)
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "none").lower()


def resolve_llm_config(reasoning_effort: str | None = None) -> dict:
    """Resolve LLM configuration from environment variables.
    
    Args:
        reasoning_effort: Optional override for reasoning effort (from UI) — "none", "low", "medium", "high"
    
    Returns provider configuration dictionary that can be used with ProviderFactory.
    """
    from jira_analyzer.analyzer.core.llm.response_schema import get_response_for_scenario
    
    provider_type = LLM_PROVIDER_TYPE
    
    if provider_type == "openai-compatible":
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY not set in environment for openai-compatible provider")
        
        final_reasoning_effort = reasoning_effort if reasoning_effort is not None else LLM_REASONING_EFFORT
        if final_reasoning_effort not in ("none", "low", "medium", "high"):
            final_reasoning_effort = "none"
        
        return {
            "provider_type": provider_type,
            "api_key": str(LLM_API_KEY),
            "base_url": str(LLM_BASE_URL),
            "model": str(LLM_MODEL),
            "reasoning_effort": final_reasoning_effort,
        }
    
    elif provider_type == "fake":
        # Use proper LLM schema based on scenario type
        fake_response = get_response_for_scenario(LLM_FAKE_SCENARIO)
        
        return {
            "provider_type": provider_type,
            "default_response": fake_response
        }
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
