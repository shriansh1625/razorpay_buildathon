"""Policy pack and settings tests."""

from revive.config import PolicyPack, PolicyPackStatus, default_draft_policy_pack, load_settings


def test_draft_policy_not_frozen_for_benchmark():
    pack = default_draft_policy_pack()
    assert pack.status == PolicyPackStatus.DRAFT
    assert pack.is_frozen_for_benchmark is False
    assert pack.epsilon_paise == 0


def test_config_hash_stable():
    pack = PolicyPack(
        version="pol_test",
        status=PolicyPackStatus.DRAFT,
        epsilon_paise=0,
    )
    assert pack.config_hash() == pack.config_hash()


def test_load_settings_defaults():
    settings = load_settings()
    assert settings.master_seed >= 0
    assert settings.timezone == "Asia/Kolkata"
