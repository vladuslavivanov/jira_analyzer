import os
from dotenv import load_dotenv

load_dotenv()

# Provider-agnostic LLM configuration
LLM_PROVIDER_TYPE = os.getenv("LLM_PROVIDER_TYPE", "fake")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "default-model")
LLM_FAKE_RESPONSE = os.getenv("LLM_FAKE_RESPONSE", "Analysis complete: test response")


def resolve_llm_config() -> dict:
    """Resolve LLM configuration from environment variables.
    
    Returns provider configuration dictionary that can be used with ProviderFactory.
    """
    provider_type = LLM_PROVIDER_TYPE
    
    if provider_type == "openai-compatible":
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY not set in environment for openai-compatible provider")
        
        return {
            "provider_type": provider_type,
            "api_key": str(LLM_API_KEY),
            "base_url": str(LLM_BASE_URL),
            "model": str(LLM_MODEL)
        }
    
    elif provider_type == "fake":
        return {
            "provider_type": provider_type,
            "default_response": str(LLM_FAKE_RESPONSE)
        }
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
