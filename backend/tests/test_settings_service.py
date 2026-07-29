from pathlib import Path

import pytest

from app.services.settings_service import SettingsService, SettingsServiceError


@pytest.fixture(autouse=True)
def _isolated_data_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.services.settings_service.settings.DATABASE_PATH", str(tmp_path / "avas.db"))
    monkeypatch.setattr("app.services.settings_service.settings.ANTHROPIC_API_KEY", "")


class TestIsApiKeyConfigured:
    def test_false_when_empty(self) -> None:
        assert SettingsService().is_api_key_configured() is False

    def test_true_after_setting(self) -> None:
        service = SettingsService()
        service.set_api_key("sk-test-123")
        assert service.is_api_key_configured() is True


class TestSetApiKey:
    def test_rejects_empty_key(self) -> None:
        with pytest.raises(SettingsServiceError):
            SettingsService().set_api_key("   ")

    def test_persists_to_local_env_file(self, tmp_path: Path) -> None:
        SettingsService().set_api_key("sk-test-123")

        local_env = tmp_path / "local.env"
        assert local_env.exists()
        assert "ANTHROPIC_API_KEY=sk-test-123" in local_env.read_text(encoding="utf-8")

    def test_updates_live_setting_without_restart(self) -> None:
        from app.core.config import settings

        SettingsService().set_api_key("sk-test-123")

        assert settings.ANTHROPIC_API_KEY == "sk-test-123"

    def test_overwriting_replaces_previous_key_not_duplicates(self, tmp_path: Path) -> None:
        service = SettingsService()
        service.set_api_key("sk-old")
        service.set_api_key("sk-new")

        local_env = tmp_path / "local.env"
        content = local_env.read_text(encoding="utf-8")
        assert content.count("ANTHROPIC_API_KEY=") == 1
        assert "ANTHROPIC_API_KEY=sk-new" in content

    def test_preserves_other_lines_in_local_env(self, tmp_path: Path) -> None:
        local_env = tmp_path / "local.env"
        local_env.parent.mkdir(parents=True, exist_ok=True)
        local_env.write_text("SOME_OTHER_SETTING=1\n", encoding="utf-8")

        SettingsService().set_api_key("sk-test-123")

        content = local_env.read_text(encoding="utf-8")
        assert "SOME_OTHER_SETTING=1" in content
        assert "ANTHROPIC_API_KEY=sk-test-123" in content
