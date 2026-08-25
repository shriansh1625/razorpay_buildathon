"""M13.22 M6/M7 identity-preserving performance tests."""

from __future__ import annotations

import hashlib
from decimal import Decimal, ROUND_HALF_EVEN

from revive.recovery.valuation.cells import shrinkage_estimate
from revive.recovery.valuation.config import default_valuation_config
from revive.recovery.valuation.money import bankers_round_paise
from revive.simulation.ids import deterministic_id
from scripts.m13_22_fingerprint import cycle_m6_m7_fingerprint

BASELINE_15 = {
    "m6_hash": "b9af5e6f94cf16997a1fa4be600130396041ac6c379aa672dbaeb1b2d070879f",
    "m7_hash": "bda2c8a45a6c6ad460958bf3f4455470b9ee66b0055e45b8bcd4ee198f1f2e4c",
    "metrics_checksum": "37d9db486094b16b614dfa20230c7e229d23df3e147674c330ada324858755cf",
}


def _legacy_deterministic_id(prefix: str, material: str) -> str:
    digest = hashlib.sha256(f"{prefix}:{material}".encode()).hexdigest()
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    value = "".join(alphabet[int(digest[i * 2 : i * 2 + 2], 16) % len(alphabet)] for i in range(26))
    return f"{prefix}_{value}"


def test_deterministic_id_matches_hex_pair_mapping():
    samples = [
        ("cand", "opp:A00:{}:0.6.0-m6"),
        ("cand", "opp:A02:{\"delay_minutes\":60}:0.6.0-m6"),
        ("ent", "seed:1:profile:BALANCED"),
    ]
    for prefix, material in samples:
        assert deterministic_id(prefix, material) == _legacy_deterministic_id(prefix, material)


def test_shrinkage_equal_priors_matches_full_formula():
    from revive.recovery.valuation.cells import beta_from_prior, beta_mean_sigma

    cfg = default_valuation_config()
    k1 = cfg.shrinkage_kappa_parent
    k2 = cfg.shrinkage_kappa_root
    for prior in (0.02, 0.15, 0.4, 0.85, 0.005, 0.995):
        got = shrinkage_estimate(prior, prior, prior, 0, cfg)
        alpha, beta = beta_from_prior(prior, cfg.prior_weight)
        parent_mean = alpha / (alpha + beta)
        mean = (k1 * parent_mean + k2 * parent_mean) / (k1 + k2)
        eff_alpha = mean * cfg.prior_weight
        eff_beta = (1.0 - mean) * cfg.prior_weight
        sigma = min(0.5, beta_mean_sigma(eff_alpha, eff_beta)[1] * 2.0)
        assert got.mean == mean
        assert got.sigma == sigma
        assert got.shrinkage_level == 2


def test_bankers_round_matches_decimal_half_even():
    one = Decimal("1")
    samples = [0.0, 0.5, 1.5, 2.5, -0.5, 12.3, 99.5, 100000.4, 0.15 * 50000]
    for value in samples:
        expected = int(Decimal(str(value)).quantize(one, rounding=ROUND_HALF_EVEN))
        assert bankers_round_paise(value) == expected


def test_seed2_balanced_15_cycle_fingerprints_unchanged():
    result = cycle_m6_m7_fingerprint(2, "BALANCED", cycles=15)
    assert result["m6_hash"] == BASELINE_15["m6_hash"]
    assert result["m7_hash"] == BASELINE_15["m7_hash"]
    assert result["metrics_checksum"] == BASELINE_15["metrics_checksum"]
