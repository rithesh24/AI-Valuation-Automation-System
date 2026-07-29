"""Runtime-editable settings the client can change from the app itself, not
just a developer editing .env — currently just the Anthropic API key.

Writes to data/local.env (colocated with the SQLite DB, same writable runtime
directory), which app/core/config.py loads *after* .env, so a client-entered
key overrides any dev-machine default. Applies the change to the in-process
settings object immediately, so no restart is needed.
"""

from pathlib import Path

from app.core.config import settings

_API_KEY_LINE_PREFIX = "ANTHROPIC_API_KEY="


class SettingsServiceError(Exception):
    """Raised when a settings update is invalid. Message is safe to show the user."""


class SettingsService:
    def is_api_key_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    def set_api_key(self, api_key: str) -> None:
        api_key = api_key.strip()
        if not api_key:
            raise SettingsServiceError("API key cannot be empty.")

        local_env_path = Path(settings.DATABASE_PATH).parent / "local.env"
        local_env_path.parent.mkdir(parents=True, exist_ok=True)

        existing_lines = (
            local_env_path.read_text(encoding="utf-8").splitlines()
            if local_env_path.exists()
            else []
        )
        kept_lines = [
            line for line in existing_lines if not line.startswith(_API_KEY_LINE_PREFIX)
        ]
        kept_lines.append(f"{_API_KEY_LINE_PREFIX}{api_key}")
        local_env_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")

        settings.ANTHROPIC_API_KEY = api_key
