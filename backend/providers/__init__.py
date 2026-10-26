"""Explicit model construction: never fall back to Bedrock."""
from config import settings

def build_model():
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        from strands.models.ollama import OllamaModel
        return OllamaModel(host=settings.ollama_host, model_id=settings.llm_model)
    if provider in {"groq", "openai-compatible"}:
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY must be configured on the backend")
        from strands.models.openai import OpenAIModel
        model_class = OpenAIModel
        params = {"max_completion_tokens": settings.max_output_tokens}
        if provider == "groq":
            from providers.groq import GroqModel
            model_class = GroqModel
            params["parallel_tool_calls"] = False
            if settings.llm_model.startswith("openai/gpt-oss-"):
                params["reasoning_effort"] = "low"
            elif settings.llm_model == "qwen/qwen3.8-27b":
                params["reasoning_effort"] = "none"
        return model_class(client_args={"api_key": settings.llm_api_key,
            "base_url": settings.llm_base_url, "timeout": 90, "max_retries": 2},
            model_id=settings.llm_model, params=params)
    if provider == "gemini":
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY must be configured on the backend")
        from strands.models.gemini import GeminiModel
        return GeminiModel(client_args={"api_key": settings.llm_api_key}, model_id=settings.llm_model)
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
