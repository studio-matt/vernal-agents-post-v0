from typing import Optional


def get_openai_default_model(default: Optional[str] = None) -> str:
    """
    Centralized default OpenAI chat model selection.

    Admin can set this via Admin > Environment Variables / system admin UI.
    Those values are persisted in `system_settings` as `env_<KEY>` and served via `env_override.get_effective_env`.
    """

    if default is None:
        default = "gpt-4o-mini"

    from env_override import get_effective_env

    model = get_effective_env("OPENAI_MODEL_NAME", default)
    if model:
        return str(model).strip()
    return default

