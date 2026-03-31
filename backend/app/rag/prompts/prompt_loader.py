"""Version-aware prompt loader. Reads prompt from disk at runtime."""
from pathlib import Path

from app.config import settings

_PROMPTS_DIR = Path(__file__).parent


def load_system_prompt() -> str:
    version = settings.prompt_version
    prompt_path = _PROMPTS_DIR / f"system_prompt_{version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt version '{version}' not found at {prompt_path}. "
            "Check PROMPT_VERSION env var."
        )
    return prompt_path.read_text(encoding="utf-8")
