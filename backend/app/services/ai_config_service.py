"""Shared AI model config loader — used by text_llm_operator and vision_llm_operator."""
import json
import logging

logger = logging.getLogger(__name__)


async def get_ai_config(model_type: str = "text", requested_model: str = None) -> dict:
    """
    Load AI model config. Prefers the default ModelProfile for the given type.
    Falls back to the legacy single ai_model_config if no profiles exist.
    Returns an empty dict if nothing is configured.
    """
    try:
        from app.core.database import async_session_maker
        from app.models.setting import Setting
        async with async_session_maker() as session:
            profiles_row = await session.get(Setting, "ai_model_profiles")
            if profiles_row:
                profiles = json.loads(profiles_row.value)
                matching = [
                    p for p in profiles
                    if p.get("enabled") and p.get("model_type") in (model_type, "both")
                ]

                chosen = None
                if requested_model:
                    chosen = next((p for p in matching if p.get("model_name") == requested_model), None)

                if not chosen:
                    flag = f"is_default_{model_type}"
                    default = next((p for p in matching if p.get(flag)), None)
                    chosen = default or (matching[0] if matching else None)

                if chosen:
                    return {
                        "enabled": True,
                        "api_key": chosen.get("api_key"),
                        "base_url": chosen.get("base_url", "https://api.openai.com/v1"),
                        "text_model": chosen.get("model_name", "gpt-4o-mini"),
                        "vision_model": chosen.get("model_name", "gpt-4o"),
                        "max_tokens": chosen.get("max_tokens", 2048 if model_type == "text" else 1024),
                        "temperature": chosen.get("temperature", 0.1),
                    }

            legacy_row = await session.get(Setting, "ai_model_config")
            if legacy_row:
                return json.loads(legacy_row.value)
    except Exception as e:
        logger.warning(f"Could not load AI config from DB: {e}")
    return {}
