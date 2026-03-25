from typing import Optional


def get_openai_default_image_model(default: Optional[str] = None) -> str:
    """
    Centralized default OpenAI image model selection.

    Admin sets `OPENAI_IMAGE_MODEL_NAME` via the system admin UI.
    Values are persisted in `system_settings` as `env_<KEY>` and served via env_override.get_effective_env.
    """

    if default is None:
        default = "dall-e-3"

    from env_override import get_effective_env

    model = get_effective_env("OPENAI_IMAGE_MODEL_NAME", default)
    if model:
        return str(model).strip()
    return default

